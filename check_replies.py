#!/usr/bin/env python3
"""
Step 3 — Check Gmail for replies from pitched targets.
  YES / INTERESTED → generate article, build PDF, send Email 2 with attachment
  DECLINE / NO     → mark as declined
"""

import imaplib
import email as email_lib
import smtplib
import time
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import date
from typing import Optional

import db
from config import (
    SENDER_EMAIL, EMAIL_PASSWORD,
    SMTP_HOST, SMTP_PORT, IMAP_HOST,
    AUTHOR_NAME, AUTHOR_TITLE, AUTHOR_LINKEDIN,
    ARTICLE_DELIVERY_TEMPLATE,
)
from article_writer import generate_article_pdf


# ── Reply classification ───────────────────────────────────────────────────────
YES_SIGNALS = [
    "yes", "sure", "sounds good", "love it", "great idea", "interested",
    "please send", "send it", "send over", "go ahead", "we'd love",
    "we would love", "happy to", "looking forward", "let's do it",
    "that works", "perfect", "absolutely", "definitely", "send the",
    "i like", "we like", "great topic", "good idea", "sounds interesting",
    "go for it", "please proceed", "approved",
]

DECLINE_SIGNALS = [
    "no thank", "not interested", "not a fit", "don't accept",
    "do not accept", "not accepting", "not looking", "full",
    "editorial calendar is full", "not right", "pass",
    "unfortunately", "regret", "not suitable", "doesn't fit",
    "doesn't align", "won't work", "not what", "not what we",
]


def classify_reply(body: str) -> str:
    """Return 'yes', 'decline', or 'unknown'."""
    lower = body.lower()
    if any(s in lower for s in YES_SIGNALS):
        return "yes"
    if any(s in lower for s in DECLINE_SIGNALS):
        return "decline"
    return "unknown"


def get_email_body(msg) -> str:
    """Extract plain-text body from an email.Message object."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                try:
                    return part.get_payload(decode=True).decode("utf-8", errors="ignore")
                except Exception:
                    pass
    else:
        try:
            return msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        except Exception:
            pass
    return ""


def fetch_replies(pitched_emails: set) -> list:
    """
    Connect to Gmail IMAP, scan inbox for replies from pitched targets.
    Returns list of dicts: {from_email, subject, body}
    """
    results = []
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(SENDER_EMAIL, EMAIL_PASSWORD)
        mail.select("INBOX")

        _, data = mail.search(None, "ALL")
        ids = data[0].split()

        # Check last 200 emails (performance limit)
        for msg_id in ids[-200:]:
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)

            from_header = msg.get("From", "")
            from_email  = email_lib.utils.parseaddr(from_header)[1].lower()

            if from_email not in pitched_emails:
                continue

            subject = msg.get("Subject", "")
            body    = get_email_body(msg)
            results.append({"from_email": from_email, "subject": subject, "body": body})

        mail.logout()
    except Exception as e:
        print(f"  IMAP error: {e}")

    return results


def send_article_email(to_email: str, editor_name: str, blog_name: str,
                        topic_title: str, pdf_bytes: bytes) -> bool:
    """Send Email 2 — the article PDF as an attachment."""
    greeting = editor_name if editor_name else "there"
    subject  = f"Re: Guest post — article attached ({topic_title[:50]})"
    body = ARTICLE_DELIVERY_TEMPLATE.format(
        greeting    = greeting,
        blog_name   = blog_name,
        topic_title = topic_title,
        author_name     = AUTHOR_NAME,
        author_title    = AUTHOR_TITLE,
        author_linkedin = AUTHOR_LINKEDIN,
    )

    # Safe filename for attachment
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in topic_title)[:50]
    filename = f"{safe_title}.pdf"

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = to_email
    msg.attach(MIMEText(body, "plain"))

    part = MIMEBase("application", "octet-stream")
    part.set_payload(pdf_bytes)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)

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


def check_and_respond(db_data: dict) -> int:
    """
    Main function: check for replies, respond with article if YES.
    Returns number of article emails sent.
    """
    # Build index: email → target
    pitched = db.get_by_status(
        db_data,
        db.STATUS_PITCHED, db.STATUS_FOLLOW_UP_1,
        db.STATUS_FOLLOW_UP_2,
    )
    if not pitched:
        print("  No pitched targets to check.")
        return 0

    email_index = {t["editor_email"].lower(): t for t in pitched}
    pitched_emails = set(email_index.keys())

    print(f"  Checking replies for {len(pitched_emails)} targets...")
    replies = fetch_replies(pitched_emails)
    print(f"  Found {len(replies)} relevant emails in inbox.")

    article_sent = 0

    for reply in replies:
        from_email = reply["from_email"]
        target = email_index.get(from_email)
        if not target:
            continue

        # Skip if already processed
        if target.get("replied"):
            continue

        classification = classify_reply(reply["body"])
        tid   = target["id"]
        blog  = target["blog_name"]
        name  = target.get("editor_name", "")
        topic = target.get("topic_title", "")
        niche = target.get("niche", "crypto")

        print(f"  Reply from {blog} ({from_email}): {classification.upper()}")

        if classification == "yes":
            # Generate article and send PDF
            bullets = target.get("topic_bullets", [])
            try:
                pdf_bytes = generate_article_pdf(topic, bullets, blog, niche)
            except Exception as e:
                print(f"    Article generation failed: {e}")
                db.update(db_data, tid, replied=True, reply_type="yes",
                          notes=f"Article gen failed: {e}")
                db.save(db_data)
                continue

            success = send_article_email(from_email, name, blog, topic, pdf_bytes)

            if success:
                db.update(
                    db_data, tid,
                    replied          = True,
                    reply_type       = "yes",
                    status           = db.STATUS_ARTICLE_SENT,
                    article_sent_date= str(date.today()),
                )
                db.save(db_data)
                article_sent += 1
                print(f"    ✅ Article sent to {blog}")
                time.sleep(random.uniform(5, 10))
            else:
                print(f"    ❌ Failed to send article to {blog}")

        elif classification == "decline":
            db.update(db_data, tid, replied=True, reply_type="decline",
                      status=db.STATUS_DECLINED)
            db.save(db_data)
            print(f"    Marked as declined.")

        else:
            # Unknown reply — log it but don't act
            db.update(db_data, tid, replied=True, reply_type="other",
                      notes=reply["body"][:200])
            db.save(db_data)
            print(f"    Unclear reply — logged for manual review.")

    return article_sent


if __name__ == "__main__":
    print("Checking for replies...")
    data = db.load()
    n = check_and_respond(data)
    print(f"\nDone. {n} articles sent.")
