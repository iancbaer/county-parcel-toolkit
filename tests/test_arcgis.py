from county_parcel_toolkit.arcgis import ArcGISLayer


def test_count_url_encodes_return_count_query():
    layer = ArcGISLayer("https://example.test/FeatureServer/0")

    url = layer.count_url()

    assert url == "https://example.test/FeatureServer/0/query?f=json&where=1%3D1&returnCountOnly=true"


def test_query_url_builds_chunked_attribute_export_query():
    layer = ArcGISLayer("https://example.test/FeatureServer/0")

    url = layer.query_url(offset=2000, limit=1000)

    assert "where=1%3D1" in url
    assert "returnGeometry=false" in url
    assert "outFields=%2A" in url
    assert "orderByFields=OBJECTID" in url
    assert "resultOffset=2000" in url
    assert "resultRecordCount=1000" in url
