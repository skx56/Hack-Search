#!/usr/bin/env python3
"""Local server with a Refresh button API for the hackathon list."""

from __future__ import annotations

import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from scrape import OUTPUT_DIR, run_scrape

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8765

_refresh_lock = threading.Lock()
_refresh_state = {"running": False, "last_error": None}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(OUTPUT_DIR), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[server] {self.address_string()} - {fmt % args}")

    def do_GET(self):  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self.path = "/hackathons.html"
            return super().do_GET()
        if path == "/api/health":
            return self._json(200, {"ok": True, "refreshing": _refresh_state["running"]})
        if path == "/api/hackathons":
            data_path = OUTPUT_DIR / "hackathons.json"
            if not data_path.exists():
                return self._json(404, {"error": "No data yet. POST /api/refresh first."})
            payload = json.loads(data_path.read_text(encoding="utf-8"))
            return self._json(200, payload)
        return super().do_GET()

    def do_POST(self):  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/refresh":
            return self._json(404, {"error": "Not found"})

        if _refresh_state["running"]:
            return self._json(409, {"error": "Refresh already running"})

        with _refresh_lock:
            if _refresh_state["running"]:
                return self._json(409, {"error": "Refresh already running"})
            _refresh_state["running"] = True
            _refresh_state["last_error"] = None

        try:
            print("[server] Refresh started…")
            payload = run_scrape(exclude_web3=True)
            print(f"[server] Refresh done — {payload['total_filtered']} events")
            return self._json(
                200,
                {
                    "ok": True,
                    "total_filtered": payload["total_filtered"],
                    "total_raw": payload["total_raw"],
                    "scraped_at": payload["scraped_at"],
                },
            )
        except Exception as exc:  # noqa: BLE001
            _refresh_state["last_error"] = str(exc)
            print(f"[server] Refresh failed: {exc}")
            return self._json(500, {"error": str(exc)})
        finally:
            _refresh_state["running"] = False

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not (OUTPUT_DIR / "hackathons.html").exists():
        print("No existing list found — running initial scrape…")
        run_scrape(exclude_web3=True)

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Hackathon list ready at http://{HOST}:{PORT}")
    print("Click Refresh in the UI anytime to pull the latest events.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
