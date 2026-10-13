"""
Adapters package and lookup factory.
"""

from __future__ import annotations

from typing import Any
from backend.app.scrapers.base import BaseSourceAdapter

from .amazon import AmazonAdapter
from .myntra import MyntraAdapter
from .flipkart import FlipkartAdapter
from .meesho import MeeshoAdapter
from .ajio import AjioAdapter
from .snapmint import SnapmintAdapter
from .indiamart import IndiamartAdapter
from .exportersindia import ExportersIndiaAdapter
from .alibaba import AlibabaAdapter
from .blinkit import BlinkitAdapter
from .swiggy_instamart import SwiggyInstamartAdapter
from .zepto import ZeptoAdapter
from .toing import ToingAdapter
from .google import GoogleSignalsAdapter
from .pinterest import PinterestAdapter
from .facebook_adlibrary import FacebookAdLibraryAdapter
from .reddit import RedditAdapter
from .x import XAdapter
from .instagram import InstagramAdapter
from .generic_custom import GenericCustomAdapter

_ADAPTER_CLASSES: dict[str, Any] = {
    "amazon": AmazonAdapter,
    "myntra": MyntraAdapter,
    "flipkart": FlipkartAdapter,
    "meesho": MeeshoAdapter,
    "ajio": AjioAdapter,
    "snapmint": SnapmintAdapter,
    "indiamart": IndiamartAdapter,
    "exportersindia": ExportersIndiaAdapter,
    "alibaba": AlibabaAdapter,
    "blinkit": BlinkitAdapter,
    "swiggy_instamart": SwiggyInstamartAdapter,
    "zepto": ZeptoAdapter,
    "toing": ToingAdapter,
    "google": GoogleSignalsAdapter,
    "pinterest": PinterestAdapter,
    "facebook": FacebookAdLibraryAdapter,
    "reddit": RedditAdapter,
    "x": XAdapter,
    "instagram": InstagramAdapter,
    "estay": lambda: GenericCustomAdapter("estay"),
}

_INSTANCES: dict[str, BaseSourceAdapter] = {}


def get_adapter(source_id: str) -> BaseSourceAdapter:
    clean_id = source_id.lower().strip()
    if clean_id not in _INSTANCES:
        factory = _ADAPTER_CLASSES.get(clean_id)
        if factory:
            _INSTANCES[clean_id] = factory()
        else:
            # Fallback to GenericCustomAdapter
            _INSTANCES[clean_id] = GenericCustomAdapter(clean_id)
    return _INSTANCES[clean_id]


__all__ = [
    "get_adapter",
    "AmazonAdapter",
    "MyntraAdapter",
    "FlipkartAdapter",
    "AjioAdapter",
    "SnapmintAdapter",
    "IndiamartAdapter",
    "ExportersIndiaAdapter",
    "AlibabaAdapter",
    "BlinkitAdapter",
    "SwiggyInstamartAdapter",
    "ZeptoAdapter",
    "ToingAdapter",
    "GoogleSignalsAdapter",
    "PinterestAdapter",
    "FacebookAdLibraryAdapter",
    "RedditAdapter",
    "XAdapter",
    "InstagramAdapter",
    "GenericCustomAdapter",
]
