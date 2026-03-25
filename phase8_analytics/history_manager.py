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

def append_weekly_record(review_count: int, themes: list, avg_rating: float = 0.0, timestamp_override: str = None):
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
                "count": getattr(t, "count", 1),
                "quote": getattr(t, "quote", ""),
                "tickets": getattr(t, "tickets", []) if hasattr(t, "tickets") else []
            })
        elif isinstance(t, dict):
            clean_themes.append({
                "theme": t.get("theme", ""),
                "summary": t.get("summary", ""),
                "count": t.get("count", 1),
                "quote": t.get("quote", ""),
                "tickets": t.get("tickets", [])
            })

    # Create the timestamped record
    timestamp = timestamp_override if timestamp_override else datetime.now().isoformat()
    record = {
        "timestamp": timestamp,
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

def add_ticket_to_theme(timestamp: str, theme_name: str, ticket_description: str):
    """
    Finds a record by timestamp and a theme by name, then appends a ticket.
    """
    if not HISTORY_FILE.exists():
        return False
    
    try:
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
        
        updated = False
        for record in history:
            if record.get("timestamp") == timestamp:
                for theme in record.get("themes", []):
                    if theme.get("theme") == theme_name:
                        if "tickets" not in theme:
                            theme["tickets"] = []
                        theme["tickets"].append(ticket_description)
                        updated = True
                        break
            if updated:
                break
        
        if updated:
            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f, indent=2)
            return True
    except Exception as e:
        print(f"Error adding ticket: {e}")
        
    return False
