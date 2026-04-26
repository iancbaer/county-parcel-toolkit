import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_source(name: str) -> dict:
    return json.loads((ROOT / "examples" / "sources" / name).read_text(encoding="utf-8"))


def test_spokane_source_uses_real_public_parcel_layer():
    source = load_source("spokane_county_wa.json")

    assert source["source_type"] == "arcgis_feature_server"
    assert source["url"] == "https://services1.arcgis.com/ozNll27nt9ZtPWOn/arcgis/rest/services/Parcels/FeatureServer/0"


def test_spokane_source_records_rich_arcgis_hub_downloads():
    source = load_source("spokane_county_wa.json")

    rich_tables = {table["name"]: table for table in source["enrichment_sources"]}

    assert rich_tables["property_info"]["arcgis_item_id"] == "3912e26a8e0840538e17712275a444ec"
    assert rich_tables["value_info"]["arcgis_item_id"] == "fcb474736d0a4a5487893c5e56495b2f"
    assert rich_tables["taxpayer_info"]["arcgis_item_id"] == "f0e09368e2ac4d458b16436973d77104"
    assert rich_tables["residential_parcel_floor_information"]["arcgis_item_id"] == "3ffc682a258247068a4899d8003c3f0d"
    assert all(table["join_key"] == "parcel" for table in rich_tables.values())


def test_spokane_source_keeps_rcw_note_as_source_metadata():
    source = load_source("spokane_county_wa.json")
    taxpayer = next(table for table in source["enrichment_sources"] if table["name"] == "taxpayer_info")

    assert "RCW 42.56.070(8)" in taxpayer["usage_note"]
    assert "agency disclosure" in taxpayer["usage_note"]
    assert "public parcel records" in taxpayer["usage_note"]
