"""
Phase 3 — Data Ingestor

Loads scraped review data from JSON or CSV, normalises columns,
and applies a configurable date-window filter (default: last 8 weeks).

Usage:
    from phase3_ingestion.ingestor import ingest

    clean_reviews = ingest("data/raw/playstore_reviews_20260310.json", weeks_back=8)
"""

import json
import csv
from datetime import datetime, timedelta
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════════
#  Loading
# ═══════════════════════════════════════════════════════════════════════════════

def load_reviews(source_path: str | Path) -> list[dict]:
    """
    Auto-detect JSON or CSV format and load reviews into a list of dicts.

    Normalises column names to: rating, text, date
    (handles common aliases from different export sources).

    Args:
        source_path: Path to a .json or .csv file

    Returns:
        List of review dicts with keys: rating, text, date

    Raises:
        FileNotFoundError: If source_path does not exist
        ValueError: If file format is not .json or .csv
    """
    source_path = Path(source_path)

    if not source_path.exists():
        raise FileNotFoundError(f"Review file not found: {source_path}")

    suffix = source_path.suffix.lower()

    if suffix == ".json":
        return _load_json(source_path)
    elif suffix == ".csv":
        return _load_csv(source_path)
    else:
        raise ValueError(
            f"Unsupported file format: {suffix}. Expected .json or .csv"
        )


def _load_json(path: Path) -> list[dict]:
    """Load and normalise reviews from a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        raise ValueError("JSON file must contain a top-level array of reviews.")

    return [_normalise_columns(r) for r in raw]


def _load_csv(path: Path) -> list[dict]:
    """Load and normalise reviews from a CSV file."""
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [_normalise_columns(row) for row in reader]


# ── Column Aliases ───────────────────────────────────────────────────────────

_COLUMN_MAP = {
    # rating aliases
    "rating": "rating",
    "score": "rating",
    "stars": "rating",
    "star_rating": "rating",
    # text aliases
    "text": "text",
    "content": "text",
    "review": "text",
    "review_text": "text",
    "body": "text",
    # date aliases
    "date": "date",
    "at": "date",
    "review_date": "date",
    "created_at": "date",
    "timestamp": "date",
}


def _normalise_columns(row: dict) -> dict:
    """
    Map various column name conventions to the internal schema:
        rating (int), text (str), date (str YYYY-MM-DD)
    """
    normalised = {}

    for key, value in row.items():
        canonical = _COLUMN_MAP.get(key.lower().strip())
        if canonical and canonical not in normalised:
            normalised[canonical] = value

    # Ensure rating is int
    try:
        normalised["rating"] = int(float(normalised.get("rating", 0)))
    except (ValueError, TypeError):
        normalised["rating"] = 0

    # Ensure text is string
    normalised["text"] = str(normalised.get("text", ""))

    # Ensure date is string
    normalised["date"] = str(normalised.get("date", ""))

    return normalised


# ═══════════════════════════════════════════════════════════════════════════════
#  Date Filtering
# ═══════════════════════════════════════════════════════════════════════════════

def filter_by_date(reviews: list[dict], weeks_back: int = 8) -> list[dict]:
    """
    Keep only reviews within the last `weeks_back` weeks from today.

    Args:
        reviews:    List of review dicts (must have 'date' key)
        weeks_back: Number of weeks to look back (default: 8, max: 12)

    Returns:
        Filtered list of review dicts
    """
    cutoff = datetime.now() - timedelta(weeks=weeks_back)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    filtered = []
    for review in reviews:
        review_date = review.get("date", "")
        # Compare as strings (YYYY-MM-DD format sorts lexicographically)
        if review_date >= cutoff_str:
            filtered.append(review)

    return filtered


# ═══════════════════════════════════════════════════════════════════════════════
#  Full Ingestion Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def ingest(source_path: str | Path, weeks_back: int = 8) -> list[dict]:
    """
    Full ingestion pipeline: load → normalise.
    (Date filtering removed as per user request).

    Args:
        source_path: Path to .json or .csv review file
        weeks_back:  (Unused) Date window in weeks

    Returns:
        List of normalised review dicts
    """
    print(f"  📂 Loading reviews from: {source_path}")
    reviews = load_reviews(source_path)
    print(f"  📊 Loaded: {len(reviews)} reviews")

    print(f"  ✅ Returning all {len(reviews)} reviews (date filter disabled)")

    return reviews


# ═══════════════════════════════════════════════════════════════════════════════
#  Standalone Execution
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    from pathlib import Path as _Path

    project_root = _Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root / "phase1_scaffold"))

    from config import load_config

    print("=" * 60)
    print("📥 Phase 3a — Data Ingestor (Standalone)")
    print("=" * 60)

    config = load_config()

    # Find the most recent review file
    json_files = sorted(config.data_raw_dir.glob("playstore_reviews_*.json"), reverse=True)
    if not json_files:
        print("\n❌ No review files found in data/raw/. Run Phase 2 first.")
        sys.exit(1)

    source = json_files[0]
    reviews = ingest(str(source), weeks_back=config.weeks_back)

    if reviews:
        print(f"\n📊 Summary:")
        print(f"  Reviews in window : {len(reviews)}")
        dates = [r["date"] for r in reviews if r["date"]]
        if dates:
            print(f"  Date range        : {min(dates)} → {max(dates)}")

        from collections import Counter
        ratings = Counter(r["rating"] for r in reviews)
        print(f"  Rating breakdown  : " + ", ".join(
            f"{k}★: {v}" for k, v in sorted(ratings.items())
        ))
    else:
        print("\n⚠️  No reviews found within the date window.")

    print("\n" + "=" * 60)
