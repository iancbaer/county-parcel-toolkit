"""Small local web-application shell for county-parcel-toolkit.

This intentionally uses the Python standard library so the repo has an
updateable application surface without taking on a web framework dependency yet.
The CLI can render the page, report JSON status, or serve it locally.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

CAPABILITIES = (
    "arcgis_discovery",
    "arcgis_export",
    "field_mapping",
    "join_validation",
    "normalization",
)


def status_payload() -> dict[str, Any]:
    """Return machine-readable app health and capability metadata."""

    return {
        "application": "county-parcel-toolkit",
        "status": "ok",
        "capabilities": list(CAPABILITIES),
        "interfaces": {
            "home": "/",
            "status": "/api/status",
        },
    }


def render_home_page() -> str:
    """Render the first local operator interface."""

    capability_items = "\n".join(f"        <li>{capability.replace('_', ' ')}</li>" for capability in CAPABILITIES)
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>County Parcel Toolkit</title>
  <style>
    :root {{ color-scheme: dark; --gold: #d6a847; --bg: #0b0b0b; --panel: #151515; --text: #f2efe8; --muted: #aaa; }}
    body {{ margin: 0; background: var(--bg); color: var(--text); font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif; }}
    main {{ max-width: 920px; margin: 0 auto; padding: 56px 24px; }}
    h1 {{ font-size: clamp(2.25rem, 7vw, 5rem); line-height: .95; margin: 0 0 18px; letter-spacing: -0.06em; }}
    .tagline {{ color: var(--gold); font-size: 1.05rem; text-transform: uppercase; letter-spacing: .14em; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 16px; margin-top: 36px; }}
    section {{ border: 1px solid #333; background: var(--panel); padding: 20px; min-height: 150px; }}
    h2 {{ margin: 0 0 12px; font-size: 1.2rem; color: var(--gold); }}
    p, li {{ color: var(--muted); line-height: 1.55; }}
    code {{ color: var(--text); background: #222; padding: 2px 5px; }}
  </style>
</head>
<body>
  <main>
    <div class=\"tagline\">Updateable local application shell</div>
    <h1>County Parcel Toolkit</h1>
    <p>Turn inconsistent public parcel sources into discovered, validated, normalized county-data exports.</p>
    <div class=\"grid\">
      <section>
        <h2>Discover sources</h2>
        <p>Search ArcGIS Online for likely public parcel FeatureServer candidates, then rank them with deterministic source signals.</p>
      </section>
      <section>
        <h2>Validate joins</h2>
        <p>Profile raw exports, infer field mappings, and measure whether enrichment tables actually join to parcel/address bases.</p>
      </section>
      <section>
        <h2>Normalize exports</h2>
        <p>Use source definitions to produce clean CSVs that downstream lead-gen and mapping workflows can reuse.</p>
      </section>
      <section>
        <h2>App API</h2>
        <p>Health/capability endpoint: <code>/api/status</code></p>
        <ul>
{capability_items}
        </ul>
      </section>
    </div>
  </main>
</body>
</html>
"""


class ParcelToolkitRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for the local application shell."""

    server_version = "CountyParcelToolkit/0.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path in ("/", "/index.html"):
            self._send_text(render_home_page(), "text/html; charset=utf-8")
            return
        if self.path == "/api/status":
            self._send_text(json.dumps(status_payload(), indent=2, sort_keys=True), "application/json; charset=utf-8")
            return
        self.send_error(404, "Not found")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        return

    def _send_text(self, body: str, content_type: str) -> None:
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Serve the local application until interrupted."""

    server = ThreadingHTTPServer((host, port), ParcelToolkitRequestHandler)
    print(f"County Parcel Toolkit app listening at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
