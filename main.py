"""
Workana job monitor: scrape new IT/Programming jobs, post to Discord,
and optionally generate bids with your local LLM and post to a second webhook.
Jobs with price >= 500 USD get an automatic bid generated and sent to Discord.

Usage:
  # Post new jobs to Discord (run on a schedule or loop)
  python main.py

  # Generate a bid for a job and post to Discord (interactive or from link)
  python main.py --bid "Job title" "https://www.workana.com/jobs/..."
"""
from __future__ import annotations

import argparse
import re
import sys
import time

from config import (
    DATA_DIR,
    DISCORD_WEBHOOK_BIDS,
    DISCORD_WEBHOOK_BIDS_2,
    DISCORD_WEBHOOK_JOBS,
    LLAMA_SERVER_URL,
    POLL_INTERVAL,
    SEEN_JOBS_FILE,
)
from discord_webhook import post_bid_to_discord, post_job_to_discord
from workana import Job, fetch_jobs
from bid_generator import generate_bid, SYSTEM_PROMPT_1, SYSTEM_PROMPT_2

# Minimum job price (USD) to trigger automatic bid generation
AUTO_BID_MIN_USD = 500


def _parse_price_max_usd(price_str: str) -> tuple[int | None, bool]:
    """
    Parse Workana price string. Returns (max_usd, is_less_than).
    E.g. "USD 500 - 1,000" -> (1000, False), "Less than USD 50" -> (50, True).
    """
    if not (price_str and price_str.strip()):
        return None, False
    s = price_str.strip()
    if re.match(r"Less than\s+(?:USD\s+)?([\d,]+)", s, re.I):
        m = re.search(r"([\d,]+)", s)
        if m:
            return int(m.group(1).replace(",", "")), True
    if re.match(r"Over\s+(?:USD\s+)?([\d,]+)", s, re.I):
        m = re.search(r"([\d,]+)", s)
        if m:
            return int(m.group(1).replace(",", "")), False
    nums = re.findall(r"[\d,]+", s)
    if nums:
        values = [int(n.replace(",", "")) for n in nums]
        return max(values), False
    return None, False


def _job_meets_auto_bid_price(job: Job, min_usd: int = AUTO_BID_MIN_USD) -> bool:
    """True if the job's price indicates budget of min_usd or more."""
    max_usd, is_less_than = _parse_price_max_usd(job.price or "")
    if max_usd is None:
        return False
    if is_less_than:
        return max_usd > min_usd  # "Less than 1000" -> can be 500+
    return max_usd >= min_usd


def run_monitor(headless: bool = True, debug: bool = False) -> None:
    """Fetch new jobs from Workana, post each to Discord; auto-generate bid if price >= 500 USD."""
    if not DISCORD_WEBHOOK_JOBS:
        print("Set DISCORD_WEBHOOK_JOBS in .env to post jobs to Discord.")
        sys.exit(1)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Checking Workana for new jobs (seen list: {SEEN_JOBS_FILE})...")
    new = fetch_jobs(SEEN_JOBS_FILE, headless=headless, debug=debug)
    if not new:
        print("No new jobs.")
        return
    print(f"Found {len(new)} new job(s). Posting to Discord...")
    for job in new:
        ok = post_job_to_discord(DISCORD_WEBHOOK_JOBS, job)
        safe_title = job.title[:50].encode("ascii", errors="replace").decode()
        print(f"  {'OK' if ok else 'FAIL'}: {safe_title}...")

        if ok and _job_meets_auto_bid_price(job) and (DISCORD_WEBHOOK_BIDS or DISCORD_WEBHOOK_BIDS_2):
            desc = (job.snippet or f"Job: {job.title}")[:2000]
            if DISCORD_WEBHOOK_BIDS:
                print(f"    Price >= ${AUTO_BID_MIN_USD} USD -> generating bid (account 1)...")
                try:
                    bid_text = generate_bid(job.title, desc, system_prompt=SYSTEM_PROMPT_1)
                    if bid_text:
                        bid_ok = post_bid_to_discord(DISCORD_WEBHOOK_BIDS, job, bid_text)
                        print(f"    Bid 1 {'posted' if bid_ok else 'failed'} to Discord.")
                    else:
                        print("    Bid 1 empty, skipped.")
                except Exception as e:
                    print(f"    Bid 1 error: {e}")
            if DISCORD_WEBHOOK_BIDS_2:
                print(f"    Generating bid (account 2 - Yevhenii K.)...")
                try:
                    bid_text = generate_bid(job.title, desc, system_prompt=SYSTEM_PROMPT_2)
                    if bid_text:
                        bid_ok = post_bid_to_discord(DISCORD_WEBHOOK_BIDS_2, job, bid_text)
                        print(f"    Bid 2 {'posted' if bid_ok else 'failed'} to Discord.")
                    else:
                        print("    Bid 2 empty, skipped.")
                except Exception as e:
                    print(f"    Bid 2 error: {e}")
    print("Done.")


def run_bid(job_title: str, job_url: str, description: str | None = None, account: int = 1) -> None:
    """Generate a bid with the local LLM and post to Discord."""
    webhook = DISCORD_WEBHOOK_BIDS if account == 1 else DISCORD_WEBHOOK_BIDS_2
    prompt = SYSTEM_PROMPT_1 if account == 1 else SYSTEM_PROMPT_2
    if not webhook:
        print(f"Set DISCORD_WEBHOOK_BIDS{' (account 1)' if account == 1 else '_2 (account 2)'} in .env to post bids.")
        sys.exit(1)
    desc = description or f"Job: {job_title}"
    print(f"Generating bid for: {job_title} (account {account})")
    print(f"Using LLM at {LLAMA_SERVER_URL}...")
    try:
        bid_text = generate_bid(job_title, desc, system_prompt=prompt)
    except Exception as e:
        print(f"LLM error: {e}")
        sys.exit(1)
    if not bid_text:
        print("Empty response from LLM.")
        sys.exit(1)
    print("Bid generated. Posting to Discord...")
    ok = post_bid_to_discord(webhook, job=None, bid_text=bid_text,
                             job_title=job_title, job_url=job_url)
    print("Posted to Discord." if ok else "Failed to post to Discord.")
    if not ok:
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description="Workana job monitor + Discord + LLM bids")
    ap.add_argument("--no-headless", action="store_true", help="Show browser when scraping")
    ap.add_argument("--loop", action="store_true", help="Loop: check Workana every POLL_INTERVAL seconds")
    ap.add_argument("--bid", nargs=2, metavar=("TITLE", "URL"), help="Generate bid for this job and post to Discord")
    ap.add_argument("--bid-desc", type=str, default=None, help="Extra job description for --bid")
    ap.add_argument("--account", type=int, choices=[1, 2], default=1, help="Account (1 or 2) for --bid; 2 uses Yevhenii K. prompt")
    ap.add_argument("--debug", action="store_true", help="Save page HTML to data/debug_page.html for inspection")
    args = ap.parse_args()

    if args.bid:
        title, url = args.bid
        run_bid(title, url, args.bid_desc, args.account)
        return

    if args.loop:
        while True:
            try:
                run_monitor(headless=not args.no_headless, debug=args.debug)
            except Exception as e:
                print(f"Monitor error: {e}")
            print(f"Sleeping {POLL_INTERVAL}s...")
            time.sleep(POLL_INTERVAL)
    run_monitor(headless=not args.no_headless, debug=args.debug)


if __name__ == "__main__":
    main()
