import csv
import json

from county_parcel_toolkit.cli import main


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_map_infer_cli_outputs_machine_readable_mapping_candidates(tmp_path, capsys):
    source = tmp_path / "assessor.csv"
    write_csv(
        source,
        [
            {"PARCELNO": "1001", "OWNER_NAME": "Ada LLC", "TOTAL_VALUE": "250000"},
            {"PARCELNO": "1002", "OWNER_NAME": "Grace Hopper", "TOTAL_VALUE": "300000"},
        ],
    )

    assert main(["map", "infer", str(source)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["parcel_id"][0]["field"] == "PARCELNO"
    assert payload["owner"][0]["field"] == "OWNER_NAME"
    assert payload["assessed_value"][0]["field"] == "TOTAL_VALUE"


def test_map_join_cli_outputs_join_confidence(tmp_path, capsys):
    left = tmp_path / "parcels.csv"
    right = tmp_path / "values.csv"
    write_csv(left, [{"parcel": "1001"}, {"parcel": "1002"}])
    write_csv(right, [{"parcel": "1001"}, {"parcel": "1002"}])

    assert main(["map", "join", str(left), str(right), "--left-key", "parcel", "--right-key", "parcel"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["overlap_count"] == 2
    assert payload["confidence"] == "high"
