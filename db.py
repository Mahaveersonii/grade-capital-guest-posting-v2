"""
db.py — Shared helpers to read/write targets.json (the pipeline's state file)

targets.json structure:
{
  "targets": [
    {
      "id": "md5_hash",
      "blog_name": "CryptoNews India",
      "blog_url": "https://cryptonewsindia.com",
      "guest_post_url": "https://cryptonewsindia.com/write-for-us",
      "editor_name": "",          # filled if found
      "editor_email": "editor@cryptonewsindia.com",
      "niche": "crypto",
      "status": "new",            # see STATUS_* below
      "found_date": "2026-05-01",
      "pitch_date": null,
      "follow_up_1_date": null,
      "follow_up_2_date": null,
      "breakup_date": null,
      "article_sent_date": null,
      "replied": false,
      "reply_type": null,         # "yes" | "decline" | "other"
      "topic_title": null,
      "topic_bullets": [],
      "alt_topic_title": null,
      "alt_topic_bullets": [],
      "linkedin_warmed": false,
      "notes": ""
    }
  ]
}
"""

import json
import hashlib
from pathlib import Path
from typing import Optional

DB_FILE = Path(__file__).parent / "targets.json"

# ── Status constants ───────────────────────────────────────────────────────────
STATUS_NEW           = "new"            # found, not yet emailed
STATUS_PITCHED       = "pitched"        # pitch email sent
STATUS_FOLLOW_UP_1   = "follow_up_1"   # follow-up 1 sent (day 5)
STATUS_FOLLOW_UP_2   = "follow_up_2"   # follow-up 2 sent (day 10)
STATUS_BREAKUP       = "breakup"        # break-up email sent (day 14)
STATUS_ARTICLE_SENT  = "article_sent"  # replied YES, article PDF sent
STATUS_DECLINED      = "declined"       # replied NO
STATUS_CLOSED        = "closed"         # no reply after breakup


def load() -> dict:
    if DB_FILE.exists():
        try:
            return json.loads(DB_FILE.read_text())
        except Exception:
            pass
    return {"targets": []}


def save(db: dict):
    DB_FILE.write_text(json.dumps(db, indent=2))


def get_all(db: dict) -> list:
    return db.get("targets", [])


def get_by_status(db: dict, *statuses) -> list:
    return [t for t in get_all(db) if t.get("status") in statuses]


def get_by_id(db: dict, target_id: str) -> Optional[dict]:
    for t in get_all(db):
        if t["id"] == target_id:
            return t
    return None


def already_have(db: dict, email: str) -> bool:
    """Return True if we already have a target with this email."""
    email_lower = email.lower()
    return any(t.get("editor_email", "").lower() == email_lower for t in get_all(db))


def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def add_target(db: dict, blog_name: str, blog_url: str, guest_post_url: str,
               editor_email: str, editor_name: str = "", niche: str = "crypto") -> bool:
    """Add a new target. Returns False if already exists."""
    from datetime import date
    if already_have(db, editor_email):
        return False
    target = {
        "id":                make_id(blog_url),
        "blog_name":         blog_name,
        "blog_url":          blog_url,
        "guest_post_url":    guest_post_url,
        "editor_name":       editor_name,
        "editor_email":      editor_email,
        "niche":             niche,
        "status":            STATUS_NEW,
        "found_date":        str(date.today()),
        "pitch_date":        None,
        "follow_up_1_date":  None,
        "follow_up_2_date":  None,
        "breakup_date":      None,
        "article_sent_date": None,
        "replied":           False,
        "reply_type":        None,
        "topic_title":       None,
        "topic_bullets":     [],
        "alt_topic_title":   None,
        "alt_topic_bullets": [],
        "linkedin_warmed":   False,
        "notes":             "",
    }
    db["targets"].append(target)
    return True


def update(db: dict, target_id: str, **kwargs):
    """Update fields on a target by id."""
    for t in db["targets"]:
        if t["id"] == target_id:
            t.update(kwargs)
            return


def days_since(date_str: Optional[str]) -> int:
    """Return how many days since a date string (YYYY-MM-DD). Returns 9999 if None."""
    if not date_str:
        return 9999
    from datetime import date
    try:
        d = date.fromisoformat(date_str)
        return (date.today() - d).days
    except Exception:
        return 9999
