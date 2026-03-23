"""
Phase 8 — Analytics History Manager

Responsible for maintaining a longitudinal JSON array of pipeline outputs
(`data/analytics_history.json`). Provides read/write access so the Web UI
can render historical charts (sentiment velocity, theme tracking).
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Path to the persistent data folder, assuming standard project structure
PROJECT_ROOT = Path(__file__).resolve().parent.parent
HISTORY_FILE = PROJECT_ROOT / "data" / "analytics_history.json"

def append_weekly_record(review_count: int, themes: list, avg_rating: float = 0.0):
    """
    Appends the current pipeline run metrics to the historical JSON array.
    """
    history = []
    
    # Load existing history if it exists
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        except json.JSONDecodeError:
            pass

    # Normalize theme data for persistence
    clean_themes = []
    for t in themes:
        if hasattr(t, "theme"):
            clean_themes.append({
                "theme": getattr(t, "theme", ""),
                "summary": getattr(t, "summary", ""),
                "quote": getattr(t, "quote", "")
            })
        elif isinstance(t, dict):
            clean_themes.append({
                "theme": t.get("theme", ""),
                "summary": t.get("summary", ""),
                "quote": t.get("quote", "")
            })

    # Create the timestamped record
    record = {
        "timestamp": datetime.now().isoformat(),
        "total_reviews": review_count,
        "avg_rating": avg_rating,
        "themes": clean_themes
    }

    history.append(record)
    
    os.makedirs(HISTORY_FILE.parent, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)
        
    print(f"  📈 Analytics: Appended week's record to {HISTORY_FILE.name}")


def get_analytics_history():
    """
    Retrieves the entire historical array to pass into the Web UI.
    Returns an empty list if no history exists yet.
    """
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []
