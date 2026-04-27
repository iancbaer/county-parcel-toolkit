#!/usr/bin/env python3
"""Resumable-ish ArcGIS FeatureServer full attribute export with progress.

Writes no geometry by default. Designed for large public parcel layers where the
normal CLI is too quiet for long runs.
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


def get_json(url: str, params: dict[str, Any] | None = None, timeout: int = 120, attempts: int = 4) -> dict[str, Any]:
    full = url if params is None else url + "?" + urllib.parse.urlencode(params)
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(full, headers={"User-Agent": "county-parcel-toolkit/0.1 full-export"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt == attempts:
                break
            time.sleep(min(30, 2**attempt))
    raise RuntimeError(f"failed after {attempts} attempts: {last}")


def query_url(layer_url: str, offset: int, chunk_size: int, order_field: str, out_fields: str) -> tuple[str, dict[str, Any]]:
    return layer_url.rstrip("/") + "/query", {
        "f": "json",
        "where": "1=1",
        "returnGeometry": "false",
        "outFields": out_fields,
        "orderByFields": order_field,
        "resultOffset": offset,
        "resultRecordCount": chunk_size,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("output")
    parser.add_argument("--chunk-size", type=int, default=2000)
    parser.add_argument("--out-fields", default="*")
    parser.add_argument("--order-field")
    parser.add_argument("--progress-every", type=int, default=50_000)
    args = parser.parse_args(argv)

    layer_url = args.url.rstrip("/")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".part")
    manifest = output.with_suffix(output.suffix + ".manifest.json")

    metadata = get_json(layer_url, {"f": "json"})
    order_field = args.order_field or metadata.get("objectIdField") or "OBJECTID"
    count_payload = get_json(layer_url + "/query", {"f": "json", "where": "1=1", "returnCountOnly": "true"})
    if "error" in count_payload:
        raise RuntimeError(json.dumps(count_payload["error"]))
    total = int(count_payload["count"])
    fields = [field.get("name") for field in metadata.get("fields", []) if field.get("name")]

    started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    rows_written = 0
    fieldnames: list[str] | None = None
    next_progress = args.progress_every
    t0 = time.time()

    print(json.dumps({
        "event": "start",
        "url": layer_url,
        "output": str(output),
        "tmp": str(tmp),
        "total": total,
        "chunk_size": args.chunk_size,
        "order_field": order_field,
        "field_count": len(fields),
        "fields": fields,
    }), flush=True)

    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = None
        offset = 0
        while offset < total:
            endpoint, params = query_url(layer_url, offset, args.chunk_size, order_field, args.out_fields)
            payload = get_json(endpoint, params)
            if "error" in payload:
                raise RuntimeError(json.dumps(payload["error"]))
            features = payload.get("features") or []
            if not features:
                break
            for feature in features:
                row = feature.get("attributes", {})
                if fieldnames is None:
                    fieldnames = list(row.keys())
                    writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
                    writer.writeheader()
                assert writer is not None
                writer.writerow(row)
                rows_written += 1
            offset += len(features)
            if rows_written >= next_progress or rows_written >= total:
                elapsed = max(time.time() - t0, 0.001)
                rate = rows_written / elapsed
                print(json.dumps({
                    "event": "progress",
                    "rows": rows_written,
                    "total": total,
                    "pct": round(rows_written / total * 100, 2) if total else None,
                    "rate_rows_per_sec": round(rate, 1),
                    "mb_written": round(tmp.stat().st_size / 1_000_000, 1),
                }), flush=True)
                next_progress += args.progress_every
            if len(features) < args.chunk_size:
                break

    output.unlink(missing_ok=True)
    tmp.rename(output)
    finished_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    manifest_data = {
        "url": layer_url,
        "output": str(output),
        "rows_expected": total,
        "rows_written": rows_written,
        "bytes": output.stat().st_size,
        "fields": fieldnames or [],
        "source_fields": fields,
        "chunk_size": args.chunk_size,
        "order_field": order_field,
        "return_geometry": False,
        "started_at": started_at,
        "finished_at": finished_at,
    }
    manifest.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    print(json.dumps({"event": "done", **manifest_data}), flush=True)
    return 0 if rows_written == total else 2


if __name__ == "__main__":
    raise SystemExit(main())
