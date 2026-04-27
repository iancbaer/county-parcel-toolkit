# County Parcel Data Toolkit — Project Definition

## One-line definition

County Parcel Data Toolkit is an open-source Python CLI/library for finding, downloading, validating, and normalizing public county parcel and assessor data into developer-friendly files.

## What problem it solves

County property data is public, but every county publishes it differently:

- ArcGIS FeatureServer layers with awkward paging rules
- Socrata or CKAN open-data portals
- static CSV downloads
- zipped shapefiles or GeoPackages
- inconsistent field names for the same concepts

The toolkit turns that mess into a repeatable pipeline:

1. define a public data source
2. inspect its fields and record count
3. download records safely in chunks
4. infer how raw tables and fields map to a canonical parcel schema
5. validate joins, null rates, duplicates, and field confidence with regular code
6. normalize common parcel/assessor fields
7. export clean CSV/GeoJSON/Parquet-style files for downstream use

The important product is the mapping layer: reusable knowledge about how a county's messy public tables connect and what each raw field means.

## Who it is for

Primary users:

- developers building civic data, GIS, housing, tax, land-use, or real-estate workflows
- data analysts who need repeatable county parcel exports
- small teams who need a boring, inspectable public-data ingestion tool

Secondary users:

- open-data researchers
- local government transparency projects
- teams that need a clean public-data ingestion foundation

## Product shape

The toolkit should be usable in three ways.

### CLI

For quick terminal workflows:

```bash
parceltool arcgis count <layer-url>
parceltool arcgis fields <layer-url>
parceltool arcgis export <layer-url> exports/raw.csv --chunk-size 2000
parceltool normalize exports/raw.csv exports/normalized.csv --mapping examples/sources/spokane_county_wa.json
```

### Python library

For scripts and larger systems:

```python
from county_parcel_toolkit.arcgis import ArcGISLayer
from county_parcel_toolkit.normalize import normalize_csv, load_mapping

layer = ArcGISLayer("https://example.gov/arcgis/rest/services/Parcels/FeatureServer/0")
layer.export_csv("exports/raw.csv")

field_map = load_mapping("examples/sources/example_county.json")
normalize_csv("exports/raw.csv", "exports/normalized.csv", field_map)
```

### Agent skill

For conversational, semi-autonomous mapping work:

```text
Load agent-skill/SKILL.md, discover public county parcel/assessor sources, classify tables, infer join keys, map fields to the canonical schema, validate those guesses with code, and write a reusable source pack plus confidence report.
```

This is intentionally hybrid. Regular code should do bulk work: downloads, profiling, null/duplicate rates, join validation, deterministic normalization, and regression tests. AI should be used sparingly for the parts that benefit from judgment: interpreting county metadata, classifying weird tables, suggesting likely field meanings, explaining caveats, and making the tool conversational for a non-specialist user.

Every AI-produced mapping should become structured data that code can inspect, validate, diff, and reuse.

## Core principles

1. Public-data plumbing
   - Code, source definitions, mappings, schemas, and docs can be public.
   - Downloaded records stay out of git.

2. Boring beats clever
   - Prefer clear CSV/JSON/stdlib-first flows before heavy frameworks.
   - Fail loudly with useful messages.

3. Source definitions are assets
   - A county source file should explain what endpoint is used, what fields map to normalized schema, and any known quirks.

4. Respect source limits
   - Chunk requests.
   - Do not hammer endpoints.
   - Document rate-limit behavior and source terms when known.

5. Normalize lightly
   - Preserve raw exports when possible.
   - Produce a small common schema without pretending all counties are identical.

## Initial common schema

The first normalized schema should stay deliberately small:

- parcel_id
- owner
- situs_address
- mailing_address
- land_use
- year_built
- assessed_value
- acreage

Likely later additions:

- county
- state
- source_url
- geometry_centroid_lat
- geometry_centroid_lon
- property_class
- tax_year
- sale_date
- sale_price

## MVP scope

Version 0.1 should prove this loop end-to-end for ArcGIS FeatureServer sources:

1. inspect a layer
   - count records
   - list fields
   - show basic metadata

2. export attributes
   - chunked pagination
   - CSV output
   - no geometry by default
   - safe output directory creation

3. normalize fields
   - JSON source mapping
   - CSV in, normalized CSV out
   - predictable missing-field behavior

4. package quality
   - tests for URL construction, pagination, normalization, CLI parsing
   - README examples
   - at least one real source definition with no bundled records

## Near-term roadmap

### Phase 1 — ArcGIS MVP

- Harden ArcGIS pagination and error handling
- Add `parceltool arcgis metadata`
- Add source JSON validation
- Add Spokane County example source definition
- Add dry-run/preview command for normalization

### Phase 2 — Source registry

- Define `examples/sources/*.json` structure
- Add validation command: `parceltool source validate <file>`
- Add source docs with known quirks and terms
- Add 2–3 public example counties across different states

### Phase 3 — Additional source adapters

- Socrata datasets
- CKAN packages
- static CSV URLs
- zipped shapefile or GeoPackage downloads

### Phase 4 — Output formats

- GeoJSON for geometry-enabled exports
- Parquet if/when dependency tradeoff is worth it
- optional geometry centroid extraction

### Phase 5 — Developer polish

- CI
- release workflow
- richer examples
- contribution guide
- issue templates

## Success criteria

The project is working when a developer can:

1. find a public county parcel layer
2. run one command to inspect it
3. run one command to export raw parcel attributes
4. run one command to normalize the output
5. understand exactly what fields were mapped and what was left blank

## Positioning

Developer tools for repeatable public county parcel data exports.

It turns inconsistent public parcel data into normalized, developer-friendly files.
