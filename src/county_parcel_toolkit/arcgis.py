"""ArcGIS FeatureServer helpers."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


@dataclass(frozen=True)
class ArcGISLayer:
    """A single ArcGIS FeatureServer layer endpoint."""

    url: str

    def _query_url(self, params: dict[str, Any]) -> str:
        return f"{self.url.rstrip('/')}/query?{urlencode(params)}"

    def count_url(self) -> str:
        return self._query_url({"f": "json", "where": "1=1", "returnCountOnly": "true"})

    def query_url(self, offset: int = 0, limit: int = 2000) -> str:
        return self._query_url(
            {
                "f": "json",
                "where": "1=1",
                "returnGeometry": "false",
                "outFields": "*",
                "orderByFields": "OBJECTID",
                "resultOffset": offset,
                "resultRecordCount": limit,
            }
        )

    def metadata_url(self) -> str:
        return f"{self.url.rstrip('/')}?{urlencode({'f': 'json'})}"

    def fetch_json(self, url: str) -> dict[str, Any]:
        with urlopen(url, timeout=60) as response:  # nosec B310 - user-supplied public data URLs are this tool's purpose
            return json.loads(response.read().decode("utf-8"))

    def count(self) -> int:
        payload = self.fetch_json(self.count_url())
        return int(payload["count"])

    def fields(self) -> list[str]:
        payload = self.fetch_json(self.metadata_url())
        return [field["name"] for field in payload.get("fields", []) if "name" in field]

    def iter_features(self, chunk_size: int = 2000):
        offset = 0
        while True:
            payload = self.fetch_json(self.query_url(offset=offset, limit=chunk_size))
            features = payload.get("features", [])
            if not features:
                break
            for feature in features:
                yield feature.get("attributes", {})
            if len(features) < chunk_size:
                break
            offset += chunk_size

    def export_csv(self, output_path: str | Path, chunk_size: int = 2000) -> int:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        rows_written = 0
        fieldnames: list[str] | None = None
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = None
            for row in self.iter_features(chunk_size=chunk_size):
                if fieldnames is None:
                    fieldnames = list(row.keys())
                    writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
                    writer.writeheader()
                assert writer is not None
                writer.writerow(row)
                rows_written += 1
        return rows_written
