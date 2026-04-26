# County Parcel Data Toolkit

Developer-first tools for discovering, downloading, and normalizing public county parcel and assessor data.

It normalizes parcel data. If someone's smart, they'll figure out why it's useful.

## Project definition

See `docs/PROJECT_DEFINITION.md` for the full product definition, MVP scope, and roadmap.

## Why

County parcel data is public, useful, and annoyingly inconsistent. One county exposes an ArcGIS FeatureServer, another publishes a zipped shapefile, another uses Socrata, and every table names the same concepts differently.

This toolkit aims to make the boring path repeatable:

1. define a public source
2. download records safely in chunks
3. normalize common parcel fields
4. export developer-friendly files

## Current status

Pre-alpha scaffold. The first supported source type is ArcGIS FeatureServer layers.

## Install for local development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```

## CLI examples

Count records in an ArcGIS layer:

```bash
parceltool arcgis count "https://example.gov/arcgis/rest/services/Parcels/FeatureServer/0"
```

Inspect fields:

```bash
parceltool arcgis fields "https://example.gov/arcgis/rest/services/Parcels/FeatureServer/0"
```

Export attributes to CSV without geometry:

```bash
parceltool arcgis export "https://example.gov/arcgis/rest/services/Parcels/FeatureServer/0" exports/parcels.csv --chunk-size 2000
```

Normalize a CSV using a source mapping:

```bash
parceltool normalize input.csv output.csv --mapping examples/sources/spokane_county_wa.json
```

## Normalized fields

The initial common schema is deliberately small:

- parcel_id
- owner
- situs_address
- mailing_address
- land_use
- year_built
- assessed_value
- acreage

## Public-data stance

- Do not commit downloaded records.
- Keep source definitions, schemas, and code public.
- Respect source terms, rate limits, robots policies, and local law.

## Roadmap

- ArcGIS FeatureServer chunked CSV export
- Source definition files
- Field normalization helpers
- Socrata support
- CKAN support
- Static CSV/zipped shapefile support
- Geometry export: GeoJSON and Parquet
- Source discovery helpers
