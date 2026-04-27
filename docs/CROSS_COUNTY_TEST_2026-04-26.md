# Cross-county workflow test — 2026-04-26

Goal: test whether the county onboarding process still produces useful normalized parcel records outside Spokane County.

## Commands / artifacts

Scratch report:

```text
scratch/cross_county_test_v2/run_report.json
```

Verification:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q src
```

Result: 15 tests passed.

## Counties / layers tested

### King County, WA

Source:

```text
https://services.arcgis.com/Ej0PsM5Aw677QF1W/arcgis/rest/services/PARCEL_ADDRESS_PUB_AREA_3069/FeatureServer/0
```

Observed source count: 635,767 records.
Sample tested: 1,000 rows, 69 fields.

Accepted inferred mapping:

```json
{
  "parcel_id": ["PIN"],
  "owner": ["FULLNAME"],
  "situs_address": ["ADDR_FULL", "CONDOSITUS"],
  "mailing_address": ["KCTP_ADDR", "KCTP_CTYST"],
  "land_use": ["PREUSE_CODE", "PREUSE_DESC"],
  "year_built": [],
  "assessed_value": ["APPRLNDVAL", "APPR_IMPR"],
  "acreage": ["KCA_ACRES"]
}
```

Result: useful normalized parcel/address/mailing/value/acreage records. Owner field needs county-specific verification because `FULLNAME` is present but not populated in the first sampled row.

### Pierce County, WA

Source: existing full export in scratch from prior Pierce run.

Observed rows tested: 339,650 records, 35 fields.

Accepted inferred mapping:

```json
{
  "parcel_id": ["TaxParcelNumber", "TaxParcelComment"],
  "owner": ["Business_Name"],
  "situs_address": ["Site_Address", "Delivery_Address"],
  "mailing_address": ["Delivery_Address"],
  "land_use": ["Landuse_Description", "Use_Code"],
  "year_built": [],
  "assessed_value": ["Taxable_Value"],
  "acreage": ["Land_Acres"]
}
```

Result: strong normalized output with parcel ID, owner/business name, situs address, mailing address, land use, taxable value, and acreage.

### Washington statewide Current Parcels layer

Source:

```text
https://services.arcgis.com/jsIt88o09Q0r1j8h/arcgis/rest/services/Current_Parcels/FeatureServer/0
```

Observed source count: 3,321,859 records.
Sample tested: 2,000 rows, 17 fields.

Accepted inferred mapping:

```json
{
  "parcel_id": ["ORIG_PARCEL_ID", "PARCEL_ID_NR"],
  "owner": [],
  "situs_address": ["SITUS_ADDRESS", "SITUS_CITY_NM"],
  "mailing_address": [],
  "land_use": ["LANDUSE_CD", "ORIG_LANDUSE_CD"],
  "year_built": [],
  "assessed_value": ["VALUE_BLDG", "VALUE_LAND"],
  "acreage": []
}
```

Result: useful statewide base parcel/value layer, but not an ownership layer. This is useful for discovery and base geometry/address coverage, not enough for ownership records by itself.

### Cook County, IL

Source:

```text
https://gis.cookcountyil.gov/traditional/rest/services/cookVwrDynmc/MapServer/44
```

Observed source count: 1,419,180 records.
Sample tested: 2,000 rows, 52 fields.

Accepted inferred mapping:

```json
{
  "parcel_id": ["Key_Pin", "PIN14"],
  "owner": [],
  "situs_address": ["Address"],
  "mailing_address": ["Address"],
  "land_use": [],
  "year_built": [],
  "assessed_value": ["BldgValue", "LandValue"],
  "acreage": []
}
```

Result: useful parcel/address/assessment layer, but not owner data. Owner data likely requires a separate assessor table or API.

## Code change made during test

Expanded deterministic field aliases in `src/county_parcel_toolkit/mapper.py` after the first run exposed false/weak inference on common fields like `TaxParcelNumber`, `PIN14`, `KCA_ACRES`, `Taxable_Value`, `Landuse_Description`, and `Delivery_Address`.

## Conclusion

The method generalizes, but with an important distinction:

1. Parcel/address/value normalization works now across multiple counties and large ArcGIS layers.
2. Real ownership coverage is county-dependent. Some counties expose owner/taxpayer fields in the parcel layer; others require separate taxpayer, real-property, CAMA, treasurer, or assessor downloads joined by parcel/PIN/account ID.
3. The durable asset is the county source pack: base source + enrichment sources + proven joins + confidence notes.

Scaling target:

- US coverage: build a crawler/indexer that discovers county official parcel/assessor/GIS portals, creates source packs, then runs deterministic validation.
- Global coverage: abstract the same model to jurisdiction/source packs; countries differ more by cadastral law and privacy rules than by file format.
