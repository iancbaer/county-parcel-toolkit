# 51-Jurisdiction US County Pilot Result — 2026-04-26

Command run:

```bash
.venv/bin/python scripts/us_county_pilot.py \
  --sample-size 200 \
  --output scratch/us_county_pilot_51state_sample
```

Machine-readable report:

```text
scratch/us_county_pilot_51state_sample/run_report.json
```

## Summary

Targets tested: 51 — one county/county-equivalent per state plus DC.

Automated ArcGIS candidate selected: 45 / 51.

No queryable ArcGIS candidate found from the current search heuristic: 6 / 51.

Status distribution from the selected samples:

- owner_ready_candidate: 12
- base_or_value_candidate: 9
- thin_parcel_candidate: 16
- weak_candidate: 8
- no_selected: 6

Canonical field coverage among selected samples:

- parcel_id: 37
- owner: 25
- situs_address: 22
- mailing_address: 16
- land_use: 13
- year_built: 8
- assessed_value: 12
- acreage: 20

## Interpretation

This proves the harness can run across states quickly on local hardware and produce structured evidence. It does not prove that each selected source is the best/official countywide source.

The biggest gap is source authority/relevance ranking. ArcGIS search often returns:

- statewide parcel aggregators instead of county-owned data
- historical parcel layers
- tiny derivative project layers
- impact-area parcels
- unrelated layers that happen to contain parcel-like fields

That is useful as a discovery smoke test, but not sufficient for production coverage.

## States needing manual/next-pass discovery from this run

No selected queryable ArcGIS candidate from the current heuristic:

- AR — Pulaski County
- KS — Johnson County
- NH — Hillsborough County
- NY — Kings County
- RI — Providence County
- WY — Laramie County

Likely reason: these jurisdictions may use non-ArcGIS portals, city/state aggregators, county download pages, Socrata, static GIS downloads, or assessor/CAMA systems that need source-specific discovery.

## Selected candidates requiring authority validation

The following examples show why the next step is not “download all,” but “rank official sources first”:

- AZ / Maricopa selected `AZOwnershipParcels`, only 78 records — likely not countywide.
- TX / Harris selected `ParcelsImpacted_Cloverleaf`, 631 records — derivative/impact layer, not countywide.
- CO / Denver selected `Commonground_Parcels_Denver_Arapahoe_Counties`, 8 records — derivative/too small.
- MO / St. Louis selected a one-record home values layer — not acceptable.
- WV / Kanawha selected buyout polygons — parcel-like but not a general parcel source.
- FL / Miami-Dade selected Florida statewide parcels — useful aggregator, not county-owned.
- WA / King selected statewide current parcels in the automated run, while manual search already found better official King County layers.

## What this says about scaling

The workflow is feasible. The missing product layer is source governance:

1. official-source scoring
2. jurisdiction/source registry
3. support for non-ArcGIS source types
4. full export only after source is validated
5. separate owner/taxpayer enrichment discovery when the base parcel source is thin

## Next build step

Add a `source authority score` to the pilot:

- official_domain_match
- official_owner_match
- title_relevance
- countywide_record_count_plausibility
- stale/historical penalty
- derivative/project-layer penalty
- statewide_aggregator flag
- owner_field_present flag
- base_parcel_fields_present flag

Then rerun all 51 and promote only validated candidates into `examples/sources/`.
