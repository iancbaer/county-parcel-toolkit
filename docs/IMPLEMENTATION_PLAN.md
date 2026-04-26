# County Parcel Data Toolkit Implementation Plan

> For Hermes: Use test-driven-development for every behavior change.

Goal: Build a public, developer-first toolkit for downloading and normalizing public parcel/assessor records without lead-generation or outreach features.

Architecture: A small Python package with source-specific adapters, a common normalization layer, and a CLI. Keep downloaded data out of git. Keep public code focused on public-data plumbing only.

Tech Stack: Python 3.10+, stdlib-first HTTP/CSV/JSON, pytest for tests.

## Phase 1: ArcGIS FeatureServer MVP

- Build ArcGIS URL/query helpers.
- Support count, field inspection, and chunked attribute CSV export.
- Normalize CSV rows with simple JSON field maps.
- Provide CLI entry point `parceltool`.

## Phase 2: Source definitions

- Define source JSON schema.
- Validate source files.
- Add real public examples with URLs, no bundled records.

## Phase 3: More source types

- Socrata datasets.
- CKAN packages.
- Static CSV downloads.
- Zipped shapefile/GeoPackage downloads.

## Phase 4: Developer polish

- Publish package docs.
- Add CI.
- Add examples for Spokane County and one non-WA county.
- Add contribution guide and code of conduct if the repo gains traction.

## Boundary

Do not add enrichment, targeting, lead scoring, DNC workflows, or outreach automation to the public repo. Those belong in private ParcelSearch Lead Engine work.
