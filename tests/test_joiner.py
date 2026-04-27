from pathlib import Path

from county_parcel_toolkit.joiner import EnrichmentJoin, join_enrichments
from county_parcel_toolkit.tables import iter_records


def test_iter_records_sniffs_pipe_delimited_file(tmp_path: Path):
    source = tmp_path / "taxpayer.txt"
    source.write_text("parcel|taxpayer|zip\n25234.2210|BAER, RONALD G & PATRICIA L|99224\n", encoding="utf-8")

    assert list(iter_records(source)) == [
        {"parcel": "25234.2210", "taxpayer": "BAER, RONALD G & PATRICIA L", "zip": "99224"}
    ]


def test_join_enrichments_writes_clean_rows_without_metadata(tmp_path: Path):
    base = tmp_path / "base.csv"
    taxpayer = tmp_path / "taxpayer.csv"
    output = tmp_path / "joined.csv"
    base.write_text("parcel,site_addr,site_city\n25234.2210,720 S F ST,SPOKANE\n99999.0001,1 UNKNOWN RD,SPOKANE\n", encoding="utf-8")
    taxpayer.write_text(
        "parcel,taxpayer,address_1,zip\n25234.2210,BAER RONALD G & PATRICIA L,720 S F ST,99224-1913\n",
        encoding="utf-8",
    )

    stats = join_enrichments(
        base,
        output,
        "parcel",
        [EnrichmentJoin("taxpayer", taxpayer, "parcel", ("taxpayer", "address_1", "zip"))],
    )

    rows = list(iter_records(output))
    assert stats["joins"]["taxpayer"]["matched_rows"] == 1
    assert stats["joins"]["taxpayer"]["match_rate"] == 0.5
    assert rows[0]["taxpayer"] == "BAER RONALD G & PATRICIA L"
    assert rows[0]["address_1"] == "720 S F ST"
    assert "usage_note" not in rows[0]
    assert rows[1]["taxpayer"] == ""


def test_join_enrichments_prefixes_conflicting_field_names(tmp_path: Path):
    base = tmp_path / "base.csv"
    owner = tmp_path / "owner.csv"
    output = tmp_path / "joined.csv"
    base.write_text("parcel,city\n1,SPOKANE\n", encoding="utf-8")
    owner.write_text("parcel,city,taxpayer\n1,MAILING CITY,OWNER\n", encoding="utf-8")

    join_enrichments(base, output, "parcel", [EnrichmentJoin("taxpayer", owner, "parcel")])

    row = list(iter_records(output))[0]
    assert row["city"] == "SPOKANE"
    assert row["taxpayer_city"] == "MAILING CITY"
    assert row["taxpayer"] == "OWNER"
