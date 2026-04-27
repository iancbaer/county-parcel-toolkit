"""Public source discovery helpers.

The goal of this module is to move common source discovery out of agent judgment
and into deterministic, inspectable code. It starts with ArcGIS Online Sharing
REST search because many counties publish parcel layers there.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ARCGIS_SEARCH_ENDPOINT = "https://www.arcgis.com/sharing/rest/search"
PARCEL_TERMS = (
    "parcel",
    "parcels",
    "assessor",
    "assessment",
    "property",
    "tax parcel",
    "taxpayer",
    "cadastral",
    "land use",
)
NON_SOURCE_TERMS = ("pdf", "map", "dashboard", "storymap", "web map", "web mapping application")


@dataclass
class ArcGISSearchResult:
    """A ranked ArcGIS Online search candidate."""

    title: str
    item_id: str
    owner: str
    item_type: str
    url: str
    tags: list[str] = field(default_factory=list)
    snippet: str = ""
    score: int = 0
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def arcgis_search_url(query: str, limit: int = 10) -> str:
    """Build an ArcGIS Sharing REST search URL for public source discovery."""

    params = {
        "f": "json",
        "q": query,
        "num": limit,
        "sortField": "relevance",
        "sortOrder": "desc",
    }
    return f"{ARCGIS_SEARCH_ENDPOINT}?{urlencode(params)}"


def _fetch_json(url: str) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": "county-parcel-toolkit/0.1 discovery"})
    with urlopen(req, timeout=60) as response:  # nosec B310 - public discovery URL
        return json.loads(response.read().decode("utf-8"))


def _item_url(item: dict[str, Any]) -> str:
    url = str(item.get("url") or "")
    if url:
        return url
    item_id = str(item.get("id") or "")
    return f"https://www.arcgis.com/home/item.html?id={item_id}" if item_id else ""


def parse_arcgis_search_results(payload: dict[str, Any]) -> list[ArcGISSearchResult]:
    """Convert ArcGIS search JSON into normalized result objects."""

    results: list[ArcGISSearchResult] = []
    for item in payload.get("results", []):
        results.append(
            ArcGISSearchResult(
                title=str(item.get("title") or ""),
                item_id=str(item.get("id") or ""),
                owner=str(item.get("owner") or ""),
                item_type=str(item.get("type") or ""),
                url=_item_url(item),
                tags=[str(tag) for tag in item.get("tags", [])],
                snippet=str(item.get("snippet") or item.get("description") or ""),
            )
        )
    return results


def _haystack(result: ArcGISSearchResult) -> str:
    return " ".join([result.title, result.item_type, result.url, result.snippet, " ".join(result.tags)]).lower()


def rank_arcgis_results(results: list[ArcGISSearchResult]) -> list[ArcGISSearchResult]:
    """Score and sort ArcGIS candidates by likely usefulness as parcel sources."""

    ranked: list[ArcGISSearchResult] = []
    for result in results:
        score = 0
        reasons: list[str] = []
        haystack = _haystack(result)
        item_type = result.item_type.lower()
        url = result.url.lower()

        if item_type == "feature service" or "featureserver" in url:
            score += 70
            reasons.append("feature_service")
        elif "service" in item_type:
            score += 35
            reasons.append("service")

        parcel_hits = [term for term in PARCEL_TERMS if term in haystack]
        if parcel_hits:
            score += 20 + min(30, 5 * len(parcel_hits))
            reasons.append("parcel_signal")

        if "assessor" in haystack or "tax parcel" in haystack:
            score += 15
            reasons.append("assessor_signal")

        if any(term in item_type.lower() for term in ("pdf", "web map", "dashboard")):
            score -= 25
            reasons.append("less_direct_item_type")
        if any(term in haystack for term in NON_SOURCE_TERMS) and "feature_service" not in reasons:
            score -= 10
            reasons.append("possible_documentation_or_viewer")

        ranked.append(
            ArcGISSearchResult(
                title=result.title,
                item_id=result.item_id,
                owner=result.owner,
                item_type=result.item_type,
                url=result.url,
                tags=result.tags,
                snippet=result.snippet,
                score=score,
                reasons=reasons,
            )
        )

    return sorted(ranked, key=lambda item: (-item.score, item.title.lower(), item.item_id))


def discover_arcgis_sources(query: str, limit: int = 10) -> list[ArcGISSearchResult]:
    """Search ArcGIS Online and return ranked likely parcel-data source candidates."""

    payload = _fetch_json(arcgis_search_url(query, limit=limit))
    if "error" in payload:
        raise RuntimeError(json.dumps(payload["error"]))
    return rank_arcgis_results(parse_arcgis_search_results(payload))
