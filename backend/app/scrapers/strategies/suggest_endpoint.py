"""
Strategy 1: Public Suggestion / JSON Autocomplete API.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote_plus

import httpx
from backend.app.net.safe_http import SafeAsyncClient
from backend.app.scrapers.registry import SourceSpec

logger = logging.getLogger("backend.scrapers.strategies.suggest_endpoint")


async def execute_suggest_strategy(spec: SourceSpec, query: str) -> list[str]:
    """
    Executes Strategy 1: lightweight HTTP query to public suggestion endpoints.
    """
    template = spec.url_templates.get("suggest")
    if not template:
        return []

    url = template.format(query=quote_plus(query))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }

    try:
        async with SafeAsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return []

            data = resp.json()
            suggestions: list[str] = []

            # Handle Google / Firefox format: ["query", ["s1", "s2", ...]]
            if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
                for item in data[1]:
                    if isinstance(item, str):
                        suggestions.append(item.strip())
                return suggestions

            # Handle Amazon format: {"suggestions": [{"value": "..."}, ...]}
            if isinstance(data, dict):
                s_list = data.get("suggestions", data.get("data", []))
                for s in s_list:
                    if isinstance(s, dict):
                        val = s.get("value", s.get("query", ""))
                        if val:
                            suggestions.append(val.strip())
                    elif isinstance(s, str):
                        suggestions.append(s.strip())
                return suggestions

            return []
    except Exception as e:
        logger.debug(f"Strategy 1 (suggest) failed for {spec.id}: {e}")
        return []


fetch_suggestions = execute_suggest_strategy
