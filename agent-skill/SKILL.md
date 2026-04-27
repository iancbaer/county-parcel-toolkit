---
name: county-parcel-mapper
description: Agent playbook for discovering public county parcel/assessor sources, inferring how raw county tables map into a canonical parcel schema, and producing reusable source packs for county-parcel-toolkit.
version: 0.1.0
author: Ian Baer + Rook
license: MIT
metadata:
  hermes:
    category: operations
    tags: [county, parcels, assessor, gis, arcgis, public-data, mapping, normalization]
---

# County Parcel Mapper

Use this skill when asked to find, map, normalize, or compare public county parcel/assessor data. The goal is not merely to download one county's file; the goal is to produce reusable mapping knowledge that any code-capable agent can apply again.

## Hybrid design

This skill assumes a hybrid system:

- deterministic code does the bulk work: source downloads, field profiling, null/duplicate stats, join tests, schema validation, normalization, regression tests, and repeatable exports
- AI is used sparingly for judgment: interpreting unfamiliar county metadata, classifying table roles, suggesting likely field meanings, identifying suspicious joins, explaining caveats, and giving the user a conversational interface
- AI outputs must become structured artifacts: source JSON, confidence reports, docs, tests, and TODOs that regular code can validate

Good outcome: the agent says, "I think these three tables join on parcel_id with high confidence because code found 99.7% overlap and low duplicates; these 11 fields map cleanly; these 8 fields are useful but unmapped."

Bad outcome: the agent dumps a giant CSV, guesses field names silently, or treats a one-off script as the product.

## Core stance

- This is public-data plumbing: discover public sources, download safely, preserve source metadata, and normalize fields.
- Do not treat county-specific legal/disclaimer text as a new toolkit restriction unless it clearly applies to downstream users. Preserve the source terms/metadata and state what the toolkit does.
- Do not bypass access controls, CAPTCHAs, logins, paywalls, or rate limits.
- Keep downloaded records out of git. Commit only code, docs, source definitions, schemas, and small synthetic fixtures.

## Repository path

Default local repo path on Ian's ICB-core:

```text
/home/iancbaer/Documents/Rook/PublicProjects/county-parcel-toolkit
```

Run commands from that directory unless told otherwise.

## Standard workflow

1. Identify the county and state.
2. Discover public data sources:
   - assessor/property search pages
   - GIS/open-data portals
   - ArcGIS Hub / ArcGIS REST services
   - Socrata, CKAN, static CSV/XLSX/ZIP/shapefile/GeoPackage downloads
3. Prefer bulk/download/API sources over scraping individual parcel pages.
4. For each candidate source, record:
   - source URL
   - source type
   - table/layer name
   - available fields
   - record count if cheaply available
   - download/API pattern
   - source terms/disclaimers as metadata
5. Classify each table's role:
   - `parcel_geometry`
   - `property_facts`
   - `owner_taxpayer`
   - `mailing_address`
   - `valuation`
   - `tax_history`
   - `sales_history`
   - `building_residential`
   - `permits`
   - `unknown_useful`
6. Infer join keys across tables:
   - Prefer parcel/account/property IDs.
   - Validate null rate, duplicate rate, and sample overlap.
   - Use normalized address fallback only as low-confidence evidence; do not silently fuzzy-join without reporting confidence.
7. Infer field mappings into the canonical schema.
8. Produce a source pack and confidence report.
9. Verify with tests or at least schema validation before committing.

## Mapping target

Start with this canonical schema, expanding only when there is a clear source field and downstream value:

```text
parcel_id
owner
situs_address
mailing_address
land_use
year_built
assessed_value
acreage
county
state
source_url
property_class
tax_year
market_value_land
market_value_improvement
market_value_total
taxable_value
sale_date
sale_price
building_sqft
finished_sqft
bedrooms
bathrooms
```

## Field inference heuristics

Score fields using all available evidence, not name matching alone.

### Strong signals

- Exact or near-exact aliases:
  - `parcel`, `parcel_id`, `parcelno`, `pin`, `apn`, `tax_parcel`, `property_id` -> `parcel_id`
  - `owner`, `owner_name`, `taxpayer`, `taxpayer_name`, `name1` -> `owner`
  - `situs`, `site_addr`, `property_address`, `location_address` -> `situs_address`
  - `mailing`, `mail_addr`, `address_1`, `owner_address` -> `mailing_address`
  - `land_use`, `use_code`, `prop_use`, `property_class` -> `land_use` / `property_class`
  - `year_built`, `yr_built`, `built`, `effective_year` -> `year_built`
  - `assessed`, `taxable`, `market`, `mkt_total`, `total_value` -> valuation fields
  - `acres`, `acreage`, `land_acres`, `shape_area` -> `acreage` only when units are known
- Sample value shape:
  - parcel IDs often repeat across assessor tables and are mostly non-null strings/numbers
  - owner fields contain person/entity names, not numeric codes
  - ZIP/state/city fields can assemble mailing addresses
  - value fields are numeric money-like columns
  - year fields are four-digit years in plausible ranges
- Table context:
  - fields in a taxpayer table are more likely owner/mailing fields
  - fields in a value table are more likely assessed/market/tax fields
  - fields in a floor/building table are more likely bedrooms/bathrooms/sqft/year-built fields

### Weak signals / warnings

- Similar names with different meaning, e.g. `tax_area`, `tax_code`, `use_code`, `class_code`.
- Geometry area is not acreage unless units/projection conversion are known.
- Owner and taxpayer can differ; preserve distinction in metadata when possible.
- Situs and mailing address can differ; do not merge unless the source only has one address concept.

## Source pack format

Create or update `examples/sources/<county>_<state>.json` with:

```json
{
  "county": "Example County",
  "state": "WA",
  "source_type": "arcgis_feature_server",
  "url": "https://example/FeatureServer/0",
  "notes": ["Plain facts about source shape and quirks."],
  "field_map": {
    "parcel_id": ["parcel", "PARCEL_ID"],
    "owner": ["owner_name", "taxpayer"],
    "situs_address": ["site_addr"],
    "mailing_address": ["mail_addr"],
    "land_use": ["use_desc"],
    "year_built": ["yr_built"],
    "assessed_value": ["assessed_total"],
    "acreage": ["acreage"]
  },
  "enrichment_sources": [
    {
      "name": "value_info",
      "source_type": "download",
      "download_url": "https://example/value.csv",
      "format": "csv",
      "join_key": "parcel_id",
      "role": "valuation",
      "useful_fields": ["parcel_id", "tax_year", "market_total"],
      "usage_note": "Source metadata only; no toolkit-imposed restriction."
    }
  ],
  "mapping_confidence": {
    "overall": "medium",
    "join_key": "high",
    "field_map": "medium"
  }
}
```

Do not invent URLs, item IDs, or fields. If a field is inferred, mark confidence; if verified by metadata/sample rows, say so.

## Confidence report

For each county, add a short doc under `docs/<COUNTY>_<STATE>.md` with:

- Source summary
- Download/API URLs
- Table role classification
- Join keys and confidence
- Mapped fields
- Useful unmapped fields
- Known gaps/quirks
- Source terms/disclaimer metadata
- Verification commands/results

## Verification commands

From the repo:

```bash
.venv/bin/python -m pytest
```

If the venv is missing:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
python -m pytest
```

Useful CLI checks:

```bash
parceltool arcgis fields <FeatureServer-layer-url>
parceltool arcgis count <FeatureServer-layer-url>
parceltool arcgis export <FeatureServer-layer-url> scratch/<county>/raw.csv --chunk-size 2000
parceltool map profile scratch/<county>/raw.csv
parceltool map infer scratch/<county>/raw.csv
parceltool map join scratch/<county>/raw.csv scratch/<county>/enrichment.csv --left-key parcel --right-key parcel
parceltool normalize scratch/<county>/raw.csv scratch/<county>/normalized.csv --mapping examples/sources/<county>_<state>.json
```

The `map` commands are the executable bridge between the skill and the codebase. Use them to test AI suggestions before accepting them into a source pack.

## Output expectations for agent runs

When a code-capable agent uses this skill, it should return:

1. What public sources were found.
2. What tables/layers appear valuable.
3. The inferred joins and confidence.
4. The canonical fields mapped and unmapped useful fields.
5. Files created/changed.
6. Verification result.
7. Any county-specific caveats that should become reusable mapping knowledge.

Keep public project language professional and functional. Do not add wink-wink disclaimers or deny sensitive downstream use cases; just state that the toolkit downloads and normalizes public parcel records.
