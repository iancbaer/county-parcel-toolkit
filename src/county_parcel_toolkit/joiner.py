"""Join county parcel tables into a wide, clean dataset."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .tables import iter_records


@dataclass(frozen=True)
class EnrichmentJoin:
    """A table to left-join onto a base parcel/address table."""

    name: str
    path: str | Path
    key: str
    fields: tuple[str, ...] = ()


def _clean_key(value: object) -> str:
    return str(value or "").strip()


def _right_output_name(source_name: str, field: str, existing_fields: set[str]) -> str:
    if field not in existing_fields:
        return field
    return f"{source_name}_{field}"


def _load_unique_index(join: EnrichmentJoin) -> tuple[dict[str, dict[str, str]], dict[str, Any]]:
    index: dict[str, dict[str, str]] = {}
    duplicate_keys: set[str] = set()
    rows = 0
    for row in iter_records(join.path):
        rows += 1
        key = _clean_key(row.get(join.key))
        if not key:
            continue
        if key in index:
            duplicate_keys.add(key)
            # Keep the first row; duplicate handling belongs in a county-specific
            # pre-aggregation step so the clean join remains deterministic.
            continue
        index[key] = row
    return index, {"rows": rows, "distinct_keys": len(index), "duplicate_keys": len(duplicate_keys)}


def join_enrichments(
    base_path: str | Path,
    output_path: str | Path,
    base_key: str,
    enrichments: list[EnrichmentJoin],
) -> dict[str, Any]:
    """Left-join enrichment tables to a base table and write a clean CSV.

    The output contains data fields only. Source notes/disclaimers from source
    packs are metadata and are deliberately not written into each cleaned row.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    indexes: dict[str, dict[str, dict[str, str]]] = {}
    join_stats: dict[str, Any] = {}
    enrichment_output_fields: dict[str, list[tuple[str, str]]] = {}

    for join in enrichments:
        index, stats = _load_unique_index(join)
        indexes[join.name] = index
        join_stats[join.name] = stats

    base_rows = list(iter_records(base_path))
    base_fields = list(base_rows[0].keys()) if base_rows else []
    output_fields = list(base_fields)
    existing = set(output_fields)

    for join in enrichments:
        sample_row = next(iter(indexes[join.name].values()), {})
        source_fields = list(join.fields) if join.fields else [field for field in sample_row if field != join.key]
        mapped_fields: list[tuple[str, str]] = []
        for source_field in source_fields:
            out_field = _right_output_name(join.name, source_field, existing)
            existing.add(out_field)
            output_fields.append(out_field)
            mapped_fields.append((source_field, out_field))
        enrichment_output_fields[join.name] = mapped_fields
        join_stats[join.name]["output_fields"] = [out for _, out in mapped_fields]
        join_stats[join.name]["matched_rows"] = 0

    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields)
        writer.writeheader()
        for base_row in base_rows:
            merged = dict(base_row)
            key = _clean_key(base_row.get(base_key))
            for join in enrichments:
                right_row = indexes[join.name].get(key)
                if right_row is not None:
                    join_stats[join.name]["matched_rows"] += 1
                for source_field, out_field in enrichment_output_fields[join.name]:
                    merged[out_field] = right_row.get(source_field, "") if right_row else ""
            writer.writerow(merged)

    for stats in join_stats.values():
        stats["base_rows"] = len(base_rows)
        stats["match_rate"] = round(stats["matched_rows"] / len(base_rows), 4) if base_rows else 0.0

    return {"base_rows": len(base_rows), "output": str(output), "joins": join_stats}
