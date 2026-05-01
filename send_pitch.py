#!/usr/bin/env python3
"""
Step 2 — Send topic pitch emails to new targets.
Generates a personalised topic + 3 bullets using Claude, then sends
a short pitch email (NO PDF, NO article). Marks target as "pitched".
"""

import json
import time
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
from typing import Optional

import anthropic
import db
from config import (
    ANTHROPIC_API_KEY, SENDER_EMAIL, EMAIL_PASSWORD,
    SMTP_HOST, SMTP_PORT, MAX_PITCHES_PER_DAY,
    AUTHOR_NAME, AUTHOR_TITLE, AUTHOR_LINKEDIN,
    PITCH_EMAIL_TEMPLATE, GIF_CONTEXT,
)


def generate_pitch_content(blog_name: str, niche: str) -> Optional[dict]:
    """Use Claude to generate a personalised topic pitch. Returns dict or None."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""You are helping Mahaveer Soni pitch a guest post to "{blog_name}", a {niche} blog.

Context about who Mahaveer is:
{GIF_CONTEXT}

Generate a guest post pitch. Return ONLY valid JSON — no explanation, no markdown:
{{
  "topic_title": "Compelling article headline (under 70 chars)",
  "bullet_1": "First concrete takeaway from the article",
  "bullet_2": "Second concrete takeaway",
  "bullet_3": "Third concrete takeaway",
  "alt_topic_title": "Alternative headline for a follow-up pitch",
  "alt_bullet_1": "Alt article takeaway 1",
  "alt_bullet_2": "Alt article takeaway 2",
  "alt_bullet_3": "Alt article takeaway 3",
  "personalization": "One sentence showing you know this blog — reference the {niche} niche specifically. Do NOT be generic."
}}

Requirements:
- Topic MUST be about crypto, blockchain, DeFi, Web3, crypto regulation, or financial literacy in India
- Must be genuinely educational and valuable to a {niche} audience
- Angle should be specific and non-obvious — not something every blog has covered
- The alternative topic should be clearly different from the main topic
- Personalization must feel genuine, not templated"""

    for attempt in range(3):
        try:
            resp = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()
            # Strip markdown code fences if Claude adds them
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())
        except (json.JSONDecodeError, anthropic.RateLimitError) as e:
            wait = 20 * (attempt + 1)
            print(f"    Claude retry ({attempt+1}/3): {e} — waiting {wait}s")
            time.sleep(wait)
        except Exception as e:
            print(f"    Claude error: {e}")
            return None
    return None


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send plain-text email via Gmail SMTP."""
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


def send_pitches(db_data: dict, limit: int = MAX_PITCHES_PER_DAY) -> int:
    """
    Send pitch emails to targets with status STATUS_NEW.
    Returns number of pitches sent.
    """
    targets = db.get_by_status(db_data, db.STATUS_NEW)
    sent = 0

    for target in targets:
        if sent >= limit:
            break

        tid   = target["id"]
        email = target["editor_email"]
        name  = target.get("editor_name") or ""
        blog  = target["blog_name"]
        niche = target.get("niche", "crypto")

        print(f"  Pitching: {blog} <{email}>")

        # Generate personalised topic
        content = generate_pitch_content(blog, niche)
        if not content:
            print("    Could not generate pitch — skipping")
            continue

        greeting = name if name else "there"
        subject  = f"Guest post idea for {blog} — {content['topic_title']}"

        body = PITCH_EMAIL_TEMPLATE.format(
            greeting       = greeting,
            personalization= content["personalization"],
            topic_title    = content["topic_title"],
            bullet_1       = content["bullet_1"],
            bullet_2       = content["bullet_2"],
            bullet_3       = content["bullet_3"],
            author_name    = AUTHOR_NAME,
            blog_name      = blog,
            author_title   = AUTHOR_TITLE,
            author_linkedin= AUTHOR_LINKEDIN,
        )

        success = send_email(email, subject, body)

        if success:
            db.update(
                db_data, tid,
                status          = db.STATUS_PITCHED,
                pitch_date      = str(date.today()),
                topic_title     = content["topic_title"],
                topic_bullets   = [content["bullet_1"], content["bullet_2"], content["bullet_3"]],
                alt_topic_title = content["alt_topic_title"],
                alt_topic_bullets = [content["alt_bullet_1"], content["alt_bullet_2"], content["alt_bullet_3"]],
            )
            db.save(db_data)
            sent += 1
            print(f"    ✅ Sent pitch: \"{content['topic_title']}\"")
            # Human-paced delay between sends
            time.sleep(random.uniform(4, 8))
        else:
            print(f"    ❌ Failed to send pitch")

    return sent


if __name__ == "__main__":
    print("Sending pitch emails...")
    data = db.load()
    n = send_pitches(data)
    print(f"\nDone. {n} pitches sent.")
