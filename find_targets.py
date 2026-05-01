#!/usr/bin/env python3
"""
Step 1 — Find free guest posting blogs.
Searches Google via Serper API, visits each blog, checks it's free,
extracts editor email, and saves to targets.json.
"""

import re
import time
import random
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from typing import Optional
import db
from config import (
    SERPER_API_KEY, SEARCH_QUERIES, DOMAIN_BLOCKLIST,
    PAID_INDICATORS, QUALITY_INDICATORS, MAX_NEW_TARGETS_PER_DAY,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

SKIP_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "example.com", "test.com", "domain.com", "yoursite.com",
    "youremail.com", "email.com", "mail.com", "xyz.com",
    "site.com", "website.com", "mydomain.com", "company.com",
    "wixpress.com", "squarespace.com", "weebly.com",
}

# Placeholder email patterns — reject these regardless of domain
FAKE_EMAIL_PATTERNS = [
    "abc@", "test@test", "email@site", "name@", "user@", "you@",
    "yourname@", "example@", "hello@example", "info@example",
    "admin@example", "webmaster@example", "no-reply@example",
]

# File extension patterns that are NOT emails (image/asset filenames)
NON_EMAIL_EXTENSIONS = re.compile(
    r"\.(png|jpg|jpeg|gif|svg|ico|pdf|zip|mp4|webp|woff|ttf|css|js)$", re.I
)

# Domains we know are NOT guest posting blogs
EXTRA_BLOCKLIST = {
    # News outlets
    "moneycontrol.com", "ndtv.com", "timesofindia.com", "hindustantimes.com",
    "economictimes.com", "livemint.com", "businesstoday.in", "inc42.com",
    "yourstory.com", "entrackr.com", "tcrn.ch",
    # Exchanges & big brands (not blogs)
    "coinswitch.co", "wazirx.com", "coindcx.com", "zebpay.com",
    "binance.com", "coinbase.com", "kraken.com",
    # Irrelevant verticals
    "amity.edu", "naukri.com", "shine.com", "jobaaj.com",
    "monafoundation.org", "ikigailaw.com", "imarticus.org",
}

EDITORIAL_KEYWORDS = [
    "editor", "editorial", "submit", "contribute", "guest",
    "write", "content", "hello", "info", "contact", "team",
]


def serper_search(query: str) -> list:
    """Search Google via Serper. Returns list of organic results."""
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            json={"q": query, "gl": "in", "hl": "en", "num": 10},
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json().get("organic", [])
    except Exception as e:
        print(f"    Serper error: {e}")
    return []


def get_domain(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "").lower()


def is_blocked_domain(url: str) -> bool:
    domain = get_domain(url)
    return domain in DOMAIN_BLOCKLIST or domain in EXTRA_BLOCKLIST


def fetch_page(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch a URL and return HTML text, or None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return None


def is_valid_email(email: str) -> bool:
    """Return True only if the email looks like a real editorial address."""
    email = email.lower().strip(".")

    # Reject image/asset filenames accidentally captured by the regex
    if NON_EMAIL_EXTENSIONS.search(email):
        return False

    # Must have exactly one @
    parts = email.split("@")
    if len(parts) != 2:
        return False

    local, domain = parts

    # Reject known junk domains
    if domain in SKIP_EMAIL_DOMAINS:
        return False

    # Reject known placeholder patterns
    if any(email.startswith(p) or p in email for p in FAKE_EMAIL_PATTERNS):
        return False

    # Domain must look like a real TLD (at least one dot, reasonable length)
    if "." not in domain or len(domain) < 4 or len(domain) > 60:
        return False

    # Local part must be at least 2 chars and not purely numeric
    if len(local) < 2 or local.isdigit():
        return False

    # Reject overly long addresses (usually garbled)
    if len(email) > 70:
        return False

    return True


def extract_email(html: str) -> Optional[str]:
    """Extract the best editorial email from page HTML."""
    # Use BeautifulSoup to get text-only (avoids capturing URLs/src attributes)
    try:
        soup = BeautifulSoup(html, "lxml")
        # Remove script and style tags
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(" ")
    except Exception:
        text = html

    emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    priority, others = [], []

    for raw_email in emails:
        email = raw_email.lower().strip(".")
        if not is_valid_email(email):
            continue
        local = email.split("@")[0]
        if any(kw in local for kw in EDITORIAL_KEYWORDS):
            priority.append(email)
        else:
            others.append(email)

    return priority[0] if priority else (others[0] if others else None)


def is_free_guest_posting(html: str) -> bool:
    """Return False if the page mentions charging for guest posts."""
    text = html.lower()
    return not any(indicator in text for indicator in PAID_INDICATORS)


def has_guest_post_page(blog_url: str) -> Optional[str]:
    """
    Try common guest-post page paths. Returns the URL of the page if found.
    """
    paths = [
        "/write-for-us", "/write-for-us/", "/guest-post", "/guest-posts",
        "/submit-article", "/submit-a-post", "/contribute", "/contributors",
        "/guest-author", "/become-a-contributor", "/content-guidelines",
        "/submission-guidelines",
    ]
    base = blog_url.rstrip("/")
    for path in paths:
        url = base + path
        html = fetch_page(url, timeout=8)
        if html:
            text_lower = html.lower()
            if any(kw in text_lower for kw in QUALITY_INDICATORS):
                return url
    return None


def infer_blog_name(html: str, url: str) -> str:
    """Extract blog name from title tag or og:site_name."""
    soup = BeautifulSoup(html, "lxml")
    og = soup.find("meta", property="og:site_name")
    if og and og.get("content"):
        return og["content"].strip()
    if soup.title and soup.title.string:
        name = soup.title.string.strip().split("|")[0].split("–")[0].strip()
        if name:
            return name
    return get_domain(url).replace("-", " ").replace(".", " ").title()


def infer_niche(text: str) -> str:
    text = text.lower()
    if any(w in text for w in ["defi", "blockchain", "crypto", "bitcoin", "web3", "nft", "tokeniz"]):
        return "crypto"
    if any(w in text for w in ["invest", "stock", "finance", "trading", "mutual fund"]):
        return "finance"
    if any(w in text for w in ["startup", "fintech", "saas", "tech"]):
        return "fintech"
    return "finance"


def find_new_targets(db_data: dict, limit: int = MAX_NEW_TARGETS_PER_DAY) -> int:
    """
    Main function: run searches, find free blogs, add to db.
    Returns number of new targets added.
    """
    added = 0
    seen_domains = set(get_domain(t["blog_url"]) for t in db.get_all(db_data))

    queries = random.sample(SEARCH_QUERIES, min(len(SEARCH_QUERIES), 6))

    for query in queries:
        if added >= limit:
            break

        print(f"  Searching: {query[:60]}...")
        results = serper_search(query)
        time.sleep(random.uniform(1.5, 3.0))

        for result in results:
            if added >= limit:
                break

            url = result.get("link", "")
            if not url:
                continue

            domain = get_domain(url)
            if domain in seen_domains or is_blocked_domain(url):
                continue

            seen_domains.add(domain)
            base_url = f"https://{domain}"

            print(f"    Checking: {domain}")

            # Try to find the guest post page
            guest_url = has_guest_post_page(base_url)
            if not guest_url:
                # Maybe the search result IS the guest post page
                html = fetch_page(url, timeout=8)
                if html and any(kw in html.lower() for kw in QUALITY_INDICATORS):
                    guest_url = url
            if not guest_url:
                print(f"      No guest post page found — skip")
                continue

            # Fetch the guest post page
            guest_html = fetch_page(guest_url, timeout=10)
            if not guest_html:
                print(f"      Could not load guest post page — skip")
                continue

            # Check it's free
            if not is_free_guest_posting(guest_html):
                print(f"      Paid guest posting detected — skip")
                continue

            # Extract email (check guest page first, then homepage)
            email = extract_email(guest_html)
            if not email:
                home_html = fetch_page(base_url, timeout=8) or ""
                email = extract_email(home_html)
            if not email:
                # Try /contact page
                contact_html = fetch_page(base_url + "/contact", timeout=6) or ""
                email = extract_email(contact_html)

            if not email:
                print(f"      No email found — skip")
                continue

            if db.already_have(db_data, email):
                print(f"      Already in DB — skip")
                continue

            # Get blog name and niche
            home_html = fetch_page(base_url, timeout=8) or guest_html
            blog_name = infer_blog_name(home_html, base_url)
            niche = infer_niche(guest_html + home_html)

            ok = db.add_target(
                db_data,
                blog_name=blog_name,
                blog_url=base_url,
                guest_post_url=guest_url,
                editor_email=email,
                niche=niche,
            )
            if ok:
                added += 1
                print(f"      ✅ Added: {blog_name} <{email}>")
                db.save(db_data)

            time.sleep(random.uniform(2, 4))

    return added


if __name__ == "__main__":
    print("Finding new free guest posting targets...")
    data = db.load()
    n = find_new_targets(data)
    print(f"\nDone. {n} new targets added.")
