"""Command line interface for county-parcel-toolkit."""

from __future__ import annotations

import argparse

from .arcgis import ArcGISLayer
from .normalize import load_mapping, normalize_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="parceltool")
    sub = parser.add_subparsers(dest="command", required=True)

    arcgis = sub.add_parser("arcgis", help="ArcGIS FeatureServer commands")
    arcgis_sub = arcgis.add_subparsers(dest="arcgis_command", required=True)

    count = arcgis_sub.add_parser("count", help="Count records in a FeatureServer layer")
    count.add_argument("url")

    fields = arcgis_sub.add_parser("fields", help="List fields in a FeatureServer layer")
    fields.add_argument("url")

    export = arcgis_sub.add_parser("export", help="Export FeatureServer attributes to CSV")
    export.add_argument("url")
    export.add_argument("output")
    export.add_argument("--chunk-size", type=int, default=2000)

    normalize = sub.add_parser("normalize", help="Normalize a CSV with a source mapping")
    normalize.add_argument("input")
    normalize.add_argument("output")
    normalize.add_argument("--mapping", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "arcgis":
        layer = ArcGISLayer(args.url)
        if args.arcgis_command == "count":
            print(layer.count())
            return 0
        if args.arcgis_command == "fields":
            for field in layer.fields():
                print(field)
            return 0
        if args.arcgis_command == "export":
            rows = layer.export_csv(args.output, chunk_size=args.chunk_size)
            print(f"wrote {rows} rows to {args.output}")
            return 0

    if args.command == "normalize":
        field_map = load_mapping(args.mapping)
        rows = normalize_csv(args.input, args.output, field_map)
        print(f"wrote {rows} rows to {args.output}")
        return 0

    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
