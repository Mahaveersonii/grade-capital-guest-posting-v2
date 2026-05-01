"""
config.py — All settings, templates, and search queries for Guest Posting v2
"""

import os

# ── API Keys (from GitHub Secrets / environment) ───────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SERPER_API_KEY    = os.environ["SERPER_API_KEY"]
SENDER_EMAIL      = os.environ["SENDER_EMAIL"]       # mahaveer@grade.capital
EMAIL_PASSWORD    = os.environ["EMAIL_PASSWORD"]     # Gmail app password

# ── Email config ───────────────────────────────────────────────────────────────
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
IMAP_HOST = "imap.gmail.com"

# ── Daily limits ───────────────────────────────────────────────────────────────
MAX_NEW_TARGETS_PER_DAY  = 8   # new blogs to find and add
MAX_PITCHES_PER_DAY      = 8   # pitch emails to send
MAX_FOLLOWUPS_PER_DAY    = 10  # follow-up emails to send

# ── Follow-up timing (days after pitch) ───────────────────────────────────────
FOLLOW_UP_1_DAYS  = 5
FOLLOW_UP_2_DAYS  = 10
BREAKUP_DAYS      = 14

# ── Author + brand ────────────────────────────────────────────────────────────
AUTHOR_NAME    = "Mahaveer Soni"
AUTHOR_TITLE   = "Founder, Grade Capital & Grade Institute of Finance"
AUTHOR_LINKEDIN = "linkedin.com/in/mahaveersoni"
AUTHOR_WEBSITE  = "grade.capital"
AUTHOR_BIO = (
    "Mahaveer Soni is the founder of Grade Capital — India's first professionally "
    "managed crypto derivatives fund — and Grade Institute of Finance (GIF), where "
    "over 2,000 students have been trained in crypto, blockchain, DeFi, and Web3. "
    "With 3+ years managing a live derivatives fund, he writes about crypto markets, "
    "regulation, blockchain infrastructure, and financial education in India."
)

GIF_CONTEXT = """
Grade Institute of Finance (GIF) is India's leading crypto and blockchain education platform.
We've trained 2,000+ students across India on crypto, blockchain, DeFi, Web3, and crypto regulation.
Our faculty are active practitioners — fund managers and blockchain developers, not academics.
We offer certification courses, bootcamps, and corporate training programs.
Grade Capital is our companion entity — India's first professionally managed crypto derivatives fund.
Key expertise areas: crypto regulation India (IFSCA, SEBI, FIU-IND), DeFi mechanics,
Bitcoin as an asset class, blockchain for finance, tokenization, Web3 education.
"""

# ── Domains to skip (don't accept guest posts or are too big/irrelevant) ──────
DOMAIN_BLOCKLIST = {
    "reddit.com", "twitter.com", "x.com", "facebook.com", "instagram.com",
    "linkedin.com", "youtube.com", "wikipedia.org", "quora.com", "amazon.com",
    "forbes.com", "techcrunch.com", "businessinsider.com", "huffpost.com",
    "entrepreneur.com", "inc.com", "wsj.com", "ft.com", "bloomberg.com",
    "coindesk.com", "cointelegraph.com", "decrypt.co", "theblock.co",
    "medium.com", "substack.com", "wordpress.com", "blogspot.com",
}

# ── Paid guest post indicators — skip if found on the write-for-us page ───────
PAID_INDICATORS = [
    "sponsored post", "paid post", "paid guest", "sponsored content",
    "sponsored article", "native advertising", "rate card", "pricing",
    "content marketing package", "advertise with us", "paid promotion",
    "publication fee", "editorial fee", "content fee", "placement fee",
    "do not accept free", "paid submissions only", "fee of $",
    "charge a fee", "we charge", "starting at $", "per post $",
    "sponsored by", "paid link", "paid collaboration",
]

# ── Indicators that confirm the blog is active and legit ──────────────────────
QUALITY_INDICATORS = [
    "write for us", "guest post guidelines", "submit article",
    "contribute", "become a contributor", "guest author",
    "accepting guest posts", "guest blog",
]

# ── Search queries — free guest posting in crypto/finance niche ───────────────
SEARCH_QUERIES = [
    # Core crypto/blockchain
    '"write for us" crypto blockchain -paid -sponsored -fee',
    '"guest post guidelines" bitcoin cryptocurrency blog India',
    '"submit article" blockchain DeFi web3 India -fee',
    '"accepting guest posts" cryptocurrency fintech India',
    '"contribute" crypto blockchain education blog India',
    '"write for us" bitcoin investing blog India free',
    '"become a contributor" DeFi web3 crypto blog',
    '"guest author" cryptocurrency blockchain finance India',

    # Finance/investing
    '"write for us" personal finance investing India blog',
    '"guest post" stock market cryptocurrency India -sponsored',
    '"contribute article" financial literacy India blog',
    '"submit a post" money investing blog India free',
    '"write for us" fintech startup India blog',
    '"guest post guidelines" investment finance India',

    # Broader crypto/web3 global
    '"write for us" cryptocurrency blog 2024 -paid',
    '"guest post" blockchain technology website free',
    '"write for us" DeFi protocol tokenization blog',
    '"accepting guest posts" web3 NFT crypto blog',
    '"submit" crypto fintech blog "no fee" OR "free" OR "complimentary"',

    # Education + crypto overlap
    '"write for us" financial education blog India',
    '"guest post" edtech fintech India free',
    '"contribute" crypto learning blog India',
    '"write for us" money investing young professionals India',

    # RWA / institutional
    '"write for us" tokenization RWA real estate blockchain',
    '"guest post" institutional crypto digital assets blog',
    '"contribute" fintech capital markets blockchain blog',
]

# ── Email templates ────────────────────────────────────────────────────────────

PITCH_EMAIL_TEMPLATE = """\
Hi {greeting},

{personalization}

I'd love to contribute a guest piece:

"{topic_title}"

It covers:
• {bullet_1}
• {bullet_2}
• {bullet_3}

About me: {author_name}, founder of Grade Capital (India's first crypto derivatives fund) \
and Grade Institute of Finance, where we've trained 2,000+ students on crypto and \
blockchain across India.

Would this work for {blog_name}?

Best,
{author_name}
{author_title}
{author_linkedin}
"""

FOLLOW_UP_1_TEMPLATE = """\
Hi {greeting},

Just checking if my previous email found you — inboxes get busy.

Still keen to contribute on:
"{topic_title}"

Happy to adjust the angle if needed.

Best,
{author_name}
"""

FOLLOW_UP_2_TEMPLATE = """\
Hi {greeting},

One more shot — here's a different angle that might suit {blog_name} better:

"{alt_topic_title}"

• {alt_bullet_1}
• {alt_bullet_2}
• {alt_bullet_3}

Worth a conversation?

{author_name}
"""

BREAKUP_TEMPLATE = """\
Hi {greeting},

I'll stop following up after this — don't want to clutter your inbox.

If the timing isn't right or the topics don't fit {blog_name}'s editorial calendar, \
completely understood.

The original idea is still open if you come back to it.

Best of luck with the blog,
{author_name}
"""

ARTICLE_DELIVERY_TEMPLATE = """\
Hi {greeting},

Excited to hear this works for {blog_name}!

I've attached the full article: "{topic_title}"

A few notes:
• Word count: ~1,800 words
• Written exclusively for {blog_name} — not published elsewhere
• Author bio included at the end — happy to adjust
• Images: can source or provide on request

Let me know if any edits are needed or if there's anything else you require.

Looking forward to seeing it live!

Best,
{author_name}
{author_title}
{author_linkedin}
"""

# ── LinkedIn warmup comment instruction (used by local linkedin_warmup.py) ────
LINKEDIN_COMMENT_INSTRUCTION = """
Write a LinkedIn comment as Mahaveer Soni (Grade Capital / Grade Institute of Finance founder).

The comment should:
1. Open with a sharp, specific opinion on the post content (2-3 sentences max)
2. End with one natural, non-spammy sentence mentioning you've emailed them about a guest post

Example ending: "Sent you an email today about contributing a piece on this — hope it's useful."
Or: "Also reached out via email about a guest article on a related angle — worth a look when you can."

Rules:
- No sycophantic openers ("Great post", "Love this")
- Don't start with "I"
- No hashtags, no emojis
- Sound like a practitioner, not a marketer
- The mention of the email must feel natural, not transactional
"""

LINKEDIN_CONNECTION_NOTE = (
    "Hi {name}, came across your work on {blog_name} — really solid content. "
    "I run Grade Capital and Grade Institute of Finance in India. "
    "Also sent you an email about a guest post idea. Would love to connect."
)
