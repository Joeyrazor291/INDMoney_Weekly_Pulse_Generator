"""
Phase 2 — Play Store Review Scraper

Fetches recent reviews for INDMoney from Google Play Store using the
`google-play-scraper` library (public API, no login required).

Usage:
    # As a module (called from main.py orchestrator)
    from phase2.scraper import fetch_reviews, save_reviews

    reviews = fetch_reviews(app_id="com.indmoney.indstocks", count=1000)
    path    = save_reviews(reviews, output_dir="data/raw")

    # Standalone
    python phase2/scraper.py
"""

import csv
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from google_play_scraper import Sort, reviews as gps_reviews


# ── Emoji removal pattern ────────────────────────────────────────────────────
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"  # dingbats
    "\U000024C2-\U0001F251"  # enclosed characters
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended-A
    "\U00002600-\U000026FF"  # misc symbols
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # zero-width joiner
    "\U000020E3"             # combining enclosing keycap
    "]+",
    flags=re.UNICODE,
)


def _strip_emojis(text: str) -> str:
    """Remove all emoji characters from text."""
    return _EMOJI_PATTERN.sub("", text).strip()


def _is_english(text: str, threshold: float = 0.7) -> bool:
    """
    Check if text is primarily English by verifying that at least
    `threshold` fraction of alphabetic characters are basic Latin (a-z).
    """
    alpha_chars = [c for c in text if c.isalpha()]
    if not alpha_chars:
        return False
    latin_count = sum(1 for c in alpha_chars if ord(c) < 128)
    return (latin_count / len(alpha_chars)) >= threshold


# ═══════════════════════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════════════════════

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds (exponential backoff: 2, 4, 8)
BATCH_SIZE = 200       # google-play-scraper fetches in batches internally


# ═══════════════════════════════════════════════════════════════════════════════
#  Field Mapping — Play Store → Internal Schema
# ═══════════════════════════════════════════════════════════════════════════════

MIN_WORD_COUNT = 5  # Reviews with fewer words are not useful for analysis


def _normalise_review(raw: dict) -> dict:
    """
    Map a single raw Play Store review dict to the internal schema.

    Play Store field → Internal field:
        score          → rating   (int 1–5)
        content        → text     (full review body)
        at (datetime)  → date     (ISO 8601 string)
        thumbsUpCount  → (dropped)
        reviewId       → (dropped — PII-adjacent)
        title          → (dropped — not available on Play Store)
    """
    review_date = raw.get("at")
    if isinstance(review_date, datetime):
        date_str = review_date.strftime("%Y-%m-%d")
    else:
        date_str = str(review_date) if review_date else ""

    return {
        "rating": raw.get("score", 0),
        "text": _strip_emojis(raw.get("content", "")),
        "date": date_str,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Core Functions
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_reviews(
    app_id: str = "com.indmoney.indstocks",
    count: int = 1000,
    lang: str = "en",
    country: str = "in",
) -> list[dict]:
    """
    Fetch the most recent reviews from Google Play Store.

    Uses `google-play-scraper` with Sort.NEWEST. Retries up to 3 times
    with exponential backoff on failure.

    Args:
        app_id:  Google Play app ID (default: com.indmoney.indstocks)
        count:   Maximum number of reviews to fetch (default: 1000)
        lang:    Language code (default: en)
        country: Country code (default: in)

    Returns:
        List of normalised review dicts with keys: rating, title, text, date

    Raises:
        RuntimeError: If all retries are exhausted.
    """
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"  🔄 Attempt {attempt}/{MAX_RETRIES}: Fetching {count} reviews "
                  f"for {app_id} (lang={lang}, country={country})...")

            result, _ = gps_reviews(
                app_id,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=count,
            )

            # Normalise each review to internal schema
            normalised = [_normalise_review(r) for r in result]

            # Drop reviews: empty, fewer than 5 words, or non-English
            before_count = len(normalised)
            normalised = [
                r for r in normalised
                if r["text"].strip()
                and len(r["text"].split()) >= MIN_WORD_COUNT
                and _is_english(r["text"])
            ]
            dropped = before_count - len(normalised)

            print(f"  ✅ Fetched {len(normalised)} reviews "
                  f"(dropped {dropped}: <{MIN_WORD_COUNT} words / empty / non-English)")

            return normalised

        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY ** attempt
                print(f"  ⚠️  Attempt {attempt} failed: {e}")
                print(f"      Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"  ❌ All {MAX_RETRIES} attempts failed.")

    raise RuntimeError(
        f"Failed to fetch reviews after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


def save_reviews(reviews: list[dict], output_dir: str | Path) -> tuple[str, str]:
    """
    Save normalised reviews to both JSON and CSV formats.

    Files are named with today's date:
        playstore_reviews_YYYYMMDD.json
        playstore_reviews_YYYYMMDD.csv

    Args:
        reviews:    List of normalised review dicts
        output_dir: Directory to write files into

    Returns:
        Tuple of (json_path, csv_path) as strings
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    date_stamp = datetime.now().strftime("%Y%m%d")
    base_name = f"playstore_reviews_{date_stamp}"

    # ── Save JSON ────────────────────────────────────────────────────────
    json_path = output_dir / f"{base_name}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(reviews, f, indent=2, ensure_ascii=False)
    print(f"  💾 JSON saved: {json_path} ({len(reviews)} reviews)")

    # ── Save CSV ─────────────────────────────────────────────────────────
    csv_path = output_dir / f"{base_name}.csv"
    if reviews:
        fieldnames = ["rating", "text", "date"]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(reviews)
        print(f"  💾 CSV saved : {csv_path} ({len(reviews)} rows)")
    else:
        print(f"  ⚠️  No reviews to write to CSV.")

    return str(json_path), str(csv_path)


def load_fallback_reviews(raw_dir: str | Path) -> list[dict]:
    """
    Fallback: Load the most recent reviews file from disk when
    scraping fails (e.g., network error, rate limiting).

    Looks for the newest .json or .csv file in raw_dir.

    Args:
        raw_dir: Directory containing previously saved review files

    Returns:
        List of review dicts, or empty list if no files found
    """
    raw_dir = Path(raw_dir)

    # Try JSON files first (preferred)
    json_files = sorted(raw_dir.glob("playstore_reviews_*.json"), reverse=True)
    if json_files:
        latest = json_files[0]
        print(f"  📂 Fallback: Loading from {latest.name}")
        with open(latest, "r", encoding="utf-8") as f:
            return json.load(f)

    # Fall back to CSV
    csv_files = sorted(raw_dir.glob("playstore_reviews_*.csv"), reverse=True)
    if csv_files:
        latest = csv_files[0]
        print(f"  📂 Fallback: Loading from {latest.name}")
        with open(latest, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    print("  ⚠️  No fallback review files found in data/raw/")
    return []


# ═══════════════════════════════════════════════════════════════════════════════
#  Standalone Execution
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Run the scraper standalone for testing."""
    # Add project root to path so we can import config
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root / "phase1_scaffold"))

    from config import load_config

    print("=" * 60)
    print("🏪 Phase 2 — Play Store Review Scraper (Standalone)")
    print("=" * 60)

    config = load_config()

    print(f"\n📱 App ID       : {config.app_id}")
    print(f"🔢 Review count : {config.review_count}")
    print(f"🌐 Lang/Country : {config.scraper_lang}/{config.scraper_country}")
    print()

    try:
        reviews = fetch_reviews(
            app_id=config.app_id,
            count=config.review_count,
            lang=config.scraper_lang,
            country=config.scraper_country,
        )
    except RuntimeError:
        print("\n🔄 Attempting fallback from local files...")
        reviews = load_fallback_reviews(config.data_raw_dir)

    if reviews:
        json_path, csv_path = save_reviews(reviews, config.data_raw_dir)

        # Print summary
        print(f"\n📊 Summary:")
        print(f"  Total reviews : {len(reviews)}")

        # Date range
        dates = [r["date"] for r in reviews if r["date"]]
        if dates:
            print(f"  Date range    : {min(dates)} → {max(dates)}")

        # Rating distribution
        from collections import Counter
        ratings = Counter(r["rating"] for r in reviews)
        print(f"  Ratings       : " + ", ".join(
            f"{'⭐' * k}: {v}" for k, v in sorted(ratings.items())
        ))

        # Sample review
        print(f"\n📝 Sample review:")
        sample = reviews[0]
        print(f"  Rating: {sample['rating']}⭐  |  Date: {sample['date']}")
        print(f"  Text  : {sample['text'][:120]}...")
    else:
        print("\n❌ No reviews available.")

    print("\n" + "=" * 60)
    print("✅ Phase 2 complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
