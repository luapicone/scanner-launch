from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from scanner_launch.models import to_dict
from scanner_launch.services.risk import RiskAnalyzerService
from scanner_launch.services.discovery import DiscoveryService
from scanner_launch.services.scan import BatchScanService


class ScannerWebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str | None = None, **kwargs):
        self.discovery_service = DiscoveryService()
        self.risk_service = RiskAnalyzerService()
        self.scan_service = BatchScanService(self.discovery_service, self.risk_service)
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/scan":
            self._handle_scan(parsed.query)
            return
        if parsed.path == "/api/discover":
            self._handle_discover(parsed.query)
            return
        if parsed.path == "/api/analyze":
            self._handle_analyze(parsed.query)
            return
        super().do_GET()

    def _handle_scan(self, query: str) -> None:
        params = parse_qs(query)
        limit = self._to_int(params.get("limit", ["20"])[0], 20)
        max_age_hours = self._to_int(params.get("maxAgeHours", ["24"])[0], 24)
        result = self.scan_service.scan(limit=limit, max_age_hours=max_age_hours)
        self._send_json(to_dict(result))

    def _handle_discover(self, query: str) -> None:
        params = parse_qs(query)
        limit = self._to_int(params.get("limit", ["20"])[0], 20)
        max_age_hours = self._to_int(params.get("maxAgeHours", ["24"])[0], 24)
        result = self.discovery_service.discover(limit=limit, max_age_hours=max_age_hours)
        self._send_json(to_dict(result))

    def _handle_analyze(self, query: str) -> None:
        params = parse_qs(query)
        token = params.get("token", [""])[0]
        chain = params.get("chain", [None])[0]
        if not token:
            self._send_json({"error": "Missing token parameter"}, status=HTTPStatus.BAD_REQUEST)
            return
        result = self.risk_service.analyze(token=token, chain=chain)
        self._send_json(to_dict(result))

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _to_int(self, value: str, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    web_dir = Path(__file__).resolve().parents[2] / "web"

    def handler(*args, **kwargs):
        return ScannerWebHandler(*args, directory=str(web_dir), **kwargs)

    server = ThreadingHTTPServer((host, port), handler)
    print(f"Scanner UI running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
