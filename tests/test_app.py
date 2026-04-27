import json

from county_parcel_toolkit.cli import main


def test_status_payload_describes_application_capabilities():
    from county_parcel_toolkit.app import status_payload

    payload = status_payload()

    assert payload["application"] == "county-parcel-toolkit"
    assert payload["status"] == "ok"
    assert "arcgis_discovery" in payload["capabilities"]
    assert "normalization" in payload["capabilities"]
    assert "field_mapping" in payload["capabilities"]


def test_home_page_renders_updateable_operator_interface():
    from county_parcel_toolkit.app import render_home_page

    html = render_home_page()

    assert "County Parcel Toolkit" in html
    assert "Discover sources" in html
    assert "Normalize exports" in html
    assert "Updateable local application shell" in html
    assert "/api/status" in html


def test_app_status_cli_outputs_json(capsys):
    assert main(["app", "status"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["application"] == "county-parcel-toolkit"
    assert payload["status"] == "ok"


def test_app_render_cli_outputs_html(capsys):
    assert main(["app", "render"]) == 0

    html = capsys.readouterr().out
    assert "<!doctype html>" in html.lower()
    assert "County Parcel Toolkit" in html
