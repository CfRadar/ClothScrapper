import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.getcwd())

import aiosqlite
from backend.app.config import get_settings


async def main():
    parser = argparse.ArgumentParser(description="Inspect Marketplace Keyword Agent SQLite database")
    parser.add_argument("--reset-quota", action="store_true", help="Reset today's recorded LLM quota count")
    args = parser.parse_args()

    settings = get_settings()
    db_path = settings.DATABASE_PATH

    if not os.path.exists(db_path):
        print(f"Database file does not exist yet at: {db_path}")
        return

    async with aiosqlite.connect(db_path) as db:
        if args.reset_quota:
            await db.execute("DELETE FROM llm_usage")
            await db.commit()
            print("[SUCCESS] Cleared llm_usage table. Daily quota reset to full capacity.")

        # 1. Quota
        print("\n--- LLM USAGE (Quota) ---")
        async with db.execute("SELECT day, model, count FROM llm_usage ORDER BY day DESC") as cursor:
            rows = await cursor.fetchall()
            if not rows:
                print("  No LLM calls recorded yet.")
            for r in rows:
                print(f"  Day: {r[0]} | Model: {r[1]} | Calls: {r[2]}")

        # 2. Runs
        print("\n--- RECENT RUNS ---")
        async with db.execute("SELECT id, status, created_at FROM runs ORDER BY created_at DESC LIMIT 10") as cursor:
            rows = await cursor.fetchall()
            if not rows:
                print("  No runs recorded yet.")
            for r in rows:
                print(f"  Run ID: {r[0]} | Status: {r[1]} | Created: {r[2]}")

        # 3. Cache
        print("\n--- CACHE ENTRIES ---")
        async with db.execute("SELECT key, created_at, ttl_seconds FROM cache ORDER BY created_at DESC LIMIT 10") as cursor:
            rows = await cursor.fetchall()
            if not rows:
                print("  No cache entries found.")
            for r in rows:
                print(f"  Key: {r[0]} | TTL: {r[2]}s")


if __name__ == "__main__":
    asyncio.run(main())
