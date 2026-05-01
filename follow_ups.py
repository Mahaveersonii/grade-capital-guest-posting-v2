#!/usr/bin/env python3
"""
Step 4 — Send timed follow-up emails.

Schedule:
  Day 5  after pitch → Follow-up 1 (gentle check-in)
  Day 10 after pitch → Follow-up 2 (alternative topic angle)
  Day 14 after pitch → Break-up email (final close)
"""

import time
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date

import db
from config import (
    SENDER_EMAIL, EMAIL_PASSWORD, SMTP_HOST, SMTP_PORT,
    MAX_FOLLOWUPS_PER_DAY,
    AUTHOR_NAME, AUTHOR_TITLE, AUTHOR_LINKEDIN,
    FOLLOW_UP_1_TEMPLATE, FOLLOW_UP_2_TEMPLATE, BREAKUP_TEMPLATE,
    FOLLOW_UP_1_DAYS, FOLLOW_UP_2_DAYS, BREAKUP_DAYS,
)


def send_plain_email(to_email: str, subject: str, body: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = to_email
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(SENDER_EMAIL, EMAIL_PASSWORD)
            smtp.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"    SMTP error: {e}")
        return False


def send_follow_ups(db_data: dict, limit: int = MAX_FOLLOWUPS_PER_DAY) -> int:
    """Send follow-ups based on days elapsed since last email. Returns count sent."""
    sent = 0
    today = str(date.today())

    # ── Follow-up 1 (day 5 since pitch, not yet replied) ──────────────────────
    candidates_1 = [
        t for t in db.get_by_status(db_data, db.STATUS_PITCHED)
        if not t.get("replied")
        and db.days_since(t.get("pitch_date")) >= FOLLOW_UP_1_DAYS
    ]
    for t in candidates_1:
        if sent >= limit:
            break
        greeting = t.get("editor_name") or "there"
        subject  = f"Re: Guest post idea for {t['blog_name']} — {t.get('topic_title','')}"
        body = FOLLOW_UP_1_TEMPLATE.format(
            greeting    = greeting,
            topic_title = t.get("topic_title", "the article"),
            author_name = AUTHOR_NAME,
        )
        ok = send_plain_email(t["editor_email"], subject, body)
        if ok:
            db.update(db_data, t["id"], status=db.STATUS_FOLLOW_UP_1,
                      follow_up_1_date=today)
            db.save(db_data)
            sent += 1
            print(f"  ✅ Follow-up 1 → {t['blog_name']}")
            time.sleep(random.uniform(4, 8))

    # ── Follow-up 2 (day 10 since pitch, or day 5 since follow-up 1) ──────────
    candidates_2 = [
        t for t in db.get_by_status(db_data, db.STATUS_FOLLOW_UP_1)
        if not t.get("replied")
        and db.days_since(t.get("pitch_date")) >= FOLLOW_UP_2_DAYS
    ]
    for t in candidates_2:
        if sent >= limit:
            break
        greeting     = t.get("editor_name") or "there"
        alt_title    = t.get("alt_topic_title", t.get("topic_title", "an alternative angle"))
        alt_bullets  = t.get("alt_topic_bullets", [])
        subject      = f"Re: Guest post for {t['blog_name']} — alternate idea"
        body = FOLLOW_UP_2_TEMPLATE.format(
            greeting        = greeting,
            blog_name       = t["blog_name"],
            alt_topic_title = alt_title,
            alt_bullet_1    = alt_bullets[0] if len(alt_bullets) > 0 else "Key insight 1",
            alt_bullet_2    = alt_bullets[1] if len(alt_bullets) > 1 else "Key insight 2",
            alt_bullet_3    = alt_bullets[2] if len(alt_bullets) > 2 else "Key insight 3",
            author_name     = AUTHOR_NAME,
        )
        ok = send_plain_email(t["editor_email"], subject, body)
        if ok:
            db.update(db_data, t["id"], status=db.STATUS_FOLLOW_UP_2,
                      follow_up_2_date=today)
            db.save(db_data)
            sent += 1
            print(f"  ✅ Follow-up 2 → {t['blog_name']}")
            time.sleep(random.uniform(4, 8))

    # ── Break-up email (day 14 since pitch) ───────────────────────────────────
    candidates_b = [
        t for t in db.get_by_status(db_data, db.STATUS_FOLLOW_UP_2)
        if not t.get("replied")
        and db.days_since(t.get("pitch_date")) >= BREAKUP_DAYS
    ]
    for t in candidates_b:
        if sent >= limit:
            break
        greeting = t.get("editor_name") or "there"
        subject  = f"Re: Guest post — closing the loop ({t['blog_name']})"
        body = BREAKUP_TEMPLATE.format(
            greeting    = greeting,
            blog_name   = t["blog_name"],
            author_name = AUTHOR_NAME,
        )
        ok = send_plain_email(t["editor_email"], subject, body)
        if ok:
            db.update(db_data, t["id"], status=db.STATUS_BREAKUP,
                      breakup_date=today)
            db.save(db_data)
            sent += 1
            print(f"  ✅ Break-up email → {t['blog_name']}")
            time.sleep(random.uniform(4, 8))

    # ── Mark no-reply-after-breakup as closed ─────────────────────────────────
    stale = [
        t for t in db.get_by_status(db_data, db.STATUS_BREAKUP)
        if not t.get("replied")
        and db.days_since(t.get("breakup_date")) >= 7
    ]
    for t in stale:
        db.update(db_data, t["id"], status=db.STATUS_CLOSED)
    if stale:
        db.save(db_data)
        print(f"  Closed {len(stale)} unresponsive targets.")

    return sent


if __name__ == "__main__":
    print("Processing follow-ups...")
    data = db.load()
    n = send_follow_ups(data)
    print(f"\nDone. {n} follow-up emails sent.")
