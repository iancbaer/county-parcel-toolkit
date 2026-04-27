# County Parcel Data Toolkit

Developer-first tools for discovering, downloading, and normalizing public county parcel and assessor data.

It turns inconsistent public parcel data into normalized, developer-friendly files.

## Project definition

See `docs/PROJECT_DEFINITION.md` for the full product definition, MVP scope, and roadmap. See `docs/COUNTY_ONBOARDING_METHOD.md` for the repeatable method for adding a new county and proving clean joins across parcel/address, owner/taxpayer, valuation, building, and sales tables.

## Agent skill

This repo includes `agent-skill/SKILL.md`: a general agent playbook for hybrid AI + deterministic county-data mapping. The intended pattern is:

- code handles repeatable discovery, downloads, schema checks, joins, stats, and exports
- AI handles sparse judgment: source classification, field/role inference, ambiguous joins, documentation, and conversational use
- every AI guess is written as a confidence-scored mapping that regular code can validate and reuse

That makes the mapping layer the durable asset, not any one county export.

## Why

County parcel data is public, useful, and annoyingly inconsistent. One county exposes an ArcGIS FeatureServer, another publishes a zipped shapefile, another uses Socrata, and every table names the same concepts differently.

This toolkit aims to make the boring path repeatable:

1. define a public source
2. download records safely in chunks
3. normalize common parcel fields
4. export developer-friendly files

## Current status

Pre-alpha toolkit with an updateable local application shell. The first supported source type is ArcGIS FeatureServer layers.

## Install for local development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```

## CLI examples

Run the local application shell:

```bash
parceltool app serve --host 127.0.0.1 --port 8765
```

Check the app capability API without starting the server:

```bash
parceltool app status
```

Render the current HTML shell for inspection or static hosting experiments:

```bash
parceltool app render > app.html
```

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

Search ArcGIS Online for likely public parcel source candidates:

```bash
parceltool discover arcgis "Spokane County WA parcel" --limit 10
```

Normalize a CSV using a source mapping:

```bash
parceltool normalize input.csv output.csv --mapping examples/sources/spokane_county_wa.json
```

Profile and infer mapping candidates from a raw county CSV:

```bash
parceltool map profile scratch/wa_test/spokane/raw.csv
parceltool map infer scratch/wa_test/spokane/raw.csv
```

Measure whether two county tables really join on a proposed key:

```bash
parceltool map join parcels.csv value_info.csv --left-key parcel --right-key parcel
```

Create a clean wide joined file from a base parcel/address table plus enrichment tables:

```bash
parceltool map merge parcels.csv joined.csv \
  --base-key parcel \
  --join taxpayer=taxpayer_info.xlsx:parcel:taxpayer,address_1,address_2,city,state,zip \
  --join value=value_info.txt:parcel:tax_year,prop_use_desc,mkt_total,taxable_reg
```

The merge output contains data fields only. Source notices and county metadata stay in source packs/docs, not repeated inside every cleaned row.

These `map` commands are the executable test that the agent skill is more than prose: AI can suggest a mapping, but code must profile fields, score candidates, report join confidence, and produce clean joins in machine-readable form.

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

## County-specific source notes

- `docs/SPOKANE_COUNTY_WA.md` documents Spokane's thin parcel FeatureServer plus richer ArcGIS Hub downloads for value, property-use, taxpayer, and residential floor data.

## Public-data stance

- Do not commit downloaded records.
- Keep source definitions, schemas, and code public.
- Respect source terms, rate limits, robots policies, and local law.
- This toolkit downloads and normalizes public parcel records; it does not impose extra use restrictions beyond the source terms and applicable law.

## Roadmap

- ArcGIS FeatureServer chunked CSV export
- Source definition files
- Field normalization helpers
- Socrata support
- CKAN support
- Static CSV/zipped shapefile support
- Geometry export: GeoJSON and Parquet
- Source discovery helpers
- Updateable local app shell
- App workflows for source discovery, export, mapping review, and normalization
