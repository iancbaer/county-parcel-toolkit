# Spokane County, WA source notes

Spokane is a good example of why the toolkit should treat a county as a bundle of related public sources, not as a single parcel layer.

## What the thin parcel layer gives us

Primary parcel layer:

`https://services1.arcgis.com/ozNll27nt9ZtPWOn/arcgis/rest/services/Parcels/FeatureServer/0`

This layer is useful for geometry/basic situs data, but it only exposes a small set of attributes such as parcel, site address, city, acreage, and shape fields. It does not expose taxpayer, assessed value, tax year, property use, or building detail fields.

## How the richer files were found

Use ArcGIS Online's Sharing REST search against the Spokane GIS owner account:

`https://www.arcgis.com/sharing/rest/search?f=json&q=owner%3AGISspokane%20%28parcel%20OR%20parcels%20OR%20assessor%20OR%20taxpayer%20OR%20value%20OR%20residential%29&num=100`

The high-signal results are downloadable ArcGIS Hub items. Each can be downloaded with:

`https://www.arcgis.com/sharing/rest/content/items/<ITEM_ID>/data`

## Rich enrichment tables

| Table | Item ID | Use | Join key |
| --- | --- | --- | --- |
| property_info | 3912e26a8e0840538e17712275a444ec | property type, full site address fields, city, status, TCA, use description, size/uom, inspection cycle | parcel |
| value_info | fcb474736d0a4a5487893c5e56495b2f | tax year, use code/description, land value, improvement value, new construction, market total, taxable value | parcel |
| taxpayer_info | f0e09368e2ac4d458b16436973d77104 | taxpayer name and mailing address fields | parcel |
| residential_parcel_floor_information | 3ffc682a258247068a4899d8003c3f0d | building/floor square footage, finished area, bedrooms, bathrooms | parcel |

## Recommended enrichment strategy

1. Export the public parcel FeatureServer for parcel IDs, geometry, site address, city, and acreage.
2. Download the rich ArcGIS Hub files listed in `examples/sources/spokane_county_wa.json`.
3. Parse pipe-delimited `.txt` files where available; prefer those over spreadsheets for repeatable CLI processing.
4. Join enrichment tables on `parcel`.
5. For `value_info`, keep the latest `tax_year` row per parcel for current values.
6. For residential floor data, aggregate by parcel:
   - `sq_ft` sum
   - `fin_area` sum
   - `bedrooms` max or sum depending downstream use; document the choice
   - `bathrooms` max or sum depending downstream use; document the choice

## Legal/use note

Spokane County's ArcGIS Hub disclaimer cites RCW 42.56.070(8). That public-records provision governs agency disclosure of lists of individuals requested for commercial purposes; it is not a special restriction added by this toolkit. The toolkit simply downloads, joins, and normalizes public parcel data while preserving source metadata for downstream users.
