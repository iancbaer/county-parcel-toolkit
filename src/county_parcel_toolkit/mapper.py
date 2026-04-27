"""Deterministic helpers for profiling county parcel tables and mapping fields.

The agent skill describes the judgment layer. This module makes the repeatable
parts executable: profile columns, score likely canonical fields, and measure
join quality.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path
from typing import Any

CANONICAL_ALIASES: dict[str, tuple[str, ...]] = {
    "parcel_id": (
        "parcel",
        "parcel_id",
        "parcelid",
        "parcelno",
        "parcel_no",
        "pin",
        "pin10",
        "pin14",
        "key_pin",
        "taxparcelnumber",
        "tax_parcel_number",
        "orig_parcel_id",
        "parcel_id_nr",
        "apn",
        "tax_parcel",
        "property_id",
    ),
    "owner": ("owner", "owner_name", "ownername", "taxpayer", "taxpayer_name", "taxpayername", "name1", "business_name", "fullname", "full_name"),
    "situs_address": (
        "situs",
        "situs_addr",
        "situs_address",
        "site_addr",
        "site_address",
        "siteaddress",
        "property_address",
        "location_address",
        "addr_full",
        "address",
    ),
    "mailing_address": (
        "mailing",
        "mail_addr",
        "mailing_address",
        "address_1",
        "owner_address",
        "delivery_address",
        "kctp_addr",
        "kctp_ctyst",
        "kctp_zip",
    ),
    "land_use": ("land_use", "landuse_cd", "landuse_description", "use_code", "use_desc", "prop_use", "prop_use_desc", "property_class", "preuse_code", "preuse_desc"),
    "year_built": ("year_built", "yr_built", "built", "effective_year"),
    "assessed_value": (
        "assessed",
        "assessed_total",
        "taxable",
        "taxable_value",
        "taxable_reg",
        "market",
        "mkt_total",
        "total_value",
        "totalvalue",
        "landvalue",
        "bldgvalue",
        "value_land",
        "value_bldg",
        "apprlndval",
        "appr_impr",
        "tax_lndval",
        "tax_impr",
    ),
    "acreage": ("acres", "acreage", "land_acres", "kca_acres"),
}


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _non_empty(value: Any) -> bool:
    return value not in (None, "")


def _looks_like_year(values: list[str]) -> bool:
    years = [v for v in values if re.fullmatch(r"(18|19|20)\d{2}", v.strip())]
    return bool(values) and len(years) / len(values) >= 0.8


def _looks_numeric(values: list[str]) -> bool:
    numeric = [v for v in values if re.fullmatch(r"[$,\d.\s]+", v.strip())]
    return bool(values) and len(numeric) / len(values) >= 0.8


def _looks_name_like(values: list[str]) -> bool:
    alpha = [v for v in values if re.search(r"[A-Za-z]", v) and not re.fullmatch(r"[$,\d.\s]+", v.strip())]
    return bool(values) and len(alpha) / len(values) >= 0.8


def profile_csv(path: str | Path, sample_size: int = 1000) -> dict[str, Any]:
    """Return basic deterministic profile data for a CSV file."""
    source = Path(path)
    samples: dict[str, list[str]] = {}
    null_counts: Counter[str] = Counter()
    distinct_values: dict[str, set[str]] = {}
    row_count = 0

    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        samples = {header: [] for header in headers}
        distinct_values = {header: set() for header in headers}

        for row in reader:
            row_count += 1
            for header in headers:
                value = row.get(header, "")
                if not _non_empty(value):
                    null_counts[header] += 1
                    continue
                text = str(value)
                distinct_values[header].add(text)
                if len(samples[header]) < sample_size:
                    samples[header].append(text)

    fields = {
        header: {
            "normalized_name": _norm(header),
            "null_count": null_counts[header],
            "distinct_count": len(distinct_values[header]),
            "sample_values": samples[header][:10],
        }
        for header in headers
    }
    return {"path": str(source), "row_count": row_count, "headers": headers, "fields": fields}


def infer_field_map(profile: dict[str, Any], max_candidates: int = 3) -> dict[str, list[dict[str, Any]]]:
    """Infer likely canonical field mappings from a profile.

    This deliberately returns candidates with scores/confidence instead of a
    single hidden answer. Agents/users can inspect and code can validate.
    """
    inferred: dict[str, list[dict[str, Any]]] = {}
    fields = profile.get("fields", {})

    for target, aliases in CANONICAL_ALIASES.items():
        candidates: list[dict[str, Any]] = []
        for field, stats in fields.items():
            normalized = stats["normalized_name"]
            samples = stats.get("sample_values", [])
            score = 0
            reasons: list[str] = []

            if normalized in aliases:
                score += 90
                reasons.append("exact_alias")
            elif any(alias in normalized or normalized in alias for alias in aliases):
                score += 55
                reasons.append("name_similarity")

            if target == "year_built" and _looks_like_year(samples):
                score += 25
                reasons.append("year_like_values")
            elif target in {"assessed_value", "acreage"} and _looks_numeric(samples):
                score += 15
                reasons.append("numeric_values")
            elif target == "owner" and _looks_name_like(samples):
                score += 10
                reasons.append("name_like_values")
            elif target in {"situs_address", "mailing_address"} and any(re.search(r"\d+\s+\w+", value) for value in samples):
                score += 10
                reasons.append("address_like_values")

            if score:
                confidence = "high" if score >= 80 else "medium" if score >= 50 else "low"
                candidates.append({"field": field, "score": score, "confidence": confidence, "reasons": reasons})

        candidates.sort(key=lambda item: (-item["score"], item["field"]))
        inferred[target] = candidates[:max_candidates]

    return inferred


def _key_counts(path: str | Path, key_field: str) -> tuple[int, Counter[str]]:
    rows = 0
    counts: Counter[str] = Counter()
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows += 1
            value = row.get(key_field, "")
            if _non_empty(value):
                counts[str(value)] += 1
    return rows, counts


def join_profile(left_path: str | Path, right_path: str | Path, left_key: str, right_key: str) -> dict[str, Any]:
    """Measure join overlap and duplicate-key risk for two CSV files."""
    left_rows, left_counts = _key_counts(left_path, left_key)
    right_rows, right_counts = _key_counts(right_path, right_key)
    left_keys = set(left_counts)
    right_keys = set(right_counts)
    overlap = left_keys & right_keys
    left_overlap_rate = round(len(overlap) / len(left_keys), 3) if left_keys else 0.0
    right_overlap_rate = round(len(overlap) / len(right_keys), 3) if right_keys else 0.0
    left_duplicate_keys = sum(1 for count in left_counts.values() if count > 1)
    right_duplicate_keys = sum(1 for count in right_counts.values() if count > 1)

    if left_overlap_rate >= 0.95 and right_duplicate_keys == 0:
        confidence = "high"
    elif left_overlap_rate >= 0.5:
        confidence = "medium"
    elif left_overlap_rate > 0:
        confidence = "low"
    else:
        confidence = "none"

    return {
        "left_rows": left_rows,
        "right_rows": right_rows,
        "left_key_count": len(left_keys),
        "right_key_count": len(right_keys),
        "overlap_count": len(overlap),
        "left_overlap_rate": left_overlap_rate,
        "right_overlap_rate": right_overlap_rate,
        "left_duplicate_keys": left_duplicate_keys,
        "right_duplicate_keys": right_duplicate_keys,
        "confidence": confidence,
    }
