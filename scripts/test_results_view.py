import json
import os
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\anura\.gemini\antigravity-ide\brain\1e10aa62-9fe7-4557-a0f1-6195bb0951ab"

# Mock completed run result to store directly into sessionStorage so the UI renders it
sample_result = {
    "run_id": "test_run_12345",
    "target_market_summary": "Gen-Z & Young Adults (18-28), Streetwear & Anime Aesthetic Enthusiasts",
    "platforms": [
        {
            "platform": "amazon",
            "keywords": [
                "oversized graphic t-shirt for men",
                "black drop shoulder streetwear tee",
                "cotton 240 gsm printed t-shirt",
                "anime graphic oversized tee",
                "loose fit casual crew neck tshirt",
                "heavyweight vintage wash graphic t-shirt",
                "skater style baggy graphic tee"
            ],
            "titles": [
                {
                    "style": "search",
                    "title": "UrbanAura Unisex Oversized Black 100% Cotton 240 GSM Graphic Print Round Neck Half Sleeve Casual Streetwear T-Shirt",
                    "length": 118,
                    "parts": [
                        {"label": "brand", "text": "UrbanAura"},
                        {"label": "gender", "text": "Unisex"},
                        {"label": "fit", "text": "Oversized"},
                        {"label": "color", "text": "Black"},
                        {"label": "fabric", "text": "100% Cotton 240 GSM"},
                        {"label": "pattern", "text": "Graphic Print"},
                        {"label": "neck", "text": "Round Neck"},
                        {"label": "sleeve", "text": "Half Sleeve"},
                        {"label": "occasion", "text": "Casual Streetwear"},
                        {"label": "tshirt_type", "text": "T-Shirt"}
                    ]
                },
                {
                    "style": "balanced",
                    "title": "UrbanAura Unisex Oversized Black Graphic Print 100% Cotton Casual Streetwear T-Shirt",
                    "length": 84,
                    "parts": [
                        {"label": "brand", "text": "UrbanAura"},
                        {"label": "gender", "text": "Unisex"},
                        {"label": "fit", "text": "Oversized"},
                        {"label": "color", "text": "Black"},
                        {"label": "pattern", "text": "Graphic Print"},
                        {"label": "fabric", "text": "100% Cotton"},
                        {"label": "occasion", "text": "Casual Streetwear"},
                        {"label": "tshirt_type", "text": "T-Shirt"}
                    ]
                },
                {
                    "style": "short",
                    "title": "UrbanAura Unisex Oversized Black Graphic Print T-Shirt",
                    "length": 53,
                    "parts": [
                        {"label": "brand", "text": "UrbanAura"},
                        {"label": "gender", "text": "Unisex"},
                        {"label": "fit", "text": "Oversized"},
                        {"label": "color", "text": "Black"},
                        {"label": "pattern", "text": "Graphic Print"},
                        {"label": "tshirt_type", "text": "T-Shirt"}
                    ]
                }
            ],
            "details": {
                "attributes_to_fill": ["Fit Type: Oversized", "Material: 100% Cotton", "Pattern: Graphic Print", "GSM: 240"],
                "price_band": "₹599 - ₹899",
                "negative_keywords": ["cheap", "polyester", "formal", "slim fit"],
                "hashtags_or_tags": ["#streetwear", "#oversizedtee", "#graphictees", "#animefashion"],
                "competition_note": "High search volume on drop shoulder and heavy GSM terms. Differentiate with fabric weight callout.",
                "seasonality_note": "Year-round demand; peaks during college reopening and festive discount sales."
            }
        },
        {
            "platform": "myntra",
            "keywords": [
                "oversized graphic print t-shirt",
                "black drop shoulder cotton tee",
                "streetwear baggy fit round neck tshirt",
                "unisex printed casual tee"
            ],
            "titles": [
                {
                    "style": "search",
                    "title": "UrbanAura Unisex Black Oversized Graphic Streetwear T-Shirt",
                    "length": 58,
                    "parts": [
                        {"label": "brand", "text": "UrbanAura"},
                        {"label": "gender", "text": "Unisex"},
                        {"label": "color", "text": "Black"},
                        {"label": "fit", "text": "Oversized"},
                        {"label": "pattern", "text": "Graphic"},
                        {"label": "occasion", "text": "Streetwear"},
                        {"label": "tshirt_type", "text": "T-Shirt"}
                    ]
                },
                {
                    "style": "balanced",
                    "title": "UrbanAura Unisex Black Oversized Graphic T-Shirt",
                    "length": 47,
                    "parts": [
                        {"label": "brand", "text": "UrbanAura"},
                        {"label": "gender", "text": "Unisex"},
                        {"label": "color", "text": "Black"},
                        {"label": "fit", "text": "Oversized"},
                        {"label": "pattern", "text": "Graphic"},
                        {"label": "tshirt_type", "text": "T-Shirt"}
                    ]
                },
                {
                    "style": "short",
                    "title": "UrbanAura Unisex Black Oversized T-Shirt",
                    "length": 39,
                    "parts": [
                        {"label": "brand", "text": "UrbanAura"},
                        {"label": "gender", "text": "Unisex"},
                        {"label": "color", "text": "Black"},
                        {"label": "fit", "text": "Oversized"},
                        {"label": "tshirt_type", "text": "T-Shirt"}
                    ]
                }
            ],
            "details": {
                "attributes_to_fill": ["Style: Streetwear", "Sleeve: Half Sleeve", "Neck: Round Neck"],
                "price_band": "₹699 - ₹999",
                "negative_keywords": ["polyester", "polo", "regular fit"],
                "hashtags_or_tags": ["#myntrastreetwear", "#oversizeddrop"],
                "competition_note": "Visual imagery and clean title case format required by Myntra catalog guidelines.",
                "seasonality_note": "Strong steady trend with surge in end-of-reason sales."
            }
        },
        {
            "platform": "flipkart",
            "keywords": [
                "black oversized t shirt men graphic",
                "cotton drop shoulder printed tshirt",
                "loose fit streetwear tshirt black"
            ],
            "titles": [
                {
                    "style": "search",
                    "title": "UrbanAura Printed Unisex Oversized Black Round Neck T-Shirt",
                    "length": 58,
                    "parts": [
                        {"label": "brand", "text": "UrbanAura"},
                        {"label": "pattern", "text": "Printed"},
                        {"label": "gender", "text": "Unisex"},
                        {"label": "fit", "text": "Oversized"},
                        {"label": "color", "text": "Black"},
                        {"label": "neck", "text": "Round Neck"},
                        {"label": "tshirt_type", "text": "T-Shirt"}
                    ]
                },
                {
                    "style": "balanced",
                    "title": "UrbanAura Printed Unisex Oversized Black T-Shirt",
                    "length": 47,
                    "parts": [
                        {"label": "brand", "text": "UrbanAura"},
                        {"label": "pattern", "text": "Printed"},
                        {"label": "gender", "text": "Unisex"},
                        {"label": "fit", "text": "Oversized"},
                        {"label": "color", "text": "Black"},
                        {"label": "tshirt_type", "text": "T-Shirt"}
                    ]
                },
                {
                    "style": "short",
                    "title": "UrbanAura Unisex Oversized Black T-Shirt",
                    "length": 39,
                    "parts": [
                        {"label": "brand", "text": "UrbanAura"},
                        {"label": "gender", "text": "Unisex"},
                        {"label": "fit", "text": "Oversized"},
                        {"label": "color", "text": "Black"},
                        {"label": "tshirt_type", "text": "T-Shirt"}
                    ]
                }
            ],
            "details": {
                "attributes_to_fill": ["Neck: Round Neck", "Pattern: Printed", "Ideal For: Unisex"],
                "price_band": "₹499 - ₹749",
                "negative_keywords": ["formal", "nylon"],
                "hashtags_or_tags": ["#flipkartfashion"],
                "competition_note": "Value-focused pricing with high conversion on clear attribute filters.",
                "seasonality_note": "High festive volume in Big Billion Days."
            }
        },
        {
            "platform": "meesho",
            "keywords": [
                "black oversized tshirt unisex printed",
                "fancy drop shoulder cotton tshirt",
                "streetwear loose tshirt under 500"
            ],
            "titles": [
                {
                    "style": "search",
                    "title": "UrbanAura Trendy Unisex Black Oversized Graphic Print Round Neck Half Sleeve Casual T-Shirt",
                    "length": 90,
                    "parts": [
                        {"label": "brand", "text": "UrbanAura"},
                        {"label": "key_feature", "text": "Trendy"},
                        {"label": "gender", "text": "Unisex"},
                        {"label": "color", "text": "Black"},
                        {"label": "fit", "text": "Oversized"},
                        {"label": "pattern", "text": "Graphic Print"},
                        {"label": "neck", "text": "Round Neck"},
                        {"label": "sleeve", "text": "Half Sleeve"},
                        {"label": "occasion", "text": "Casual"},
                        {"label": "tshirt_type", "text": "T-Shirt"}
                    ]
                },
                {
                    "style": "balanced",
                    "title": "UrbanAura Trendy Unisex Black Oversized Graphic Print T-Shirt",
                    "length": 60,
                    "parts": [
                        {"label": "brand", "text": "UrbanAura"},
                        {"label": "key_feature", "text": "Trendy"},
                        {"label": "gender", "text": "Unisex"},
                        {"label": "color", "text": "Black"},
                        {"label": "fit", "text": "Oversized"},
                        {"label": "pattern", "text": "Graphic Print"},
                        {"label": "tshirt_type", "text": "T-Shirt"}
                    ]
                },
                {
                    "style": "short",
                    "title": "UrbanAura Unisex Black Oversized T-Shirt",
                    "length": 39,
                    "parts": [
                        {"label": "brand", "text": "UrbanAura"},
                        {"label": "gender", "text": "Unisex"},
                        {"label": "color", "text": "Black"},
                        {"label": "fit", "text": "Oversized"},
                        {"label": "tshirt_type", "text": "T-Shirt"}
                    ]
                }
            ],
            "details": {
                "attributes_to_fill": ["Fabric: Cotton", "Sleeve: Half Sleeve", "Color: Black"],
                "price_band": "₹349 - ₹549",
                "negative_keywords": ["dry clean only", "expensive"],
                "hashtags_or_tags": ["#meeshofinds", "#resellers", "#oversized"],
                "competition_note": "Reseller discovery prioritizes descriptive simple keywords and aggressive price points.",
                "seasonality_note": "High continuous demand with reseller catalogs."
            }
        }
    ],
    "llm_calls_used": 2,
}

from backend.app.schemas import ProductBrief
from backend.app.titles.curated_titles import extract_top_scraped_titles

brief_obj = ProductBrief(
    platforms=["amazon", "myntra", "flipkart", "meesho"],
    tshirt_type="oversized graphic t-shirt",
    color="black",
    gender="unisex",
    fit="oversized",
    fabric="100% cotton 240 GSM",
    neck="round neck",
    sleeve="half sleeve",
    print_or_design="graphic print",
    occasion="casual streetwear",
    brand_name="UrbanAura",
)

for plat_item in sample_result["platforms"]:
    comps = extract_top_scraped_titles(plat_item["platform"], brief_obj, None)
    plat_item["top_scraped_titles"] = [c.model_dump() for c in comps]

def capture_results():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="msedge")
        context = browser.new_context(viewport={"width": 1440, "height": 950})
        page = context.new_page()

        page.goto("http://localhost:5173", wait_until="networkidle")

        # Inject sample run into sessionStorage
        storage_payload = {
            "runId": "test_run_12345",
            "runToken": "mock_token_abc123",
            "result": sample_result
        }
        page.evaluate(f"sessionStorage.setItem('mka.last_run.v1', JSON.stringify({json.dumps(storage_payload)}));")

        # Reload to let useRun pick it up
        page.reload(wait_until="networkidle")
        time.sleep(1)

        # 1. Capture results view in light mode
        res_light = os.path.join(ARTIFACT_DIR, "single_page_results_light.png")
        page.screenshot(path=res_light)
        print(f"Captured results light mode: {res_light}")

        # 2. Capture results view in dark mode
        theme_btn = page.locator("button[aria-label='Toggle theme']")
        if theme_btn.count() > 0:
            theme_btn.click()
            time.sleep(0.5)
            res_dark = os.path.join(ARTIFACT_DIR, "single_page_results_dark.png")
            page.screenshot(path=res_dark)
            print(f"Captured results dark mode: {res_dark}")

        browser.close()
        print("Results capture complete!")

if __name__ == "__main__":
    capture_results()
