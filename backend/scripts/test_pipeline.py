import httpx
import json
import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

async def test():
    async with httpx.AsyncClient(timeout=180.0) as client:
        brief = {
            "tshirt_type": "Oversized",
            "color": "Black",
            "details": "Anime Graphic Heavy Cotton",
            "platforms": ["amazon", "myntra", "flipkart", "meesho"],
            "research_sources": ["google", "pinterest", "reddit"]
        }
        r = await client.post("http://127.0.0.1:8000/api/runs", json=brief)
        print("Post run status:", r.status_code)
        if r.status_code not in (200, 201):
            print("Response:", r.text)
            return
        data = r.json()
        run_id = data["run_id"]
        run_token = data["run_token"]
        print(f"Streaming run_id: {run_id}")

        headers = {"X-Run-Token": run_token}
        result_payload = {}
        async with client.stream("GET", f"http://127.0.0.1:8000/api/runs/{run_id}/events", headers=headers) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    raw = line[5:].strip()
                    if not raw or raw.startswith("[DONE]"):
                        continue
                    try:
                        evt = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    evt_type = evt.get("type")
                    stage = evt.get("stage")
                    msg = evt.get("message", "")
                    payload = evt.get("payload") or evt.get("data") or {}
                    if msg:
                        print(f"[{stage}] {evt_type}: {msg}")
                    if evt_type == "result":
                        result_payload = payload
                    if evt_type in ("done", "error"):
                        print(f"\n=== FINISHED with type={evt_type} ===")
                        if evt_type == "error":
                            print("Error details:", payload)
                        else:
                            platforms = result_payload.get("platforms", [])
                            print(f"Total platforms in result: {len(platforms)}")
                            for p in platforms:
                                p_name = p.get("platform")
                                print(f"\n--- Platform: {p_name.upper()} ---")
                                titles = p.get("titles", [])
                                for t in titles:
                                    print(f"  Title ({t.get('style')}, {t.get('length')} chars): {t.get('title')}")
                                kws = p.get("keywords", [])
                                print(f"  Keywords ({len(kws)} items): {', '.join(kws[:6])}...")
                                comps = p.get("top_scraped_titles", [])
                                print(f"  Top Scraped Competitors count: {len(comps)}")
                                for idx, c in enumerate(comps[:3], 1):
                                    print(f"    #{idx} [{c.get('rating')}* | {c.get('rating_count')} revs | {c.get('price')}]: {c.get('title')[:65]}")
                        break

if __name__ == "__main__":
    asyncio.run(test())
