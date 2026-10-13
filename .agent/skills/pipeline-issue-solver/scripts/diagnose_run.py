"""
Diagnostic script for inspecting the latest pipeline run from SQLite database.
Prints run status, stage durations, LLM usage, generated titles, and competitor rankings.
"""

import json
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")

def diagnose_latest_run(db_path: str = "backend/data/app.db") -> None:
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT id, status, brief_json, result_json, created_at FROM runs ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            print("No runs found in database.")
            return

        run_id, status, brief_json, result_json, created_at = row
        print(f"=== RUN DIAGNOSTIC: {run_id} ===")
        print(f"Timestamp: {created_at}")
        print(f"Status:    {status}")

        if brief_json:
            brief = json.loads(brief_json)
            print(f"Brief:     {brief.get('color')} {brief.get('tshirt_type')} | Platforms: {brief.get('platforms')}")

        if result_json:
            res = json.loads(result_json)
            platforms = res.get("platforms", [])
            print(f"Platforms in Result: {len(platforms)}")
            for p in platforms:
                p_name = p.get("platform")
                titles = p.get("titles", [])
                comps = p.get("top_scraped_titles", [])
                print(f"\n--- Platform: {p_name.upper()} ---")
                print(f"Titles Generated: {len(titles)}")
                for t in titles:
                    print(f"  [{t.get('style')}] ({t.get('length')} chars): {t.get('title')}")
                print(f"Top Competitors: {len(comps)}")
                for c in comps[:3]:
                    print(f"  #{c.get('rank')} [{c.get('rating')}* | {c.get('rating_count')} revs | {c.get('price')}]: {c.get('title')[:60]}")
    except Exception as e:
        print(f"Error diagnosing run: {e}")

if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "backend/data/app.db"
    diagnose_latest_run(db)
