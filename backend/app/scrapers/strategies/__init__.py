"""
Strategy package for scraper strategy ladder:
1. suggest_endpoint
2. embedded_json
3. network_capture
4. dom_selectors
5. heuristics
"""

from .suggest_endpoint import fetch_suggestions
from .embedded_json import extract_embedded_json
from .network_capture import capture_network_json
from .dom_selectors import parse_dom
from .heuristics import parse_heuristics

__all__ = [
    "fetch_suggestions",
    "extract_embedded_json",
    "capture_network_json",
    "parse_dom",
    "parse_heuristics",
]
