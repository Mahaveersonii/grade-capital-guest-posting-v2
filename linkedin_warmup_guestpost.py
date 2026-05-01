#!/usr/bin/env python3
"""
LinkedIn Warm-up for Guest Posting — runs LOCALLY as a Claude Code routine.

For each new target (blog editors we're about to pitch):
  1. Search LinkedIn for the editor / blog
  2. Comment on their latest relevant post (opinion + mention of email)
  3. Send a connection request with a short note

Reads targets from targets.json in this folder (synced from GitHub by pipeline).
Updates targets.json locally — commit manually or let GitHub Actions pick it up.

Run:  python3 linkedin_warmup_guestpost.py
"""

import os
import sys
import json
import time
import random
from pathlib import Path
from typing import Optional

import anthropic
from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
TARGETS_FILE = BASE_DIR / "targets.json"

# Reuse the existing Mahaveer LinkedIn session
LINKEDIN_SESSION = (
    Path(__file__).parent.parent / "linkedin-automation" / "linkedin_session.json"
)

# ── Load env ───────────────────────────────────────────────────────────────────
_ENV = Path(__file__).parent.parent / "linkedin-automation" / ".env"
if _ENV.exists():
    for _ln in _ENV.read_text().splitlines():
        _ln = _ln.strip()
        if _ln and not _ln.startswith("#") and "=" in _ln:
            _k, _v = _ln.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

MAX_PER_RUN = 5  # LinkedIn warm-ups per run (avoid rate limits)

AUTHOR_CONTEXT = """
You are writing as Mahaveer Soni — Marketing Manager at Grade Capital (India's first
crypto derivatives fund) and Grade Institute of Finance. Expert in crypto markets, DeFi,
blockchain regulation, and tokenization. 3+ years at Grade Capital working with live derivatives markets.
"""

STYLE_RULES = """
- 2-3 sentences MAX
- Open with a sharp opinion on the post (reference something specific from it)
- End with ONE casual sentence mentioning you sent them an email about a guest post
- No hashtags, no emojis, no sycophantic openers ("Great post", "Love this")
- Don't start with "I"
- State opinions with conviction — no hedging
- The email mention must feel natural, not like an ad
"""


def load_targets() -> dict:
    if TARGETS_FILE.exists():
        return json.loads(TARGETS_FILE.read_text())
    return {"targets": []}


def save_targets(data: dict):
    TARGETS_FILE.write_text(json.dumps(data, indent=2))


def get_new_targets(data: dict) -> list:
    """Return targets that are new and haven't been warmed up on LinkedIn yet."""
    return [
        t for t in data.get("targets", [])
        if t.get("status") == "new" and not t.get("linkedin_warmed")
    ]


def generate_warmup_comment(post_text: str, blog_name: str) -> Optional[str]:
    """Generate a comment that's a genuine opinion + mentions the email."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""
{AUTHOR_CONTEXT}

Write a LinkedIn comment on this post. The commenter (Mahaveer) has also sent an
email to {blog_name} today about contributing a guest article.

{STYLE_RULES}

POST:
\"\"\"{post_text[:800]}\"\"\"

Write the comment now. Just the comment text — no explanation.
"""
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        print(f"    Claude error: {e}")
        return None


def human_delay(a=1.5, b=3.5):
    time.sleep(random.uniform(a, b))


def search_linkedin_for_blog(page, blog_name: str) -> Optional[str]:
    """
    Search LinkedIn for the blog/editor. Returns the URL of the top result or None.
    """
    search_url = (
        f"https://www.linkedin.com/search/results/people/"
        f"?keywords={blog_name.replace(' ', '%20')}"
    )
    try:
        page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
        human_delay(2, 4)

        # Find first person result link
        links = page.query_selector_all("a.app-aware-link")
        for link in links:
            href = link.get_attribute("href") or ""
            if "/in/" in href and "linkedin.com" in href:
                return href.split("?")[0]
    except Exception as e:
        print(f"    Search error: {e}")
    return None


def get_latest_post(page, profile_url: str) -> Optional[dict]:
    """
    Visit a LinkedIn profile, go to their posts, return the latest post text + btn_index.
    """
    posts_url = profile_url.rstrip("/") + "/recent-activity/all/"
    try:
        page.goto(posts_url, wait_until="domcontentloaded", timeout=20000)
        human_delay(3, 5)

        for _ in range(3):
            page.evaluate("window.scrollBy(0, window.innerHeight * 1.5)")
            human_delay(1.5, 2.5)

        posts = page.evaluate("""() => {
            const boxes = document.querySelectorAll('[data-testid="expandable-text-box"]');
            const allCommentBtns = Array.from(document.querySelectorAll('button')).filter(b =>
                b.textContent.trim() === 'Comment' && b.offsetParent !== null
            );
            const results = [];
            for (const box of boxes) {
                const text = box.innerText.trim();
                if (text.length < 100) continue;
                let el = box;
                let commentBtn = null;
                for (let i = 0; i < 25; i++) {
                    el = el.parentElement;
                    if (!el || el.tagName === 'BODY') break;
                    const btns = Array.from(el.querySelectorAll('button')).filter(b =>
                        b.textContent.trim() === 'Comment' && b.offsetParent !== null
                    );
                    if (btns.length === 1) { commentBtn = btns[0]; break; }
                    if (btns.length > 4) break;
                }
                if (!commentBtn) continue;
                const btnIndex = allCommentBtns.indexOf(commentBtn);
                if (btnIndex === -1) continue;
                results.push({ text: text.substring(0, 800), btn_index: btnIndex });
                if (results.length >= 3) break;
            }
            return results;
        }""") or []

        if posts:
            return posts[0]  # latest post
    except Exception as e:
        print(f"    Post fetch error: {e}")
    return None


def post_comment(page, btn_index: int, comment_text: str) -> bool:
    """Click comment button and type + submit the comment."""
    try:
        # Click the comment button
        result = page.evaluate(f"""() => {{
            const btns = Array.from(document.querySelectorAll('button')).filter(b =>
                b.textContent.trim() === 'Comment' && b.offsetParent !== null
            );
            if (btns.length > {btn_index}) {{
                btns[{btn_index}].scrollIntoView({{block:'center'}});
                btns[{btn_index}].click();
                return true;
            }}
            return false;
        }}""")
        if not result:
            return False

        human_delay(1.5, 2.5)

        # Find the comment editor
        box = None
        for sel in ["[contenteditable='true']", "div[role='textbox']"]:
            try:
                page.wait_for_selector(sel, timeout=6000)
                candidates = page.query_selector_all(sel)
                for c in reversed(candidates):
                    if c.is_visible():
                        box = c
                        break
                if box:
                    break
            except PwTimeout:
                continue

        if not box:
            return False

        box.click()
        human_delay(0.3, 0.8)

        for char in comment_text:
            page.keyboard.type(char)
            time.sleep(random.uniform(0.04, 0.11))

        human_delay(1.5, 2.0)

        # Submit
        submitted = page.evaluate("""() => {
            const editor = document.querySelector('[contenteditable="true"]');
            if (!editor) return false;
            let el = editor;
            for (let i = 0; i < 12; i++) {
                el = el.parentElement;
                if (!el) break;
                const btns = Array.from(el.querySelectorAll('button')).filter(b =>
                    !b.disabled && b.textContent.trim() === 'Comment' && b.offsetParent !== null
                );
                if (btns.length > 0) { btns[btns.length-1].click(); return true; }
            }
            return false;
        }""")

        if submitted:
            human_delay(2, 3.5)
            return True

    except Exception as e:
        print(f"    Comment error: {e}")
    return False


def send_connection_request(page, profile_url: str, editor_name: str,
                             blog_name: str) -> bool:
    """Go to the profile and send a connection request with a note."""
    try:
        page.goto(profile_url, wait_until="domcontentloaded", timeout=20000)
        human_delay(2, 4)

        # Click Connect button
        connected = page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const connectBtn = btns.find(b =>
                b.textContent.trim() === 'Connect' && b.offsetParent !== null
            );
            if (connectBtn) { connectBtn.click(); return true; }
            return false;
        }""")

        if not connected:
            # Some profiles have Connect under "More" menu
            try:
                page.click("button[aria-label*='More actions']", timeout=3000)
                human_delay(0.5, 1)
                page.click("text=Connect", timeout=3000)
                human_delay(0.5, 1)
            except Exception:
                return False

        human_delay(1, 2)

        # Click "Add a note"
        try:
            page.click("button:has-text('Add a note')", timeout=5000)
            human_delay(0.5, 1)
        except PwTimeout:
            # Some flows skip straight to send
            pass

        # Type the note
        note_text = (
            f"Hi {editor_name or 'there'}, came across your work on {blog_name} — "
            f"really solid content. I run Grade Capital and Grade Institute of Finance "
            f"in India. Also sent you an email about a guest post idea. Would love to connect."
        )

        try:
            note_box = page.query_selector("textarea[name='message']")
            if note_box:
                note_box.click()
                human_delay(0.3, 0.6)
                for char in note_text[:300]:
                    page.keyboard.type(char)
                    time.sleep(random.uniform(0.03, 0.09))
                human_delay(1, 1.5)
        except Exception:
            pass

        # Send the request
        try:
            page.click("button:has-text('Send')", timeout=5000)
            human_delay(1.5, 2.5)
            return True
        except PwTimeout:
            return False

    except Exception as e:
        print(f"    Connection request error: {e}")
    return False


def run():
    if not LINKEDIN_SESSION.exists():
        print("No LinkedIn session found.")
        print(f"Expected at: {LINKEDIN_SESSION}")
        print("Run setup_session.py first.")
        return

    if not TARGETS_FILE.exists():
        print("No targets.json found. Run the GitHub pipeline first to generate targets.")
        return

    data = load_targets()
    new_targets = get_new_targets(data)

    if not new_targets:
        print("No new targets to warm up on LinkedIn.")
        return

    targets_to_process = new_targets[:MAX_PER_RUN]
    print(f"\n{'='*55}")
    print(f"  LinkedIn Guest Post Warm-up")
    print(f"  Processing {len(targets_to_process)} targets")
    print(f"{'='*55}\n")

    warmed = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled",
                  "--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            storage_state=str(LINKEDIN_SESSION),
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="Asia/Kolkata",
        )
        page = context.new_page()

        # Verify session
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=25000)
        human_delay(3, 5)
        if "authwall" in page.url or "login" in page.url:
            print("LinkedIn session expired. Re-run setup_session.py.")
            browser.close()
            return

        print("LinkedIn session active.\n")

        for target in targets_to_process:
            blog  = target["blog_name"]
            email = target["editor_email"]
            name  = target.get("editor_name", "")
            tid   = target["id"]

            print(f"Warming up: {blog} ({email})")

            # Step 1: Find editor on LinkedIn
            profile_url = search_linkedin_for_blog(page, blog)
            if not profile_url:
                print(f"  Could not find {blog} on LinkedIn — skipping warmup")
                # Still mark as warmed so we don't retry endlessly
                for t in data["targets"]:
                    if t["id"] == tid:
                        t["linkedin_warmed"] = True
                        t["notes"] = "LinkedIn profile not found"
                        break
                save_targets(data)
                continue

            print(f"  Profile: {profile_url}")

            # Step 2: Get their latest post
            post = get_latest_post(page, profile_url)
            if not post:
                print(f"  No recent posts found — skipping comment")
            else:
                print(f"  Post: {post['text'][:60]}...")
                comment = generate_warmup_comment(post["text"], blog)
                if comment:
                    print(f"  Comment: {comment[:80]}...")
                    # Navigate back to their activity and comment
                    page.goto(
                        profile_url.rstrip("/") + "/recent-activity/all/",
                        wait_until="domcontentloaded", timeout=20000
                    )
                    human_delay(3, 5)
                    for _ in range(2):
                        page.evaluate("window.scrollBy(0, window.innerHeight * 1.5)")
                        human_delay(1.5, 2.5)

                    # Refresh post list
                    fresh_posts = page.evaluate("""() => {
                        const boxes = document.querySelectorAll('[data-testid="expandable-text-box"]');
                        const allBtns = Array.from(document.querySelectorAll('button')).filter(b =>
                            b.textContent.trim() === 'Comment' && b.offsetParent !== null
                        );
                        for (const box of boxes) {
                            let el = box;
                            for (let i = 0; i < 25; i++) {
                                el = el.parentElement;
                                if (!el || el.tagName === 'BODY') break;
                                const btns = Array.from(el.querySelectorAll('button')).filter(b =>
                                    b.textContent.trim() === 'Comment' && b.offsetParent !== null
                                );
                                if (btns.length === 1) {
                                    return [{ btn_index: allBtns.indexOf(btns[0]) }];
                                }
                            }
                        }
                        return [];
                    }""") or []

                    if fresh_posts and fresh_posts[0]["btn_index"] >= 0:
                        success = post_comment(page, fresh_posts[0]["btn_index"], comment)
                        if success:
                            print(f"  ✅ Comment posted")
                        else:
                            print(f"  ⚠️  Comment failed")
                    human_delay(2, 4)

            # Step 3: Send connection request
            print(f"  Sending connection request...")
            connected = send_connection_request(page, profile_url, name, blog)
            print(f"  {'✅ Connection request sent' if connected else '⚠️  Connection request failed'}")

            # Mark as warmed
            for t in data["targets"]:
                if t["id"] == tid:
                    t["linkedin_warmed"] = True
                    t["linkedin_profile"] = profile_url
                    break
            save_targets(data)
            warmed += 1

            wait = random.randint(90, 150)
            print(f"  Waiting {wait}s before next target...\n")
            time.sleep(wait)

        browser.close()

    print(f"Done. {warmed} targets warmed up on LinkedIn.")


if __name__ == "__main__":
    run()
