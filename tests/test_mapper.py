import csv

from county_parcel_toolkit.mapper import infer_field_map, join_profile, profile_csv


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_profile_csv_reports_headers_rows_nulls_and_distinct_counts(tmp_path):
    source = tmp_path / "parcels.csv"
    write_csv(
        source,
        [
            {"PARCELNO": "1001", "OWNER_NAME": "Ada LLC", "TOTAL_VALUE": "250000"},
            {"PARCELNO": "1002", "OWNER_NAME": "", "TOTAL_VALUE": "300000"},
        ],
    )

    profile = profile_csv(source)

    assert profile["row_count"] == 2
    assert profile["headers"] == ["PARCELNO", "OWNER_NAME", "TOTAL_VALUE"]
    assert profile["fields"]["OWNER_NAME"]["null_count"] == 1
    assert profile["fields"]["PARCELNO"]["distinct_count"] == 2


def test_infer_field_map_scores_common_county_aliases_from_headers_and_samples(tmp_path):
    source = tmp_path / "assessor.csv"
    write_csv(
        source,
        [
            {
                "PARCELNO": "1001",
                "OWNER_NAME": "Ada LLC",
                "SITUS_ADDR": "10 Main St",
                "YR_BUILT": "1984",
                "TOTAL_VALUE": "250000",
            },
            {
                "PARCELNO": "1002",
                "OWNER_NAME": "Grace Hopper",
                "SITUS_ADDR": "11 Main St",
                "YR_BUILT": "1992",
                "TOTAL_VALUE": "300000",
            },
        ],
    )

    inferred = infer_field_map(profile_csv(source))

    assert inferred["parcel_id"][0]["field"] == "PARCELNO"
    assert inferred["owner"][0]["field"] == "OWNER_NAME"
    assert inferred["situs_address"][0]["field"] == "SITUS_ADDR"
    assert inferred["year_built"][0]["field"] == "YR_BUILT"
    assert inferred["assessed_value"][0]["field"] == "TOTAL_VALUE"
    assert inferred["parcel_id"][0]["confidence"] == "high"


def test_join_profile_measures_overlap_duplicates_and_confidence(tmp_path):
    left = tmp_path / "parcels.csv"
    right = tmp_path / "values.csv"
    write_csv(left, [{"parcel": "1001"}, {"parcel": "1002"}, {"parcel": "1003"}])
    write_csv(right, [{"parcel": "1001"}, {"parcel": "1002"}, {"parcel": "1002"}, {"parcel": "9999"}])

    profile = join_profile(left, right, "parcel", "parcel")

    assert profile["left_rows"] == 3
    assert profile["right_rows"] == 4
    assert profile["overlap_count"] == 2
    assert profile["left_overlap_rate"] == 0.667
    assert profile["right_duplicate_keys"] == 1
    assert profile["confidence"] == "medium"
