import json

from county_parcel_toolkit.cli import main
from county_parcel_toolkit.discovery import ArcGISSearchResult, arcgis_search_url, rank_arcgis_results


def test_arcgis_search_url_builds_public_sharing_rest_query():
    url = arcgis_search_url("Spokane County WA parcel", limit=25)

    assert url.startswith("https://www.arcgis.com/sharing/rest/search?")
    assert "f=json" in url
    assert "num=25" in url
    assert "Spokane+County+WA+parcel" in url


def test_rank_arcgis_results_prefers_feature_services_with_parcel_signals():
    ranked = rank_arcgis_results(
        [
            ArcGISSearchResult(
                title="County Parks",
                item_id="parks",
                owner="gis",
                item_type="Feature Service",
                url="https://example.test/parks/FeatureServer",
                tags=["parks"],
                snippet="Park boundaries",
            ),
            ArcGISSearchResult(
                title="Current Parcels",
                item_id="parcels",
                owner="gis",
                item_type="Feature Service",
                url="https://example.test/parcels/FeatureServer",
                tags=["parcel", "assessor"],
                snippet="County assessor parcel polygons",
            ),
            ArcGISSearchResult(
                title="Parcel metadata PDF",
                item_id="pdf",
                owner="gis",
                item_type="PDF",
                url="https://example.test/parcel.pdf",
                tags=["parcel"],
                snippet="Documentation",
            ),
        ]
    )

    assert ranked[0].item_id == "parcels"
    assert ranked[0].score > ranked[1].score
    assert "feature_service" in ranked[0].reasons
    assert "parcel_signal" in ranked[0].reasons


def test_discover_arcgis_cli_outputs_ranked_candidates(monkeypatch, capsys):
    def fake_discover(query, limit=10):
        assert query == "Spokane County WA parcel"
        assert limit == 2
        return [
            ArcGISSearchResult(
                title="Current Parcels",
                item_id="abc123",
                owner="GISspokane",
                item_type="Feature Service",
                url="https://example.test/arcgis/rest/services/Parcels/FeatureServer",
                tags=["parcel"],
                snippet="Parcel layer",
                score=125,
                reasons=["feature_service", "parcel_signal"],
            )
        ]

    monkeypatch.setattr("county_parcel_toolkit.cli.discover_arcgis_sources", fake_discover)

    assert main(["discover", "arcgis", "Spokane County WA parcel", "--limit", "2"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["title"] == "Current Parcels"
    assert payload[0]["item_id"] == "abc123"
    assert payload[0]["score"] == 125
