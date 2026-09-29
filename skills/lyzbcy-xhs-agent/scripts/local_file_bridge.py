#!/usr/bin/env python3
"""Serve one authorized local file once to an exact browser Origin."""

from __future__ import annotations

import argparse
import json
import mimetypes
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlsplit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, type=Path, help="Local file authorized for upload")
    parser.add_argument("--origin", default="https://creator.xiaohongshu.com", help="Exact allowed page Origin")
    parser.add_argument("--port", type=int, default=18766, help="Loopback port")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = args.file.expanduser().resolve(strict=True)
    if not path.is_file():
        raise SystemExit(f"not a file: {path}")

    parsed_origin = urlsplit(args.origin)
    if parsed_origin.scheme not in {"http", "https"} or not parsed_origin.netloc:
        raise SystemExit("--origin must be an exact http(s) Origin")
    allowed_origin = f"{parsed_origin.scheme}://{parsed_origin.netloc}"

    token = secrets.token_urlsafe(24)
    route = f"/{token}/{quote(path.name)}"
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    class Handler(BaseHTTPRequestHandler):
        def _cors(self) -> None:
            request_origin = self.headers.get("Origin")
            if request_origin == allowed_origin:
                self.send_header("Access-Control-Allow-Origin", allowed_origin)
                self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Cache-Control", "no-store")

        def do_OPTIONS(self) -> None:  # noqa: N802
            if self.headers.get("Origin") != allowed_origin:
                self.send_error(403)
                return
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            if self.path != route or self.headers.get("Origin") != allowed_origin:
                self.send_error(404)
                return
            data = path.read_bytes()
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            threading.Thread(target=self.server.shutdown, daemon=True).start()

        def log_message(self, format: str, *values: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    host, port = server.server_address
    print(json.dumps({
        "url": f"http://{host}:{port}{route}",
        "filename": path.name,
        "content_type": content_type,
        "bytes": path.stat().st_size,
        "allowed_origin": allowed_origin,
        "stops_after": "first authorized GET",
    }, ensure_ascii=False), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
