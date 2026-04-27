"""Command line interface for county-parcel-toolkit."""

from __future__ import annotations

import argparse
import json

from .arcgis import ArcGISLayer
from .discovery import discover_arcgis_sources
from .joiner import EnrichmentJoin, join_enrichments
from .mapper import infer_field_map, join_profile, profile_csv
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

    discover = sub.add_parser("discover", help="Discover public parcel-data source candidates")
    discover_sub = discover.add_subparsers(dest="discover_command", required=True)
    discover_arcgis = discover_sub.add_parser("arcgis", help="Search ArcGIS Online for likely parcel sources")
    discover_arcgis.add_argument("query")
    discover_arcgis.add_argument("--limit", type=int, default=10)

    mapper = sub.add_parser("map", help="Profile CSVs and infer mapping candidates")
    mapper_sub = mapper.add_subparsers(dest="map_command", required=True)

    profile = mapper_sub.add_parser("profile", help="Profile headers, nulls, distinct counts, and samples")
    profile.add_argument("input")

    infer = mapper_sub.add_parser("infer", help="Infer canonical field mapping candidates from a CSV")
    infer.add_argument("input")

    join = mapper_sub.add_parser("join", help="Measure join overlap and duplicate-key risk between two CSVs")
    join.add_argument("left")
    join.add_argument("right")
    join.add_argument("--left-key", required=True)
    join.add_argument("--right-key", required=True)

    merge = mapper_sub.add_parser("merge", help="Left-join enrichment tables to a base parcel table")
    merge.add_argument("base", help="Base parcel/address table")
    merge.add_argument("output", help="Output clean wide CSV")
    merge.add_argument("--base-key", required=True)
    merge.add_argument(
        "--join",
        action="append",
        default=[],
        metavar="NAME=PATH:KEY[:FIELD,FIELD]",
        help="Enrichment table join spec. Repeat for multiple tables.",
    )

    return parser


def _parse_join_spec(spec: str) -> EnrichmentJoin:
    """Parse NAME=PATH:KEY[:FIELD,FIELD] CLI join specs."""
    if "=" not in spec:
        raise SystemExit(f"Invalid --join spec {spec!r}; expected NAME=PATH:KEY[:FIELD,FIELD]")
    name, rest = spec.split("=", 1)
    parts = rest.rsplit(":", 2)
    if len(parts) < 2:
        raise SystemExit(f"Invalid --join spec {spec!r}; expected NAME=PATH:KEY[:FIELD,FIELD]")
    path, key = parts[0], parts[1]
    fields: tuple[str, ...] = ()
    if len(parts) == 3 and parts[2]:
        fields = tuple(field.strip() for field in parts[2].split(",") if field.strip())
    return EnrichmentJoin(name=name, path=path, key=key, fields=fields)


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

    if args.command == "discover":
        if args.discover_command == "arcgis":
            results = discover_arcgis_sources(args.query, limit=args.limit)
            print(json.dumps([result.to_dict() for result in results], indent=2, sort_keys=True))
            return 0

    if args.command == "map":
        if args.map_command == "profile":
            print(json.dumps(profile_csv(args.input), indent=2, sort_keys=True))
            return 0
        if args.map_command == "infer":
            print(json.dumps(infer_field_map(profile_csv(args.input)), indent=2, sort_keys=True))
            return 0
        if args.map_command == "join":
            print(json.dumps(join_profile(args.left, args.right, args.left_key, args.right_key), indent=2, sort_keys=True))
            return 0
        if args.map_command == "merge":
            enrichments = [_parse_join_spec(spec) for spec in args.join]
            print(json.dumps(join_enrichments(args.base, args.output, args.base_key, enrichments), indent=2, sort_keys=True))
            return 0

    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
