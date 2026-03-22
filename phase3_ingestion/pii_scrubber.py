"""
Phase 3 — PII Scrubber

Strips personally identifiable information (PII) from review text
using regex patterns. Does NOT mutate input — returns new copies.

Patterns redacted:
    - Email addresses
    - Phone numbers (Indian 10-digit + international)
    - Sensitive URL tokens (URLs with keys/tokens/passwords)
    - UPI IDs

Usage:
    from phase3_ingestion.pii_scrubber import scrub_pii

    clean_reviews = scrub_pii(reviews)
"""

import re
from copy import deepcopy


# ═══════════════════════════════════════════════════════════════════════════════
#  PII Regex Patterns
# ═══════════════════════════════════════════════════════════════════════════════

_PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    # Email addresses: user@domain.com
    (
        "email",
        re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.IGNORECASE),
    ),
    # Indian phone numbers: +91 9876543210, 91-9876543210, 09876543210
    (
        "phone_indian",
        re.compile(r"(?:\+?91[\s\-]?)?0?[6-9]\d{9}\b"),
    ),
    # International phone numbers: +1-555-1234567, +44 7911 123456
    (
        "phone_intl",
        re.compile(r"\+\d{1,3}[\s\-]?\d{7,12}"),
    ),
    # UPI IDs: username@bank
    (
        "upi_id",
        re.compile(r"\b[\w.]+@(?:ybl|okhdfcbank|okicici|okaxis|oksbi|paytm|upi|apl|ibl)\b", re.IGNORECASE),
    ),
    # Sensitive URLs containing tokens, keys, passwords, or auth params
    (
        "sensitive_url",
        re.compile(
            r"https?://\S*(?:key|token|password|secret|auth|api_key|access_token)=\S+",
            re.IGNORECASE,
        ),
    ),
]

REDACTION_MARKER = "[REDACTED]"


# ═══════════════════════════════════════════════════════════════════════════════
#  Core Functions
# ═══════════════════════════════════════════════════════════════════════════════

def scrub_text(text: str) -> tuple[str, int]:
    """
    Apply all PII patterns to a single text string.

    Args:
        text: Raw text to scrub

    Returns:
        Tuple of (scrubbed_text, redaction_count)
    """
    total_redactions = 0

    for pattern_name, pattern in _PII_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            total_redactions += len(matches)
            text = pattern.sub(REDACTION_MARKER, text)

    return text, total_redactions


def scrub_pii(reviews: list[dict]) -> list[dict]:
    """
    Strip PII from the 'text' field of each review.

    Does NOT mutate the input list — returns new dicts with redacted copies.

    Args:
        reviews: List of review dicts (must have 'text' key)

    Returns:
        New list of review dicts with PII redacted
    """
    scrubbed = []
    total_redactions = 0

    for review in reviews:
        clean = deepcopy(review)

        # Scrub the text field
        if "text" in clean:
            clean["text"], count = scrub_text(clean["text"])
            total_redactions += count

        scrubbed.append(clean)

    if total_redactions > 0:
        print(f"  🔒 PII scrubbed: {total_redactions} redaction(s) applied")
    else:
        print(f"  ✅ No PII detected in {len(reviews)} reviews")

    return scrubbed


# ═══════════════════════════════════════════════════════════════════════════════
#  Standalone Execution & Demo
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("🧹 Phase 3b — PII Scrubber (Standalone Demo)")
    print("=" * 60)

    # Demo with synthetic PII-injected reviews
    test_reviews = [
        {
            "rating": 1,
            "text": "Terrible app! Contact me at john.doe@gmail.com for refund",
            "date": "2026-03-01",
        },
        {
            "rating": 2,
            "text": "My phone +91 9876543210 was charged incorrectly. Fix it!",
            "date": "2026-03-02",
        },
        {
            "rating": 3,
            "text": "Sent money to wrong UPI rahul.sharma@ybl please reverse",
            "date": "2026-03-03",
        },
        {
            "rating": 4,
            "text": "Great app, but call me at 08012345678 for partnership",
            "date": "2026-03-04",
        },
        {
            "rating": 5,
            "text": "Love this app! Best investment platform in India.",
            "date": "2026-03-05",
        },
        {
            "rating": 1,
            "text": "Check https://api.example.com?token=abc123&secret=xyz this bug",
            "date": "2026-03-06",
        },
    ]

    print(f"\n📊 Testing with {len(test_reviews)} synthetic reviews:\n")

    scrubbed = scrub_pii(test_reviews)

    for i, (orig, clean) in enumerate(zip(test_reviews, scrubbed)):
        changed = "🔴 REDACTED" if orig["text"] != clean["text"] else "🟢 Clean"
        print(f"  [{changed}] Review {i + 1}:")
        if orig["text"] != clean["text"]:
            print(f"    Before: {orig['text']}")
            print(f"    After : {clean['text']}")
        else:
            print(f"    Text  : {clean['text']}")
        print()

    # Verify no mutation
    assert test_reviews[0]["text"] == "Terrible app! Contact me at john.doe@gmail.com for refund", \
        "Original was mutated!"
    print("  ✅ Original data was NOT mutated (immutability check passed)")

    print("\n" + "=" * 60)
