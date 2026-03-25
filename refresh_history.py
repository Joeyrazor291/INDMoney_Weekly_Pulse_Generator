import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Imports from project
from phase1_scaffold.config import load_config
from phase4_theme_engine.openrouter_client import OpenRouterClient
from phase4_theme_engine.engine import analyze_reviews
from phase8_analytics.history_manager import append_weekly_record, HISTORY_FILE

def refresh_history():
    print("🧹 Refreshing Analytics History...")
    
    # 1. Clear existing history
    if HISTORY_FILE.exists():
        print(f"  🗑️  Clearing existing history at {HISTORY_FILE}")
        with open(HISTORY_FILE, "w") as f:
            json.dump([], f)
    
    # 2. Load config and router
    config = load_config()
    router = OpenRouterClient(api_key=config.openrouter_api_key, model=config.openrouter_model)
    
    # 3. Find raw files
    raw_dir = config.data_raw_dir
    raw_files = sorted(list(raw_dir.glob("*.json")))
    
    if not raw_files:
        print("  ⚠️  No raw JSON files found in data/raw/")
        return

    print(f"  📂 Found {len(raw_files)} weekly files to process.")

    # 4. Process each file
    for raw_path in raw_files:
        print(f"\n📦 Processing {raw_path.name}...")
        
        with open(raw_path, "r") as f:
            reviews = json.load(f)
        
        # Analyze ALL reviews for accurate counts
        theme_reviews = reviews
        
        print(f"  🎨 Running theme engine on {len(theme_reviews)} reviews...")
        theme_result = analyze_reviews(router, theme_reviews)
        
        if theme_result and theme_result.themes:
            # Note: theme_result.themes now have .count
            print(f"  ✅ Appending record for {raw_path.name}...")
            
            # Use file date as timestamp if possible, otherwise now
            date_str = raw_path.stem.split("_")[-1]
            try:
                timestamp = datetime.strptime(date_str, "%Y%m%d").isoformat()
            except:
                timestamp = datetime.now().isoformat()

            append_weekly_record(
                review_count=len(reviews),
                themes=theme_result.themes,
                avg_rating=0.0,
                timestamp_override=timestamp
            )
        else:
            print(f"  ⚠️  No themes generated for {raw_path.name}")

    print("\n✨ Refresh Complete! History now contains full volume records.")

if __name__ == "__main__":
    refresh_history()
