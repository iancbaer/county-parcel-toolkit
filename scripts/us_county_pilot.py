#!/usr/bin/env python3
"""Run a lightweight one-county-per-state parcel-source pilot.

This is intentionally stdlib-only. It searches ArcGIS Online for likely public
county parcel/assessor FeatureServer/MapServer layers, exports a bounded sample,
profiles fields, infers canonical mappings, and writes a machine-readable report.

It does not scrape parcel search pages, bypass access controls, or download full
county datasets unless --full is explicitly provided.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from county_parcel_toolkit.mapper import infer_field_map, profile_csv
from county_parcel_toolkit.normalize import normalize_csv

# Largest/recognizable county-equivalent per state. These are test targets, not
# a final priority list. DC is included separately because it is a useful
# county-equivalent property-data jurisdiction.
DEFAULT_TARGETS = [
    ("AL", "Jefferson County"),
    ("AK", "Anchorage Municipality"),
    ("AZ", "Maricopa County"),
    ("AR", "Pulaski County"),
    ("CA", "Los Angeles County"),
    ("CO", "Denver County"),
    ("CT", "Fairfield County"),
    ("DE", "New Castle County"),
    ("FL", "Miami-Dade County"),
    ("GA", "Fulton County"),
    ("HI", "Honolulu County"),
    ("ID", "Ada County"),
    ("IL", "Cook County"),
    ("IN", "Marion County"),
    ("IA", "Polk County"),
    ("KS", "Johnson County"),
    ("KY", "Jefferson County"),
    ("LA", "East Baton Rouge Parish"),
    ("ME", "Cumberland County"),
    ("MD", "Montgomery County"),
    ("MA", "Middlesex County"),
    ("MI", "Wayne County"),
    ("MN", "Hennepin County"),
    ("MS", "Hinds County"),
    ("MO", "St. Louis County"),
    ("MT", "Yellowstone County"),
    ("NE", "Douglas County"),
    ("NV", "Clark County"),
    ("NH", "Hillsborough County"),
    ("NJ", "Bergen County"),
    ("NM", "Bernalillo County"),
    ("NY", "Kings County"),
    ("NC", "Wake County"),
    ("ND", "Cass County"),
    ("OH", "Cuyahoga County"),
    ("OK", "Oklahoma County"),
    ("OR", "Multnomah County"),
    ("PA", "Philadelphia County"),
    ("RI", "Providence County"),
    ("SC", "Greenville County"),
    ("SD", "Minnehaha County"),
    ("TN", "Shelby County"),
    ("TX", "Harris County"),
    ("UT", "Salt Lake County"),
    ("VT", "Chittenden County"),
    ("VA", "Fairfax County"),
    ("WA", "King County"),
    ("WV", "Kanawha County"),
    ("WI", "Milwaukee County"),
    ("WY", "Laramie County"),
    ("DC", "District of Columbia"),
]

PARCEL_TERMS = "parcel OR parcels OR assessor OR taxlot OR cadastre OR property"
RELEVANT_TERMS = (
    "parcel",
    "parcels",
    "tax parcel",
    "taxparcel",
    "taxlot",
    "tax lot",
    "assessment",
    "assessor",
    "cadastral",
    "cadastre",
    "property",
    "real property",
)
NOISE_TERMS = (
    "transit",
    "community center",
    "permit",
    "zoning",
    "school",
    "bike",
    "park",
    "trail",
    "boundary",
    "border",
    "housing element",
)
DERIVATIVE_TERMS = (
    "impacted",
    "impact",
    "clip",
    "buffer",
    "project",
    "study",
    "demo",
    "test",
    "sample",
    "draft",
    "temporary",
    "buyout",
    "fema",
    "flood",
    "park and ride",
    "covenant",
    "covenants",
    "apartments",
    "mobile homes",
)
STALE_TERMS = (
    "historical",
    "archive",
    "archived",
    "old",
    "legacy",
    "retired",
)
OFFICIAL_OWNER_TERMS = (
    "county",
    "assessor",
    "auditor",
    "gis",
    "planning",
    "open data",
    "opendata",
    "government",
    "gov",
    "state",
    "city",
)
OFFICIAL_DOMAIN_TERMS = (
    ".gov",
    ".us",
    "arcgis.com",
    "maps.arcgis.com",
    "opendata.arcgis.com",
)


def get_json(url: str, params: dict[str, Any] | None = None, timeout: int = 60) -> dict[str, Any]:
    full = url if params is None else url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(full, headers={"User-Agent": "county-parcel-toolkit/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def arcgis_search(county: str, state: str, limit: int = 12) -> list[dict[str, Any]]:
    queries = [
        f'"{county}" {state} parcel type:"Feature Service"',
        f'"{county}" {state} assessor type:"Feature Service"',
        f'"{county}" {state} property type:"Feature Service"',
        f'"{county}" {state} tax parcel type:"Feature Service"',
    ]
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    for query in queries:
        data = get_json(
            "https://www.arcgis.com/sharing/rest/search",
            {"f": "json", "q": query, "num": limit, "sortField": "numViews", "sortOrder": "desc"},
        )
        for item in data.get("results", []):
            item_id = item.get("id")
            if item_id and item_id not in seen:
                seen.add(item_id)
                items.append(item)
    items.sort(key=relevance_score, reverse=True)
    return items[:limit]


def relevance_score(item: dict[str, Any]) -> int:
    text = " ".join(
        str(item.get(key, "")) for key in ("title", "snippet", "description", "tags", "url")
    ).lower()
    score = 0
    for term in RELEVANT_TERMS:
        if term in text:
            score += 10
    for term in NOISE_TERMS:
        if term in text:
            score -= 15
    if "parcel" in str(item.get("title", "")).lower():
        score += 30
    if "assessor" in str(item.get("title", "")).lower():
        score += 20
    if "property" in str(item.get("title", "")).lower():
        score += 10
    return score


def layer_url(item: dict[str, Any]) -> str | None:
    url = item.get("url")
    if not url:
        return None
    if url.endswith("/0") or "/MapServer/" in url or "/FeatureServer/" in url and url.rsplit("/", 1)[-1].isdigit():
        return url
    if url.endswith("/FeatureServer") or url.endswith("/MapServer"):
        return url + "/0"
    return None


def count_layer(url: str) -> tuple[int | None, str | None]:
    try:
        data = get_json(url + "/query", {"f": "json", "where": "1=1", "returnCountOnly": "true"})
        if "error" in data:
            return None, json.dumps(data["error"])
        return data.get("count"), None
    except Exception as exc:  # noqa: BLE001 - report and continue
        return None, repr(exc)


def export_sample(url: str, output: Path, sample_size: int) -> tuple[int, list[str], bool | None, str | None]:
    try:
        data = get_json(
            url + "/query",
            {
                "f": "json",
                "where": "1=1",
                "outFields": "*",
                "returnGeometry": "false",
                "resultRecordCount": sample_size,
            },
        )
        if "error" in data:
            return 0, [], None, json.dumps(data["error"])
        features = data.get("features") or []
        rows = [feature.get("attributes", {}) for feature in features]
        headers: list[str] = []
        for row in rows:
            for key in row:
                if key not in headers:
                    headers.append(key)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return len(rows), headers, data.get("exceededTransferLimit"), None
    except Exception as exc:  # noqa: BLE001 - report and continue
        return 0, [], None, repr(exc)


def accepted_mapping(inferred: dict[str, list[dict[str, Any]]]) -> dict[str, list[str]]:
    canonical = ["parcel_id", "owner", "situs_address", "mailing_address", "land_use", "year_built", "assessed_value", "acreage"]
    output = {key: [] for key in canonical}
    for key, candidates in inferred.items():
        for candidate in candidates:
            if candidate.get("confidence") in {"high", "medium"}:
                field = candidate["field"]
                if field not in output[key]:
                    output[key].append(field)
            if len(output[key]) >= 2:
                break
    return output


def score_mapping(mapping: dict[str, list[str]]) -> dict[str, Any]:
    has = {key: bool(value) for key, value in mapping.items()}
    base = has["parcel_id"] and (has["situs_address"] or has["mailing_address"])
    ownership = has["owner"] and has["parcel_id"]
    useful_fields = sum(1 for value in has.values() if value)
    if ownership and useful_fields >= 5:
        status = "owner_ready_candidate"
    elif base and useful_fields >= 4:
        status = "base_or_value_candidate"
    elif has["parcel_id"]:
        status = "thin_parcel_candidate"
    else:
        status = "weak_candidate"
    return {"status": status, "has": has, "useful_field_count": useful_fields}


def authority_score(item: dict[str, Any], county: str, state: str, source_count: int | None, mapping_score: dict[str, Any]) -> dict[str, Any]:
    """Score whether a found layer is worth becoming a source-pack candidate.

    This is deliberately a lightweight gate, not a final truth engine. It keeps
    the pilot focused on building the method: choose likely official,
    countywide, parcel-relevant sources; flag the rest for enrichment/manual
    discovery instead of pretending the first query result is coverage.
    """
    title = str(item.get("title") or "")
    owner = str(item.get("owner") or "")
    url = str(item.get("url") or "")
    text = " ".join(
        str(item.get(key, "")) for key in ("title", "snippet", "description", "tags", "url", "owner")
    ).lower()
    title_l = title.lower()
    owner_l = owner.lower()
    url_l = url.lower()
    county_base = county.lower().replace(" county", "").replace(" parish", "").replace(" municipality", "")

    signals: list[str] = []
    penalties: list[str] = []
    score = 0

    if county.lower() in text or county_base in text:
        score += 25
        signals.append("county_name_match")
    if state.lower() in text or f" {state.lower()} " in f" {text} ":
        score += 5
        signals.append("state_match")
    if any(term in title_l for term in ("parcel", "tax parcel", "taxparcel", "cadastral", "cadastre")):
        score += 30
        signals.append("parcel_title")
    if any(term in title_l for term in ("assessor", "property", "real estate", "cama")):
        score += 15
        signals.append("assessor_property_title")
    if any(term in owner_l for term in OFFICIAL_OWNER_TERMS):
        score += 15
        signals.append("official_owner_like")
    if any(term in url_l for term in OFFICIAL_DOMAIN_TERMS):
        score += 8
        signals.append("official_or_common_gis_domain")

    for term in STALE_TERMS:
        if term in text:
            score -= 20
            penalties.append(f"stale:{term}")
    for term in DERIVATIVE_TERMS:
        if term in text:
            score -= 25
            penalties.append(f"derivative:{term}")
    for term in NOISE_TERMS:
        if term in text:
            score -= 15
            penalties.append(f"noise:{term}")

    if "statewide" in text or "state wide" in text:
        score -= 8
        penalties.append("statewide_aggregator")
    if source_count is not None:
        if source_count < 1_000:
            score -= 45
            penalties.append("implausibly_small_count")
        elif source_count >= 10_000:
            score += 15
            signals.append("countywide_plausible_count")
        elif source_count >= 3_000:
            score += 5
            signals.append("small_count_but_plausible")

    has = mapping_score.get("has", {})
    if has.get("parcel_id"):
        score += 20
        signals.append("parcel_id_mapped")
    if has.get("situs_address") or has.get("mailing_address"):
        score += 10
        signals.append("address_mapped")
    if has.get("owner"):
        score += 8
        signals.append("owner_mapped")
    if has.get("assessed_value") or has.get("land_use") or has.get("acreage"):
        score += 6
        signals.append("useful_property_fields")

    if "implausibly_small_count" in penalties:
        decision = "do_not_promote_without_manual_validation"
    elif score >= 70:
        decision = "promote_source_pack_candidate"
    elif score >= 40:
        decision = "review_candidate"
    else:
        decision = "do_not_promote_without_manual_validation"
    return {"score": score, "decision": decision, "signals": signals, "penalties": penalties}


def run_target(state: str, county: str, output_root: Path, sample_size: int, full: bool = False) -> dict[str, Any]:
    slug = f"{state.lower()}_{county.lower().replace(' ', '_').replace('.', '').replace('-', '_')}"
    target_dir = output_root / slug
    record: dict[str, Any] = {"state": state, "county": county, "slug": slug}
    items = arcgis_search(county, state)
    record["search_results"] = [
        {"title": item.get("title"), "owner": item.get("owner"), "type": item.get("type"), "url": item.get("url"), "id": item.get("id")}
        for item in items
    ]
    viable: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if relevance_score(item) <= 0:
            continue
        url = layer_url(item)
        if not url:
            continue
        count, count_error = count_layer(url)
        sample_path = target_dir / f"candidate_{index:02d}_sample.csv"
        rows, headers, exceeded, export_error = export_sample(url, sample_path, sample_size if not full else min(sample_size, 2000))
        candidate = {
            "title": item.get("title"),
            "owner": item.get("owner"),
            "item_id": item.get("id"),
            "url": url,
            "source_count": count,
            "count_error": count_error,
            "sample_rows": rows,
            "field_count": len(headers),
            "exceeded_transfer_limit": exceeded,
            "export_error": export_error,
            "sample_path": str(sample_path),
        }
        if rows and headers:
            profile = profile_csv(sample_path)
            inferred = infer_field_map(profile)
            mapping = accepted_mapping(inferred)
            mapping_score = score_mapping(mapping)
            candidate["mapping"] = mapping
            candidate["score"] = mapping_score
            candidate["authority"] = authority_score(item, county, state, count, mapping_score)
            viable.append(candidate)
        else:
            record.setdefault("rejected_candidates", []).append(candidate)
        time.sleep(0.25)

    if viable:
        decision_rank = {
            "promote_source_pack_candidate": 2,
            "review_candidate": 1,
            "do_not_promote_without_manual_validation": 0,
        }
        viable.sort(
            key=lambda c: (
                decision_rank.get(c.get("authority", {}).get("decision", ""), 0),
                c.get("authority", {}).get("score", -999),
                c.get("score", {}).get("useful_field_count", 0),
            ),
            reverse=True,
        )
        selected = viable[0]
        selected_sample_path = Path(selected["sample_path"])
        canonical_sample = target_dir / "sample.csv"
        canonical_sample.write_text(selected_sample_path.read_text(encoding="utf-8"), encoding="utf-8")
        norm_path = target_dir / "normalized_sample.csv"
        normalize_csv(canonical_sample, norm_path, selected["mapping"])
        selected["normalized_sample"] = str(norm_path)
        (target_dir / "auto_mapping.json").write_text(
            json.dumps({"field_map": selected["mapping"], "authority": selected["authority"]}, indent=2),
            encoding="utf-8",
        )
        record["selected"] = selected
        record["candidate_count"] = len(viable)
        record["review_candidates"] = viable[1:5]
    else:
        record["status"] = "no_queryable_arcgis_candidate_found"
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scratch/us_county_pilot", help="Output scratch directory")
    parser.add_argument("--sample-size", type=int, default=1000)
    parser.add_argument("--states", help="Comma-separated state abbreviations to test; default is all")
    parser.add_argument("--limit", type=int, help="Limit number of targets for smoke tests")
    parser.add_argument("--full", action="store_true", help="Reserved for future full exports; current pilot remains sample-bounded")
    args = parser.parse_args(argv)

    selected_states = {part.strip().upper() for part in args.states.split(",")} if args.states else None
    targets = [(state, county) for state, county in DEFAULT_TARGETS if selected_states is None or state in selected_states]
    if args.limit:
        targets = targets[: args.limit]

    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)
    results = []
    for state, county in targets:
        print(f"testing {county}, {state}...", file=sys.stderr)
        results.append(run_target(state, county, output_root, args.sample_size, args.full))
        (output_root / "run_report.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        time.sleep(0.5)

    report = output_root / "run_report.json"
    print(json.dumps({"targets": len(targets), "report": str(report)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
