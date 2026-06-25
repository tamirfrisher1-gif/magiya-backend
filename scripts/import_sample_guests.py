"""
Imports the mock guest dataset (data/sample_guests.csv) into Supabase.
Useful for demos and testing without needing real guest data yet.

Run with: python scripts/import_sample_guests.py
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.guests import import_guests_from_list

INPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "sample_guests.csv"


def main() -> None:
    with open(INPUT_FILE, encoding="utf-8") as f:
        guests = list(csv.DictReader(f))

    result = import_guests_from_list(guests)
    print(f"Inserted {result['inserted']} guests, skipped {len(result['skipped'])}.")
    if result["skipped"]:
        for item in result["skipped"]:
            print(f"  Skipped ({item['reason']}): {item['row']}")


if __name__ == "__main__":
    main()
