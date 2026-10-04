#!/usr/bin/env python3
"""
scripts/inspect_db.py

Usage:
    python scripts/inspect_db.py
    python scripts/inspect_db.py --db-path ./backend/data/app.db

Description:
    Inspects the application's local SQLite database (managed via aiosqlite).
    Reports total row counts across core tables (cache, llm_usage, runs, scrape_log),
    active cached items by platform, and today's total LLM API calls grouped by model
    to monitor OpenRouter free-tier quotas.

Requirements:
    Standard Python 3 sqlite3 module (no external dependencies required).
"""

import sys
import os
import sqlite3
import argparse
from datetime import datetime, date

DEFAULT_DB_PATH = os.path.join(os.getcwd(), "backend", "data", "app.db")

def inspect_database(db_path: str):
    if not os.path.exists(db_path):
        print(f"[!] Database file does not exist at: {db_path}")
        print("    Ensure the backend has started or run migrations first.")
        sys.exit(0)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n" + "=" * 70)
    print(f"DATABASE INSPECTION: {db_path}")
    print(f"Current Local Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 1. Inspect Table Counts
    tables = ["cache", "llm_usage", "runs", "scrape_log"]
    print("\n[1] TABLE RECORD COUNTS:")
    for tbl in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
            count = cursor.fetchone()[0]
            print(f"  - {tbl:<16}: {count:>6} rows")
        except sqlite3.OperationalError:
            print(f"  - {tbl:<16}: [TABLE NOT INITIALIZED]")

    # 2. Inspect Cache Breakdown & Active Entries
    print("\n[2] ACTIVE 24H CACHE ENTRIES:")
    try:
        now_ts = int(datetime.now().timestamp())
        cursor.execute("""
            SELECT 
                SUBSTR(key, 1, INSTR(key, ':') - 1) as prefix,
                COUNT(*) as total,
                SUM(CASE WHEN created_at + ttl_seconds > ? THEN 1 ELSE 0 END) as valid
            FROM cache
            GROUP BY prefix
        """, (now_ts,))
        rows = cursor.fetchall()
        if rows:
            for prefix, total, valid in rows:
                print(f"  - Prefix '{prefix}': {valid or 0} active / {total} total")
        else:
            print("  (Cache table is empty)")
    except sqlite3.OperationalError as e:
        print(f"  Could not read cache: {e}")

    # 3. Inspect Today's LLM Quota Usage
    today_str = date.today().isoformat()
    print(f"\n[3] LLM QUOTA USAGE FOR TODAY ({today_str}):")
    try:
        cursor.execute("""
            SELECT model, count 
            FROM llm_usage 
            WHERE day = ?
            ORDER BY count DESC
        """, (today_str,))
        rows = cursor.fetchall()
        total_calls = sum(r[1] for r in rows) if rows else 0
        if rows:
            for model, count in rows:
                print(f"  - {model:<45}: {count:>4} calls")
            print(f"  Total Today: {total_calls} calls (OpenRouter free daily budget)")
        else:
            print(f"  Zero LLM calls recorded for {today_str}.")
    except sqlite3.OperationalError as e:
        print(f"  Could not read llm_usage: {e}")

    # 4. Recent Runs
    print("\n[4] RECENT RUNS (Last 5):")
    try:
        cursor.execute("""
            SELECT id, status, created_at 
            FROM runs 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        runs = cursor.fetchall()
        if runs:
            for run_id, status, created_at in runs:
                print(f"  - Run {run_id[:8]}... | Status: {status:<10} | Created: {created_at}")
        else:
            print("  (No runs logged yet)")
    except sqlite3.OperationalError as e:
        print(f"  Could not read runs: {e}")

    print("=" * 70 + "\n")
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="Inspect SQLite cache, runs, and daily LLM quota tables.")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, help="Path to SQLite database file")
    args = parser.parse_args()
    inspect_database(args.db_path)

if __name__ == "__main__":
    main()
