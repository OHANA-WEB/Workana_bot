"""
Scrape Workana IT & Programming jobs.
Uses Playwright because the job list is loaded with JavaScript.
Extracts job data from embedded JSON (results-initials) when available.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import sync_playwright

WORKANA_JOBS_URL = "https://www.workana.com/jobs?category=it-programming&language=xx"


@dataclass
class Job:
    """A single job listing."""
    job_id: str
    title: str
    url: str
    snippet: str
    price: str = ""
    posted: str = ""
    bids: str = ""
    payment_method: str = ""
    skills: str = ""
    client_name: str = ""
    client_nationality: str = ""
    client_rating: str = ""
    client_avatar_url: str = ""  # Avatar/image URL for Discord
    workana_job_id: str = ""  # Short id for footer, e.g. 7ed60ee401c1

    def __hash__(self) -> int:
        return hash(self.job_id)


def _extract_results_from_page(page) -> list[dict]:
    """
    Extract job results from embedded JSON in results-initials (Vue component data).
    Returns list of raw job dicts with authorName, budget, profileLogo, rating, etc.
    """
    raw = page.evaluate("""
        () => {
            const searchEl = document.querySelector('search');
            if (searchEl) {
                // Check all possible attribute name variations
                const attrNames = [':results-initials', 'results-initials', 'v-bind:results-initials', 'resultsInitials'];
                for (const name of attrNames) {
                    try {
                        const v = searchEl.getAttribute(name);
                        if (v && v.length > 500 && v.includes('"results"') && (v.includes('"slug"') || v.includes('&quot;slug&quot;'))) {
                            return v;
                        }
                    } catch (e) {}
                }
                // Check all attributes on search element
                for (let i = 0; i < searchEl.attributes.length; i++) {
                    const attr = searchEl.attributes[i];
                    if ((attr.name.includes('results-initials') || attr.name.includes('resultsInitials') || 
                         attr.name.includes('results_initials')) && 
                        attr.value && attr.value.length > 500 && 
                        (attr.value.includes('"results"') || attr.value.includes('&quot;results&quot;')) &&
                        (attr.value.includes('"slug"') || attr.value.includes('&quot;slug&quot;'))) {
                        return attr.value;
                    }
                }
            }
            // Fallback: search for any element with results-initials attribute
            const names = ['results-initials', 'resultsInitials', ':results-initials', 'v-bind:results-initials'];
            for (const name of names) {
                try {
                    const el = document.querySelector('[' + name + ']');
                    if (el) {
                        const v = el.getAttribute(name);
                        if (v && v.length > 500 && v.includes('"results"')) return v;
                    }
                } catch (e) {}
            }
            // Last resort: search all elements
            const all = document.querySelectorAll('[class*="search"], [class*="container"], search, [class*="job"], [class*="project"]');
            for (const el of all) {
                for (let i = 0; i < el.attributes.length; i++) {
                    const a = el.attributes[i];
                    if (a.value && a.value.length > 500 && 
                        (a.value.includes('"results"') || a.value.includes('&quot;results&quot;')) &&
                        (a.value.includes('"slug"') || a.value.includes('&quot;slug&quot;'))) {
                        return a.value;
                    }
                }
            }
            return null;
        }
    """)
    if not raw:
        return []
    try:
        decoded = html.unescape(raw)
        data = json.loads(decoded)
        return data.get("results") or []
    except (json.JSONDecodeError, TypeError) as e:
        return []


def _job_from_json(item: dict, base_url: str = "https://www.workana.com") -> Job | None:
    """Build Job from embedded JSON result item."""
    slug = item.get("slug") or ""
    if not slug:
        return None
    job_url = f"{base_url}/job/{slug}"
    job_id = _normalize_job_id(job_url)
    title = ""
    if isinstance(item.get("title"), str):
        raw_title = item.get("title", "")
        m_title = re.search(r'title=["\']([^"\']+)["\']', raw_title)
        if m_title:
            title = html.unescape(m_title.group(1)).strip()
        if not title:
            title = re.sub(r"<[^>]+>", "", raw_title).strip()
            title = html.unescape(title)
    if not title:
        return None
    desc = item.get("description") or ""
    desc = re.sub(r"<[^>]+>", " ", desc)
    desc = re.sub(r"\s+", " ", desc).strip()
    snippet = (desc[:500] + "…") if len(desc) > 500 else desc or title[:300]
    budget = (item.get("budget") or "").strip()
    posted = (item.get("postedDate") or item.get("publishedDate") or "").strip()
    posted = re.sub(r"^Published:\s*", "", posted, flags=re.I)
    total_bids = item.get("totalBids") or ""
    if isinstance(total_bids, str):
        m = re.search(r"(\d+)", total_bids)
        total_bids = m.group(1) if m else ""
    if item.get("hasVerifiedPaymentMethod"):
        payment = "Verified"
    else:
        payment = "Hourly" if item.get("isHourly") else "Fixed"
    skills_list = item.get("skills") or []
    skills = ", ".join(s.get("anchorText", "") for s in skills_list if isinstance(s, dict))
    client_name = (item.get("authorName") or "").strip()[:80]
    country_html = item.get("country") or ""
    client_nationality = ""
    if isinstance(country_html, str):
        m = re.search(r'title=["\']([^"\']+)["\']', country_html)
        if m:
            client_nationality = html.unescape(m.group(1)).strip()[:50]
        elif "country-name" in country_html:
            m = re.search(r'country-name[^>]*>.*?>([^<]+)<', country_html)
            if m:
                client_nationality = html.unescape(m.group(1)).strip()[:50]
    rating_obj = item.get("rating") or {}
    client_rating = (rating_obj.get("value") or "") if isinstance(rating_obj, dict) else ""
    profile_logo = item.get("profileLogo") or ""
    client_avatar_url = ""
    if isinstance(profile_logo, str):
        m = re.search(r'src=["\']([^"\']+)["\']', profile_logo)
        if m:
            client_avatar_url = m.group(1).split("?")[0]
    wid = hashlib.md5(job_url.encode()).hexdigest()[:12]
    return Job(
        job_id=job_id,
        title=title,
        url=job_url,
        snippet=snippet,
        price=budget,
        posted=posted,
        bids=total_bids,
        payment_method=payment,
        skills=skills,
        client_name=client_name,
        client_nationality=client_nationality,
        client_rating=client_rating,
        client_avatar_url=client_avatar_url,
        workana_job_id=wid,
    )


def _normalize_job_id(url: str) -> str:
    """Use URL path as stable id (no query params)."""
    from urllib.parse import urlparse
    p = urlparse(url)
    path = (p.path or "").rstrip("/")
    return path or url


def load_seen_ids(path: Path) -> set[str]:
    """Load set of already-seen job IDs from file."""
    if not path.exists():
        return set()
    return set(line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def save_seen_ids(path: Path, ids: set[str]) -> None:
    """Persist seen job IDs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(sorted(ids)) + "\n", encoding="utf-8")


def _extract_json_from_html(html_content: str) -> list[dict]:
    """Fallback: extract results array from raw HTML when results-initials is present."""
    # First, try to find the search tag and extract the attribute value
    # The attribute value might span multiple lines, so we need to handle that
    search_idx = html_content.find('<search')
    if search_idx >= 0:
        # Find the start of results-initials attribute
        for pattern in [
            r':results-initials\s*=\s*["\']',  # :results-initials='
            r'results-initials\s*=\s*["\']',  # results-initials='
        ]:
            m = re.search(pattern, html_content[search_idx:search_idx + 50000], re.I | re.MULTILINE)
            if m:
                attr_value_start = search_idx + m.end()
                # Find the opening quote character
                quote_char = html_content[attr_value_start - 1]
                # Now find the matching closing quote, but we need to parse the JSON inside
                # Instead, let's find the opening brace and parse from there
                brace_start = html_content.find('{', attr_value_start)
                if brace_start >= 0:
                    content = html_content[brace_start:]
                    decoded = html.unescape(content)
                    brace_count = 0
                    in_string = False
                    escape = False
                    quote = None
                    for i, c in enumerate(decoded):
                        if escape:
                            escape = False
                            continue
                        if c == "\\":
                            escape = True
                            continue
                        if c in '"\'':
                            if not in_string:
                                in_string = True
                                quote = c
                            elif c == quote:
                                in_string = False
                            continue
                        if in_string:
                            continue
                        if c == "{":
                            brace_count += 1
                        elif c == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                try:
                                    data = json.loads(decoded[:i + 1])
                                    return data.get("results") or []
                                except (json.JSONDecodeError, TypeError):
                                    pass
                                break
                    break
    # Try to find "results" array directly in HTML (HTML-encoded or not)
    results_patterns = [
        r'&quot;results&quot;\s*:\s*\[',  # HTML-encoded "results": [
        r'"results"\s*:\s*\[',  # "results": [
        r'&quot;results&quot;\s*:\s*&quot;\[',  # HTML-encoded with quotes around array
    ]
    for pattern in results_patterns:
        m = re.search(pattern, html_content, re.I)
        if m:
            # Found "results": [, now extract the array
            array_start = m.end()
            content = html_content[array_start:]
            decoded = html.unescape(content)
            # Find the matching closing bracket
            bracket_count = 0
            in_string = False
            escape = False
            quote = None
            for i, c in enumerate(decoded):
                if escape:
                    escape = False
                    continue
                if c == "\\":
                    escape = True
                    continue
                if c in '"\'':
                    if not in_string:
                        in_string = True
                        quote = c
                    elif c == quote:
                        in_string = False
                    continue
                if in_string:
                    continue
                if c == "[":
                    bracket_count += 1
                elif c == "]":
                    bracket_count -= 1
                    if bracket_count == 0:
                        try:
                            array_str = decoded[:i + 1]
                            results_array = json.loads(array_str)
                            if isinstance(results_array, list) and len(results_array) > 0:
                                # Check if first item has "slug" key
                                if isinstance(results_array[0], dict) and "slug" in results_array[0]:
                                    return results_array
                        except (json.JSONDecodeError, TypeError):
                            pass
                        break
            break
    
    # Fallback: search for results-initials patterns
    for pattern in [
        r':results-initials\s*=\s*["\'](\{)',  # :results-initials='{
        r'results-initials\s*=\s*["\'](\{)',  # results-initials='{
        r'["\']results-initials["\']\s*:\s*["\'](\{)',
        r':results-initials\s*=\s*["\'](&quot;resultDescription&quot;)',  # HTML-encoded with colon
        r'results-initials\s*=\s*["\'](&quot;resultDescription&quot;)',  # HTML-encoded
    ]:
        m = re.search(pattern, html_content, re.I)
        if m:
            break
    else:
        return []
    if m.lastindex and m.lastindex >= 1:
        start = m.start(1)
    else:
        idx = m.start()
        start = html_content.rfind("{", max(0, idx - 50000), idx + 1)
        if start == -1:
            start = html_content.rfind("&quot;resultDescription&quot;", max(0, idx - 50000), idx + 1)
            if start >= 0:
                start = html_content.rfind("{", max(0, start - 1000), start + 1)
            if start == -1:
                return []
    content = html.unescape(html_content[start:])
    brace_count = 0
    in_string = False
    escape = False
    quote = None
    for i, c in enumerate(content):
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c in '"\'':
            if not in_string:
                in_string = True
                quote = c
            elif c == quote:
                in_string = False
            continue
        if in_string:
            continue
        if c == "{":
            brace_count += 1
        elif c == "}":
            brace_count -= 1
            if brace_count == 0:
                try:
                    data = json.loads(content[: i + 1])
                    return data.get("results") or []
                except (json.JSONDecodeError, TypeError):
                    pass
                break
    return []


def fetch_jobs(seen_path: Path, headless: bool = True, debug: bool = False) -> list[Job]:
    """
    Open Workana jobs page and extract jobs only from embedded JSON (results-initials).
    No DOM scraping or job page visits.
    """
    seen = load_seen_ids(seen_path)
    new_jobs: list[Job] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
            )
            page = context.new_page()
            page.set_default_timeout(20000)
            page.set_viewport_size({"width": 1920, "height": 1080})

            api_response_data = []
            api_urls_seen = []
            raw_html_response = [None]
            
            def handle_response(response):
                url = response.url
                api_urls_seen.append(url)
                # Capture the main HTML response
                if url == WORKANA_JOBS_URL or (url.startswith("https://www.workana.com/jobs") and "?" in url and "category=" in url):
                    try:
                        raw_html_response[0] = response.body()
                    except Exception:
                        pass
                content_type = response.headers.get("content-type", "").lower()
                if ("json" in content_type or "/jobs" in url or "search" in url.lower() or 
                    "projects" in url.lower() or "api" in url.lower() or "workana.com/jobs" in url):
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            if "results" in data and isinstance(data.get("results"), list):
                                api_response_data.append(data)
                            elif "data" in data and isinstance(data.get("data"), dict):
                                if "results" in data["data"]:
                                    api_response_data.append(data["data"])
                            elif "resultDescription" in data:
                                api_response_data.append(data)
                    except Exception:
                        pass
            
            page.on("response", handle_response)
            
            # Use domcontentloaded to get HTML before Vue fully processes it
            page.goto(WORKANA_JOBS_URL, wait_until="domcontentloaded")
            # Try to extract from raw response body first
            json_results = []
            if raw_html_response[0]:
                try:
                    html_text = raw_html_response[0].decode('utf-8', errors='ignore')
                    json_results = _extract_json_from_html(html_text)
                    if json_results:
                        print(f"  [Workana] Found {len(json_results)} jobs from raw HTML response.")
                except Exception as e:
                    if debug:
                        print(f"  [Debug] Error reading raw HTML: {e}")
            # Also try immediate content capture
            if not json_results:
                initial_html = page.content()
                json_results = _extract_json_from_html(initial_html)
                if json_results:
                    print(f"  [Workana] Found {len(json_results)} jobs from initial HTML.")
            page.wait_for_timeout(5000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(3000)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(2000)

            try:
                page.wait_for_selector('a[href*="/job/"]', timeout=10000)
            except Exception:
                pass

            if not json_results:
                json_results = []
            if api_response_data:
                json_results = api_response_data[0].get("results") or []
                if json_results:
                    print(f"  [Workana] Found {len(json_results)} jobs via API response.")

            if not json_results:
                json_results = []
                for _ in range(12):
                    json_results = _extract_results_from_page(page)
                    if json_results:
                        break
                    if api_response_data:
                        json_results = api_response_data[0].get("results") or []
                        if json_results:
                            break
                    page.wait_for_timeout(1000)
            if not json_results:
                json_results = page.evaluate("""
                    () => {
                        if (window.__VUE__ || window.Vue) {
                            const app = document.querySelector('#app') || document.querySelector('[data-v-app]');
                            if (app && app.__vue__) {
                                const vm = app.__vue__;
                                const search = vm.$children.find(c => c.$options.name === 'search' || c.$el?.tagName === 'SEARCH');
                                if (search && search.$props && search.$props.resultsInitials) {
                                    return search.$props.resultsInitials.results || [];
                                }
                            }
                        }
                        return null;
                    }
                """)
            if not json_results:
                # Try to get the attribute value directly from the DOM element
                attr_value = page.evaluate("""
                    () => {
                        const searchEl = document.querySelector('search');
                        if (searchEl) {
                            const attrNames = [':results-initials', 'results-initials', 'v-bind:results-initials'];
                            for (const name of attrNames) {
                                const v = searchEl.getAttribute(name);
                                if (v && v.includes('"results"') && v.includes('"slug"')) {
                                    return v;
                                }
                            }
                            // Check all attributes
                            for (const attr of searchEl.attributes) {
                                if (attr.name.includes('results-initials') && attr.value && 
                                    attr.value.length > 500 && attr.value.includes('"results"')) {
                                    return attr.value;
                                }
                            }
                        }
                        return null;
                    }
                """)
                if attr_value:
                    try:
                        decoded = html.unescape(attr_value)
                        data = json.loads(decoded)
                        json_results = data.get("results") or []
                        if json_results:
                            print(f"  [Workana] Found {len(json_results)} jobs from search element attribute.")
                    except (json.JSONDecodeError, TypeError) as e:
                        if debug:
                            print(f"  [Debug] Failed to parse attribute value: {e}")
                if not json_results:
                    html_content = page.content()
                    if debug:
                        debug_file = seen_path.parent / "debug_page.html"
                        debug_file.write_text(html_content[:500000], encoding="utf-8")
                        print(f"  [Debug] Saved page HTML to {debug_file} (first 500KB)")
                        # Also save a search for results-initials
                        if 'results-initials' in html_content.lower():
                            print(f"  [Debug] Found 'results-initials' in HTML")
                        if '<search' in html_content.lower():
                            print(f"  [Debug] Found '<search' tag in HTML")
                    json_results = _extract_json_from_html(html_content)
            if not json_results:
                page.wait_for_timeout(3000)
                json_results = page.evaluate("""
                    () => {
                        const searchEl = document.querySelector('search');
                        if (searchEl && searchEl.__vue__) {
                            const vm = searchEl.__vue__;
                            if (vm.$props && vm.$props.resultsInitials) {
                                return vm.$props.resultsInitials.results || [];
                            }
                            if (vm.$data && vm.$data.searchResults && vm.$data.searchResults.results) {
                                return vm.$data.searchResults.results || [];
                            }
                        }
                        const app = document.querySelector('#app');
                        if (app && app.__vue__) {
                            const walk = (vm) => {
                                if (vm.$props && vm.$props.resultsInitials) {
                                    return vm.$props.resultsInitials.results || [];
                                }
                                if (vm.$data && vm.$data.searchResults && vm.$data.searchResults.results) {
                                    return vm.$data.searchResults.results || [];
                                }
                                if (vm.$children) {
                                    for (const child of vm.$children) {
                                        const found = walk(child);
                                        if (found) return found;
                                    }
                                }
                                return null;
                            };
                            const found = walk(app.__vue__);
                            if (found) return found;
                        }
                        const scripts = document.querySelectorAll('script');
                        for (const s of scripts) {
                            const t = s.textContent || '';
                            const idx = t.indexOf('"results"');
                            if (idx >= 0 && t.indexOf('"slug"') >= 0) {
                                const start = t.lastIndexOf('{', idx);
                                if (start >= 0) {
                                    let depth = 0, inStr = false, q = null, esc = false;
                                    for (let i = start; i < t.length && i < start + 200000; i++) {
                                        const c = t[i];
                                        if (esc) { esc = false; continue; }
                                        if (c === '\\\\') { esc = true; continue; }
                                        if ('"\\''.indexOf(c) >= 0) {
                                            if (!inStr) { inStr = true; q = c; }
                                            else if (c === q) inStr = false;
                                            continue;
                                        }
                                        if (inStr) continue;
                                        if (c === '{') depth++;
                                        else if (c === '}') {
                                            depth--;
                                            if (depth === 0) {
                                                try {
                                                    const parsed = JSON.parse(t.substring(start, i + 1));
                                                    return parsed.results || [];
                                                } catch (e) {}
                                                break;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        return null;
                    }
                """)
                if json_results and isinstance(json_results, str):
                    try:
                        decoded = html.unescape(json_results)
                        data = json.loads(decoded)
                        json_results = data.get("results") or []
                    except Exception:
                        json_results = []
            if not json_results:
                html_content = page.content()
                idx = html_content.find('"results"')
                if idx >= 0 and html_content.find('"slug"') >= 0:
                    start = html_content.rfind("{", max(0, idx - 100000), idx + 1)
                    if start >= 0:
                        content = html.unescape(html_content[start:start + 500000])
                        brace_count = 0
                        in_string = False
                        escape = False
                        quote = None
                        for i, c in enumerate(content):
                            if escape:
                                escape = False
                                continue
                            if c == "\\":
                                escape = True
                                continue
                            if c in '"\'':
                                if not in_string:
                                    in_string = True
                                    quote = c
                                elif c == quote:
                                    in_string = False
                                continue
                            if in_string:
                                continue
                            if c == "{":
                                brace_count += 1
                            elif c == "}":
                                brace_count -= 1
                                if brace_count == 0:
                                    try:
                                        data = json.loads(content[:i + 1])
                                        json_results = data.get("results") or []
                                        break
                                    except (json.JSONDecodeError, TypeError):
                                        pass

            if not json_results:
                print("  [Workana] Could not extract job list from page (JSON not found).")
                if debug and api_urls_seen:
                    api_candidates = [u for u in api_urls_seen if "/jobs" in u or "search" in u.lower() or "api" in u.lower()][:5]
                    if api_candidates:
                        print(f"  [Debug] Sample API URLs seen: {api_candidates[:3]}")
                print("  [Workana] The page may load jobs via API after initial render.")
            else:
                parsed = 0
                for item in json_results:
                    job = _job_from_json(item)
                    if job:
                        parsed += 1
                        if job.job_id not in seen:
                            new_jobs.append(job)
                            seen.add(job.job_id)
                if parsed and not new_jobs:
                    print(f"  [Workana] Extracted {parsed} jobs from page; all already in seen list.")

            if new_jobs:
                save_seen_ids(seen_path, seen)

        finally:
            browser.close()

    return new_jobs
