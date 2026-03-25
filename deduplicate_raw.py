import os
import glob
from pathlib import Path
from datetime import datetime
import collections

def deduplicate_raw_data(data_dir="data/raw"):
    """
    Groups raw playstore review files by ISO week and keeps only the latest 
    instance per week.
    """
    print(f"🔍 Checking for duplicate raw files in {data_dir}...")
    
    # Path to the raw directory
    raw_path = Path(data_dir)
    if not raw_path.exists():
        print(f"  ❌ Directory {data_dir} not found.")
        return

    # Find all playstore_reviews_*.json files
    json_files = list(raw_path.glob("playstore_reviews_*.json"))
    
    if not json_files:
        print("  ✅ No raw JSON files found.")
        return

    # Group files by ISO Week (Year, WeekNumber)
    # Using a dictionary: (year, week) -> List of Path objects
    weeks_map = collections.defaultdict(list)
    
    for f in json_files:
        # Extract date from filename: playstore_reviews_YYYYMMDD.json
        date_str = f.stem.split("_")[-1]
        try:
            date_obj = datetime.strptime(date_str, "%Y%m%d")
            # isocalendar returns (year, week, weekday)
            iso_year, iso_week, _ = date_obj.isocalendar()
            weeks_map[(iso_year, iso_week)].append(f)
        except ValueError:
            print(f"  ⚠️ Skipping file with invalid date format: {f.name}")
            continue

    deleted_count = 0
    
    # Process each week
    for (year, week), files in weeks_map.items():
        if len(files) > 1:
            # Sort by date string in filename (descending) to get the latest one
            files.sort(key=lambda x: x.stem.split("_")[-1], reverse=True)
            
            latest_file = files[0]
            redundant_files = files[1:]
            
            print(f"  📅 Week {year}-W{week}: Keeping {latest_file.name}, cleaning up {len(redundant_files)} duplicates.")
            
            for rf in redundant_files:
                # Delete the JSON
                try:
                    rf.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"    ❌ Error deleting {rf.name}: {e}")
                
                # Delete the corresponding CSV if it exists
                csv_file = rf.with_suffix(".csv")
                if csv_file.exists():
                    try:
                        csv_file.unlink()
                    except Exception as e:
                        print(f"    ❌ Error deleting {csv_file.name}: {e}")

    if deleted_count > 0:
        print(f"✨ Successfully deleted {deleted_count} duplicate files.")
    else:
        print("✅ No duplicates found. One file per week verified.")

if __name__ == "__main__":
    # Adjust default path if running from subdirectories
    PROJECT_ROOT = Path(__file__).resolve().parent
    DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw"
    
    deduplicate_raw_data(data_dir=DEFAULT_RAW_DIR)
