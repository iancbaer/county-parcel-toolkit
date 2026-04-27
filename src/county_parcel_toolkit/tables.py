"""Small table readers for county data files.

County portals publish CSV, pipe-delimited text, TSV, and sometimes XLSX.
This module keeps ingestion dependency-light so source packs can be tested in
plain Python.
"""

from __future__ import annotations

import csv
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Iterator


def _column_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref)
    if not match:
        return 0
    index = 0
    for char in match.group(1):
        index = index * 26 + ord(char) - 64
    return index - 1


def _xlsx_shared_strings(package: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in package.namelist():
        return []
    namespace = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ET.fromstring(package.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall("a:si", namespace):
        values.append("".join(text.text or "" for text in item.findall(".//a:t", namespace)))
    return values


def iter_xlsx_records(path: str | Path, sheet_index: int = 1) -> Iterator[dict[str, str]]:
    """Yield dictionaries from a simple XLSX worksheet using only stdlib.

    This supports the flat spreadsheets commonly published by county portals.
    It intentionally does not evaluate formulas or styles.
    """
    source = Path(path)
    namespace = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(source) as package:
        shared_strings = _xlsx_shared_strings(package)
        sheet_name = f"xl/worksheets/sheet{sheet_index}.xml"
        root = ET.fromstring(package.read(sheet_name))

        headers: list[str] | None = None
        for row in root.findall(".//a:row", namespace):
            values_by_col: dict[int, str] = {}
            for cell in row.findall("a:c", namespace):
                value_node = cell.find("a:v", namespace)
                if value_node is None:
                    value = ""
                else:
                    value = value_node.text or ""
                    if cell.attrib.get("t") == "s":
                        value = shared_strings[int(value)]
                values_by_col[_column_index(cell.attrib.get("r", "A"))] = value

            width = max(values_by_col.keys(), default=-1) + 1
            values = [values_by_col.get(index, "") for index in range(width)]
            if headers is None:
                headers = [value.strip() for value in values]
                continue
            if not any(values):
                continue
            yield {headers[index]: values[index] if index < len(values) else "" for index in range(len(headers))}


def _sniff_delimiter(sample: str) -> str:
    candidates = [",", "|", "\t", ";"]
    counts = {delimiter: sample.count(delimiter) for delimiter in candidates}
    return max(counts, key=counts.get) if any(counts.values()) else ","


def iter_delimited_records(path: str | Path, delimiter: str | None = None) -> Iterator[dict[str, str]]:
    source = Path(path)
    with source.open(newline="", encoding="utf-8-sig") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        reader = csv.DictReader(handle, delimiter=delimiter or _sniff_delimiter(sample))
        for row in reader:
            yield {key: value for key, value in row.items() if key is not None}


def iter_records(path: str | Path) -> Iterator[dict[str, str]]:
    source = Path(path)
    if source.suffix.lower() == ".xlsx":
        yield from iter_xlsx_records(source)
    else:
        yield from iter_delimited_records(source)
