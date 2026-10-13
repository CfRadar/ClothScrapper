import sqlite3, json, sys

sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("backend/data/app.db")
r = conn.execute("SELECT result_json FROM runs WHERE id='6aee8a3e857541e79cc49b46ad0f9831'").fetchone()
data = json.loads(r[0])
for p in data.get("platforms", []):
    print(f"\n=================== {p['platform'].upper()} ===================")
    print("--- GENERATED TITLES ---")
    for t in p.get("titles", []):
        print(f"[{t.get('style')}] ({t.get('length')} chars): {t.get('title')}")
    print("\n--- TOP SCRAPED BESTSELLERS (Curated & Ranked) ---")
    for i, c in enumerate(p.get("top_scraped_titles", [])[:5], 1):
        print(f"#{i} [Rating: {c.get('rating')} | Reviews: {c.get('rating_count')} | Price: {c.get('price')}]: {c.get('title')}")
