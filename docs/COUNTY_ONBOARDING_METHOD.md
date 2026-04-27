# County Onboarding and Clean Join Method

Goal: for any county, build a repeatable source pack that downloads public parcel/address data, discovers owner/taxpayer and other enrichment tables, proves join quality, and outputs a clean joined CSV without per-row source disclaimers or metadata noise.

## Core model

Treat every county as a bundle, not a single file.

1. Base parcel/address source
   - Usually parcel geometry, assessor parcel layer, or property-info table.
   - Required fields: parcel/account ID and situs address or address components.

2. Owner/taxpayer source
   - Owner name, taxpayer name, mailing address, care-of, role percentage if present.
   - Join to base source by parcel/account/property ID.

3. Value/use/building/sales sources
   - Assessed or market values, land use, year built, bedrooms, bathrooms, square footage, sale date/price.
   - Join by parcel/account/property ID.
   - If there are multiple rows per parcel, define a deterministic aggregation rule before joining.

4. Source metadata
   - Source URLs, item IDs, county notes, and source-provided notices stay in the source pack and docs.
   - They are not written into the cleaned row output.

## Discovery sequence for a new county

Use this order. Stop only when the join is proven, not when a likely-looking file is found.

1. Search official county pages for:
   - assessor download
   - parcel download
   - property information download
   - tax/treasurer download
   - GIS open data
   - ArcGIS Hub or FeatureServer
   - Socrata/CKAN/open data portal

2. Identify candidate source roles:
   - `base_parcel_address`
   - `owner_taxpayer`
   - `mailing_address`
   - `valuation`
   - `land_use`
   - `building_residential`
   - `sales_history`

3. Download public files into scratch space only:
   - `scratch/<state>/<county>/downloads/`
   - Never commit raw records.

4. Profile every candidate table:

   ```bash
   parceltool map profile scratch/<state>/<county>/downloads/<file>
   parceltool map infer scratch/<state>/<county>/downloads/<file>
   ```

5. Validate join candidates:

   ```bash
   parceltool map join base.csv owner.csv --left-key parcel --right-key parcel
   ```

6. Accept a join only when:
   - base overlap is >= 95% for the intended base population, or the missing population is explainable
   - right-side duplicate keys are zero, or a documented pre-aggregation rule exists
   - spot checks against the county search UI match known addresses/owners

7. Produce a clean wide join:

   ```bash
   parceltool map merge base.csv joined.csv \
     --base-key parcel \
     --join taxpayer=taxpayer_info.xlsx:parcel:taxpayer,address_1,address_2,city,state,zip \
     --join value=value_info.txt:parcel:tax_year,prop_use_desc,mkt_total,taxable_reg
   ```

8. Normalize the joined file into canonical columns if needed:

   ```bash
   parceltool normalize joined.csv normalized.csv --mapping examples/sources/<county>_<state>.json
   ```

## Source pack requirements

Each county gets `examples/sources/<county>_<state>.json`.

Required keys:

```json
{
  "name": "Example County, ST parcels",
  "source_type": "bundle",
  "base_source": {
    "name": "parcels",
    "url": "https://official.example/source",
    "format": "csv|pipe|xlsx|arcgis_feature_server",
    "role": "base_parcel_address",
    "key": "parcel"
  },
  "field_map": {
    "parcel_id": ["parcel"],
    "owner": ["taxpayer", "owner_name"],
    "situs_address": ["site_addr", "site_address"],
    "mailing_address": ["mail_addr", "address_1"],
    "land_use": ["prop_use_desc"],
    "year_built": ["year_built"],
    "assessed_value": ["mkt_total", "taxable_reg"],
    "acreage": ["acreage"]
  },
  "enrichment_sources": [
    {
      "name": "taxpayer",
      "download_url": "https://official.example/taxpayer.xlsx",
      "format": "xlsx",
      "role": "owner_taxpayer",
      "join_key": "parcel",
      "output_fields": ["taxpayer", "address_1", "address_2", "city", "state", "zip"]
    }
  ],
  "join_expectations": {
    "base_key": "parcel",
    "minimum_base_overlap": 0.95,
    "right_duplicate_policy": "reject unless pre-aggregated"
  },
  "source_metadata": {
    "notes": ["Source notices live here, not in cleaned rows."]
  }
}
```

## Clean output policy

Cleaned output may include:

- parcel_id / parcel
- owner / taxpayer
- situs address
- mailing address
- land use
- value fields
- building facts
- sale facts
- source_url if explicitly requested for traceability

Cleaned output must not include:

- county disclaimer text repeated per row
- source-pack notes
- legal commentary
- agent confidence prose
- HTML snippets from portals

Those belong in docs and source metadata only.

## Spokane proof of pattern

Spokane County proves the method works:

- Base parcel/address layer: 214,005 distinct parcel IDs
- Bulk taxpayer file: 362,764 distinct parcel IDs
- Join key: `parcel`
- Matched base parcels: 214,004
- Missing base parcels: 1
- Known spot check: `720 S F ST` -> `25234.2210` -> `BAER, RONALD G & PATRICIA L`

This is the template for new counties: discover official public tables, classify roles, prove join quality, write source pack, then output clean joined data.
