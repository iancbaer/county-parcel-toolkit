# US County Pilot Plan

Goal: validate the county-parcel-toolkit workflow across the United States before scaling to full county coverage.

## Core question

Can the same approach work across states?

Answer: yes for the architecture, but not as a single uniform source type. The repeatable unit is a county/jurisdiction source pack:

1. discover official public parcel/assessor/GIS sources
2. classify source role: base parcel/address, owner/taxpayer, valuation, building, sales
3. export a bounded sample first
4. profile fields and infer canonical mappings
5. prove joins between base and enrichment tables
6. normalize clean data rows
7. write source pack + confidence report

Some states/counties expose owner data directly in a parcel layer. Others expose only parcel/address/value data and require separate assessor, taxpayer, CAMA, recorder, or treasurer enrichment sources.

## Hardware feasibility on ICB-core

Observed local machine during planning:

- Memory: 30 GiB total, about 22 GiB available at check time
- CPU: 20 logical cores
- Disk: about 1.4 TiB available on `/`
- Current project scratch: 356 MiB after Spokane/Pierce/cross-county tests

Feasibility:

- One-county-per-state sample test: easy; under 1 GB in normal sample mode.
- One-county-per-state full attribute downloads: feasible on current hardware.
- Conservative storage scenarios for 51 jurisdictions:
  - 100 MB each: about 5 GB total
  - 500 MB each: about 25 GB total
  - 2 GB each: about 102 GB total

The bottleneck is not RAM or disk. The bottleneck is source discovery quality, network time, server paging limits, throttling, and legal/source-specific access rules.

## Pilot phases

### Phase 1 — sample-only 51-jurisdiction smoke test

Run bounded ArcGIS discovery/export samples for one county or county-equivalent in every state plus DC.

Command:

```bash
.venv/bin/python scripts/us_county_pilot.py \
  --sample-size 200 \
  --output scratch/us_county_pilot_51state_sample
```

Outputs:

```text
scratch/us_county_pilot_51state_sample/run_report.json
scratch/us_county_pilot_51state_sample/<state>_<county>/sample.csv
scratch/us_county_pilot_51state_sample/<state>_<county>/normalized_sample.csv
scratch/us_county_pilot_51state_sample/<state>_<county>/auto_mapping.json
```

Success metrics:

- discovered queryable candidate layer
- exports a sample without geometry
- maps parcel_id
- maps at least one address or valuation field
- flags whether owner fields are present

### Phase 2 — authority and relevance hardening

ArcGIS search can return statewide layers, stale layers, private derivative layers, or irrelevant layers. The pilot now writes an `authority` block for each viable candidate:

```json
{
  "score": 142,
  "decision": "promote_source_pack_candidate",
  "signals": ["county_name_match", "parcel_title", "countywide_plausible_count"],
  "penalties": []
}
```

The score is intentionally a gate, not the final product. It exists to keep us from getting lost: the system should produce a small queue of candidates to review and promote into source packs, not pretend it solved every county automatically.

Current scoring rules:

- prefer official county/city/state GIS owners and domains
- prefer titles containing parcels, tax parcels, assessor parcels, real property, CAMA
- reward plausible countywide record counts
- reward mapped parcel ID, address, owner, value, land-use, and acreage fields
- demote permits, transit, parks, schools, community centers, zoning-only, impact-only, stale/historical layers unless explicitly requested
- demote derivative/project layers such as clips, buffers, buyouts, flood/FEMA subsets, covenants, apartment-only/mobile-home-only subsets
- flag statewide aggregators separately
- hard-stop implausibly tiny record counts from auto-promotion even when the fields look rich

### Phase 3 — source packs for winners

For each state, choose the best official county source and create:

```text
examples/sources/<county>_<state>.json
docs/<COUNTY>_<STATE>.md
```

Each source pack should identify:

- base parcel/address source
- owner/taxpayer source if separate
- valuation source if separate
- join key and join confidence
- source metadata/terms
- normalized fields available
- gaps

### Phase 4 — full exports for validated counties

Only after source quality is proven, run full exports with streaming/chunked downloads.

Rules:

- `returnGeometry=false` for attribute-first exports
- chunk by OBJECTID or service-supported pagination
- keep raw downloads under scratch/data, not git
- create summaries and normalized outputs
- archive source packs, not raw personal-data-heavy records

## Initial smoke-test observation

A 5-state smoke run proved the harness works technically, but also showed why source relevance scoring matters:

- AZ / Maricopa search found an owner-like parcel candidate, but it was a tiny 78-record layer and needs official-source validation.
- FL / Miami-Dade search found a Florida statewide parcel layer, useful but not county-specific ownership.
- IL / Cook search found parcel history, but separate current assessment/owner source selection still needs authority ranking.
- TX / Harris search found an impacted-area parcel derivative, not necessarily the official countywide source.
- WA / King search found a statewide current parcels layer; earlier manual search found better King County official layers.

Conclusion: automated search/export works, but source authority ranking is the next necessary step before claiming each state is covered.

## Product implication

The scalable public product is not “one scraper.” It is:

- a source discovery engine
- a source-pack registry
- a deterministic validation/normalization engine
- a county/jurisdiction status dashboard

For US coverage, the registry should track about 3,000+ county/county-equivalent jurisdictions, with state-level aggregators used where available.
