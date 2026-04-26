"""Normalize parcel records to a small common schema."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

DEFAULT_FIELDS = [
    "parcel_id",
    "owner",
    "situs_address",
    "mailing_address",
    "land_use",
    "year_built",
    "assessed_value",
    "acreage",
]


def normalize_record(record: dict[str, object], field_map: dict[str, list[str]]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for target, candidates in field_map.items():
        value = ""
        for source in candidates:
            raw = record.get(source)
            if raw not in (None, ""):
                value = str(raw)
                break
        normalized[target] = value
    return normalized


def load_mapping(path: str | Path) -> dict[str, list[str]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload.get("field_map", payload)


def normalize_csv(input_path: str | Path, output_path: str | Path, field_map: dict[str, list[str]]) -> int:
    source = Path(input_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = 0
    with source.open(newline="", encoding="utf-8") as in_handle, output.open("w", newline="", encoding="utf-8") as out_handle:
        reader = csv.DictReader(in_handle)
        fieldnames = list(field_map.keys())
        writer = csv.DictWriter(out_handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in reader:
            writer.writerow(normalize_record(record, field_map))
            rows += 1
    return rows
