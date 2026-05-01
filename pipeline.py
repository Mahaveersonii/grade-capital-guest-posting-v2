#!/usr/bin/env python3
"""
pipeline.py — Master orchestrator. Run this daily via GitHub Actions.

Order of execution:
  1. Check replies   → send articles to anyone who said YES (time-sensitive)
  2. Send follow-ups → scheduled follow-up / break-up emails
  3. Find targets    → discover new free guest posting blogs
  4. Send pitches    → send topic pitch emails to new targets
"""

import sys
from datetime import datetime

import db
import check_replies
import follow_ups
import find_targets
import send_pitch


def run():
    start = datetime.now()
    print(f"\n{'='*60}")
    print(f"  Guest Posting Pipeline — {start:%d %b %Y %H:%M UTC}")
    print(f"{'='*60}\n")

    data = db.load()
    total = len(db.get_all(data))
    print(f"Database: {total} total targets\n")

    # ── Step 1: Check replies first (highest priority) ─────────────────────────
    print("── Step 1: Checking replies ──────────────────────────────────")
    try:
        articles_sent = check_replies.check_and_respond(data)
        data = db.load()  # reload after mutations
        print(f"   Articles sent: {articles_sent}\n")
    except Exception as e:
        print(f"   ⚠️  Reply check failed: {e}\n")
        articles_sent = 0

    # ── Step 2: Send follow-ups ────────────────────────────────────────────────
    print("── Step 2: Follow-up emails ──────────────────────────────────")
    try:
        followups_sent = follow_ups.send_follow_ups(data)
        data = db.load()
        print(f"   Follow-ups sent: {followups_sent}\n")
    except Exception as e:
        print(f"   ⚠️  Follow-ups failed: {e}\n")
        followups_sent = 0

    # ── Step 3: Find new targets ───────────────────────────────────────────────
    print("── Step 3: Finding new free blogs ───────────────────────────")
    try:
        found = find_targets.find_new_targets(data)
        data = db.load()
        print(f"   New targets added: {found}\n")
    except Exception as e:
        print(f"   ⚠️  Target finding failed: {e}\n")
        found = 0

    # ── Step 4: Send pitch emails ──────────────────────────────────────────────
    print("── Step 4: Sending pitch emails ──────────────────────────────")
    try:
        pitched = send_pitch.send_pitches(data)
        data = db.load()
        print(f"   Pitches sent: {pitched}\n")
    except Exception as e:
        print(f"   ⚠️  Pitching failed: {e}\n")
        pitched = 0

    # ── Summary ────────────────────────────────────────────────────────────────
    elapsed = (datetime.now() - start).seconds
    print(f"{'='*60}")
    print(f"  Run complete in {elapsed}s")
    print(f"  Articles sent : {articles_sent}")
    print(f"  Follow-ups    : {followups_sent}")
    print(f"  New targets   : {found}")
    print(f"  Pitches sent  : {pitched}")
    print(f"  DB total      : {len(db.get_all(db.load()))} targets")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run()
