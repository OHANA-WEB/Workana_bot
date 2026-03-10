"""
Post messages to Discord via webhooks.
"""
from __future__ import annotations

from datetime import datetime

import httpx
from workana import Job

# Discord embed max lengths
TITLE_MAX = 256
DESC_MAX = 4096
FIELD_VALUE_MAX = 1024


def _posted_timestamp() -> str:
    """Format as 'Today at 4:29 AM'."""
    now = datetime.now()
    hour = now.hour % 12 or 12
    ampm = "AM" if now.hour < 12 else "PM"
    return f"Today at {hour}:{now.minute:02d} {ampm}"


def post_job_to_discord(webhook_url: str, job: Job) -> bool:
    """Post a single new job as an embed matching the sample format."""
    if not webhook_url:
        return False
    title = (job.title or "Untitled")[:TITLE_MAX]
    description = (job.snippet or "—")[:DESC_MAX - 50]
    if not description.endswith("…") and len(job.snippet or "") > 200:
        description = description.rstrip() + "…"

    fields = [
        {"name": "Job URL", "value": job.url, "inline": False},
        {"name": "Price", "value": job.price or "N/A", "inline": True},
        {"name": "Posted", "value": job.posted or "—", "inline": True},
        {"name": "Bids", "value": job.bids or "0", "inline": True},
        {"name": "Payment method", "value": job.payment_method or "N/A", "inline": True},
        {"name": "Skills", "value": (job.skills or "—")[:FIELD_VALUE_MAX], "inline": False},
    ]

    client_parts = []
    if job.client_name:
        client_parts.append(f"**Name:** {job.client_name}")
    if job.client_nationality:
        client_parts.append(f"**Nationality:** {job.client_nationality}")
    if job.client_rating:
        client_parts.append(f"**Rating:** {job.client_rating}")
    client_value = "\n".join(client_parts) if client_parts else "—"
    fields.append({"name": "Client", "value": client_value, "inline": False})
    avatar_url = (job.client_avatar_url or "").strip()

    wid = (job.workana_job_id or "—").strip()
    ts = _posted_timestamp()
    footer = f"Workana job id: {wid} • {ts}"

    embed = {
        "title": title,
        "url": job.url,
        "description": description,
        "color": 0x5865F2,
        "fields": fields,
        "footer": {"text": footer[:2048]},
    }
    if avatar_url:
        embed["thumbnail"] = {"url": avatar_url}
    payload = {"embeds": [embed]}
    with httpx.Client(timeout=15.0) as client:
        r = client.post(webhook_url, json=payload)
    if not r.is_success and r.text:
        try:
            err = r.json()
            if "message" in err:
                print(f"Discord jobs webhook: {err.get('message', r.text)}")
        except Exception:
            print(f"Discord jobs webhook: {r.status_code} {r.text[:200]}")
    return r.is_success


def post_bid_to_discord(webhook_url: str, job: Job | None = None, bid_text: str = "", 
                        job_title: str = "", job_url: str = "") -> bool:
    """
    Post a generated bid to the bids webhook with job details.
    
    Args:
        webhook_url: Discord webhook URL
        job: Job object (preferred, includes all details)
        bid_text: The generated bid text
        job_title: Job title (fallback if job is None)
        job_url: Job URL (fallback if job is None)
    """
    if not webhook_url:
        return False
    
    # Use Job object if provided, otherwise use individual parameters
    if job:
        title = (job.title or "Bid")[:TITLE_MAX]
        url = job.url
        price = job.price or "N/A"
        avatar_url = job.client_avatar_url or ""
    else:
        title = (job_title or "Bid")[:TITLE_MAX]
        url = job_url
        price = "N/A"
    
    # Put bid text in a code block in the description for easy copying
    # Discord code blocks make it easy to select and copy - users can click and select all text
    # Using description field (4096 chars) instead of field value (1024 chars) for longer bids
    bid_display = f"```\n{bid_text}\n```"
    description = bid_display[:DESC_MAX]
    
    # Build fields with job information
    fields = [
        {"name": "Job URL", "value": url, "inline": False},
        {"name": "Price", "value": price, "inline": True},
    ]
    
    ts = _posted_timestamp()
    footer = f"Generated bid • {ts}"
    
    payload = {
        "embeds": [
            {
                "title": f"Bid: {title}",
                "url": url,
                "description": description,
                "color": 0x57F287,
                "fields": fields,
                "footer": {"text": footer[:2048]},
            }
        ]
    }
    
    # Add thumbnail if available
    if avatar_url:
        payload["embeds"][0]["thumbnail"] = {"url": avatar_url}
    
    with httpx.Client(timeout=15.0) as client:
        r = client.post(webhook_url, json=payload)
    if not r.is_success and r.text:
        try:
            err = r.json()
            if "message" in err:
                print(f"Discord bids webhook: {err.get('message', r.text)}")
        except Exception:
            print(f"Discord bids webhook: {r.status_code} {r.text[:200]}")
    return r.is_success
