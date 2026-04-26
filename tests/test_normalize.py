from county_parcel_toolkit.normalize import normalize_record


def test_normalize_record_uses_first_present_source_field():
    record = {
        "PIN": "35191.0201",
        "OWNER_NAME": "Example Owner",
        "PROPERTY_ADDRESS": "123 Main St",
        "YR_BUILT": "1978",
    }
    field_map = {
        "parcel_id": ["PARCEL_ID", "PIN", "APN"],
        "owner": ["OWNER", "OWNER_NAME"],
        "situs_address": ["SITUS_ADDRESS", "PROPERTY_ADDRESS"],
        "year_built": ["YEAR_BUILT", "YR_BUILT"],
    }

    normalized = normalize_record(record, field_map)

    assert normalized == {
        "parcel_id": "35191.0201",
        "owner": "Example Owner",
        "situs_address": "123 Main St",
        "year_built": "1978",
    }


def test_normalize_record_returns_blank_for_missing_fields():
    record = {"PIN": "35191.0201"}
    field_map = {"parcel_id": ["PIN"], "owner": ["OWNER", "OWNER_NAME"]}

    normalized = normalize_record(record, field_map)

    assert normalized == {"parcel_id": "35191.0201", "owner": ""}
