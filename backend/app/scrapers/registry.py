"""
Registry loader and validator for sources.yaml.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger("backend.scrapers.registry")

HOSTNAME_REGEX = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*\.[A-Za-z]{2,63}$"
)

GroupType = Literal["B2C", "B2B", "Quick commerce", "Search and social", "Custom"]
KindType = Literal["marketplace", "b2b", "quickcommerce", "search", "social"]
RoleType = Literal["sell_target", "signal"]
RiskType = Literal["low", "medium", "high", "unknown"]
RelevanceType = Literal["high", "medium", "low", "none", "unknown"]


class SourceSpec(BaseModel):
    id: str
    label: str
    group: GroupType
    kind: KindType
    roles: list[RoleType] = Field(default_factory=list)
    default_enabled: bool = False
    ui_visible: bool = False
    tos_risk: RiskType = "medium"
    relevance: RelevanceType = "medium"
    requires: str | None = None
    hosts: list[str] = Field(default_factory=list)
    strategies: list[str] = Field(default_factory=list)
    url_templates: dict[str, str] = Field(default_factory=dict)
    selectors: dict[str, str] = Field(default_factory=dict)
    delay_min: int = 2
    delay_max: int = 5
    block_images: bool = True
    notes: str | None = None
    status_override: str | None = None
    status_reason: str | None = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(r"^[a-z0-9_]+$", clean):
            raise ValueError(f"Source ID '{v}' must be lowercase alphanumeric with underscores.")
        return clean

    @field_validator("hosts")
    @classmethod
    def validate_hosts(cls, hosts: list[str]) -> list[str]:
        cleaned = []
        for h in hosts:
            host_str = h.strip().lower()
            if host_str.startswith("*") or "://" in host_str or "/" in host_str:
                raise ValueError(f"Invalid host '{h}': wildcards, schemes, and paths are forbidden.")
            cleaned.append(host_str)
        return cleaned

    @model_validator(mode="after")
    def validate_security_rules(self) -> SourceSpec:
        # High risk sources must never be enabled by default
        if self.tos_risk == "high" and self.default_enabled:
            raise ValueError(f"High risk source '{self.id}' cannot be default_enabled: true.")
        return self


class SourcesRegistry(BaseModel):
    version: str = "1.0"
    sources: list[SourceSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_uniqueness(self) -> SourcesRegistry:
        seen = set()
        for src in self.sources:
            if src.id in seen:
                raise ValueError(f"Duplicate source ID in registry: '{src.id}'")
            seen.add(src.id)
        return self


_REGISTRY_CACHE: SourcesRegistry | None = None


def get_registry_path() -> Path:
    # Resolve relative to this module
    return Path(__file__).parent / "sources.yaml"


def load_registry(yaml_path: str | Path | None = None, force_reload: bool = False) -> SourcesRegistry:
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is not None and not force_reload:
        return _REGISTRY_CACHE

    target_path = Path(yaml_path) if yaml_path else get_registry_path()
    if not target_path.exists():
        raise FileNotFoundError(f"Sources registry file not found: {target_path}")

    with open(target_path, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f)

    registry = SourcesRegistry(**raw_data)
    _REGISTRY_CACHE = registry
    return registry


def get_source_spec(source_id: str) -> SourceSpec | None:
    registry = load_registry()
    for src in registry.sources:
        if src.id == source_id:
            return src
    return None


def get_allowlisted_hosts() -> set[str]:
    """
    Returns the dynamic set of allowlisted hostnames extracted from sources.yaml
    plus core required platform hosts.
    """
    registry = load_registry()
    hosts = {
        "openrouter.ai",
        "api.openrouter.ai",
    }
    for src in registry.sources:
        for host in src.hosts:
            if host:
                hosts.add(host.lower())
    return hosts
