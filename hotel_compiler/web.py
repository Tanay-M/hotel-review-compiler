"""Local single-review and CSV dashboard adapter for the shared compiler.

Only the packaged demo assets are served. Analysis uses the same public
function as the CLI. One batch is retained in memory; nothing is auto-saved.
"""

import argparse
import csv
from io import StringIO
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
import re
import socket
from urllib.parse import parse_qs, unquote, urlsplit

from .pipeline import MAX_REVIEW_LENGTH, analyze_review
from .sentiwordnet import ResourceError, load_synsets
from .vocabulary import load_vocabulary
from .csv_input import CSVLimits
from .exports import batch_csv_bytes
from .paper_tables import paper_archive
from .web_batch import BatchBusyError, BatchStore


MAX_BODY_BYTES = 65_536
_ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/dashboard.js": ("dashboard.js", "text/javascript; charset=utf-8"),
    "/demo.csv": ("demo.csv", "text/csv; charset=utf-8"),
    "/reviews_100.csv": ("reviews_100.csv", "text/csv; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
}
_EXAMPLES = [
    {"label": "Mixed feedback", "text": "The room was not clean, but the staff were very helpful."},
    {"label": "Negation", "text": "The room wasn’t clean."},
    {"label": "Intensifier", "text": "The staff were extremely helpful."},
    {"label": "Room service", "text": "Room service was slow."},
    {"label": "Neutral", "text": "The service was average."},
    {"label": "Partial analysis", "text": "The room was odd but the staff were helpful."},
    {"label": "Shared aspect", "text": "The room was clean and quiet."},
]


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "HotelCompilerDemo/0.1"
    sys_version = ""

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(10)

    def _send(self, status: int, body: bytes, content_type: str, filename: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, value: dict) -> None:
        self._send(status, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _local_request(self) -> bool:
        port = self.server.server_port
        if self.headers.get("Host") not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "Use the local URL printed in the terminal."})
            return False
        return True

    def do_GET(self) -> None:
        if not self._local_request():
            return
        path = urlsplit(self.path).path
        if path in _ASSETS:
            name, content_type = _ASSETS[path]
            payload = files("hotel_compiler").joinpath("web_assets", name).read_bytes()
            self._send(HTTPStatus.OK, payload, content_type)
        elif path == "/api/config":
            vocabulary = load_vocabulary()
            self._json(HTTPStatus.OK, {
                "categories": vocabulary["categories"],
                "aspects": vocabulary["aspects"],
                "opinions": vocabulary["opinions"],
                "opinion_aliases": vocabulary.get("opinion_aliases", {}),
                "auxiliaries": vocabulary.get("auxiliaries", []),
                "predicate_adverbs": vocabulary.get("predicate_adverbs", []),
                "emphasis_phrases": vocabulary.get("emphasis_phrases", []),
                "negations": vocabulary["negations"],
                "intensifiers": vocabulary["intensifiers"],
                "connectors": vocabulary["connectors"],
                "max_review_length": MAX_REVIEW_LENGTH,
                "examples": _EXAMPLES,
            })
        elif path == "/api/health":
            self._json(HTTPStatus.OK, {"status": "ok"})
        elif path == "/api/demo.csv":
            try:
                query = parse_qs(urlsplit(self.path).query)
                size = int(query.get("rows", ["12"])[0])
                if size not in {12, 100, 500}:
                    raise ValueError
            except ValueError:
                self._json(HTTPStatus.BAD_REQUEST, {"error": "Choose 12, 100, or 500 demo reviews."})
                return
            source = files("hotel_compiler").joinpath("web_assets/demo.csv").read_text(encoding="utf-8")
            if size == 12:
                payload = source.encode("utf-8-sig")
            else:
                reviews = [row["review_text"] for row in csv.DictReader(StringIO(source))]
                target = StringIO(newline="")
                writer = csv.writer(target)
                writer.writerow(["review_id", "review_text"])
                writer.writerows([f"DEMO-{index + 1:04d}", reviews[index % len(reviews)]] for index in range(size))
                payload = target.getvalue().encode("utf-8-sig")
            self._send(HTTPStatus.OK, payload, "text/csv; charset=utf-8", f"synthetic-{size}.csv")
        elif path.startswith("/api/batches/"):
            match = re.fullmatch(r"/api/batches/([a-zA-Z0-9-]+)(?:/(reviews/[0-9]+|download/(?:reviews|aspects|paper)))?", path)
            if not match:
                self._json(HTTPStatus.NOT_FOUND, {"error": "Unknown batch route."})
                return
            try:
                session = self.server.batch_store.get(match[1])
            except KeyError as error:
                self._json(HTTPStatus.NOT_FOUND, {"error": error.args[0]})
                return
            action = match[2]
            if action is None:
                self._json(HTTPStatus.OK, session.overview())
            elif action.startswith("reviews/"):
                ordinal = int(action.split("/")[1])
                if not 1 <= ordinal <= len(session.batch.rows):
                    self._json(HTTPStatus.NOT_FOUND, {"error": "Unknown review row."})
                else:
                    self._json(HTTPStatus.OK, session.batch.rows[ordinal - 1].to_dict(include_trace=True))
            elif action == "download/paper":
                self._send(HTTPStatus.OK, paper_archive(session.batch, session.report), "application/zip", "report-tables.zip")
            else:
                kind = action.split("/")[1]
                self._send(HTTPStatus.OK, batch_csv_bytes(session.batch, kind), "text/csv; charset=utf-8", f"{kind}.csv")
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "This route is not part of the demo."})

    def do_POST(self) -> None:
        if not self._local_request():
            return
        parsed = urlsplit(self.path)
        if parsed.path not in {"/api/analyze", "/api/batches"}:
            self._json(HTTPStatus.NOT_FOUND, {"error": "This route is not part of the demo."})
            return
        origin = self.headers.get("Origin")
        port = self.server.server_port
        if origin and origin not in {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}:
            self._json(HTTPStatus.FORBIDDEN, {"error": "Open the demo from its own local URL."})
            return
        is_batch = parsed.path == "/api/batches"
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        allowed = {"text/csv", "application/octet-stream"} if is_batch else {"application/json"}
        if content_type not in allowed:
            self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "Send a CSV file body." if is_batch else "Send an application/json request."})
            return
        if self.headers.get("Content-Length") is None:
            self._json(HTTPStatus.LENGTH_REQUIRED, {"error": "A Content-Length header is required."})
            return
        try:
            length = int(self.headers["Content-Length"])
            if length < 0:
                raise ValueError
        except ValueError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "Invalid request length."})
            return
        if length > (CSVLimits().max_file_bytes if is_batch else MAX_BODY_BYTES):
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "Request body is too large."})
            return
        try:
            payload = self.rfile.read(length)
            if len(payload) != length:
                raise ValueError("Incomplete request body.")
            if is_batch:
                query = parse_qs(parsed.query, keep_blank_values=True)
                if any(len(values) != 1 for values in query.values()) or set(query) - {"text_column", "id_column"}:
                    raise ValueError("Select one review-text and one ID column.")
                filename = unquote(self.headers.get("X-File-Name", "upload.csv")).replace("\\", "/").split("/")[-1][:128] or "upload.csv"
                session = self.server.batch_store.submit(payload, source_name=filename,
                    text_column=query.get("text_column", ["review_text"])[0], id_column=query.get("id_column", ["review_id"])[0])
                self._json(HTTPStatus.OK, session.overview())
                return
            body = json.loads(payload.decode("utf-8"))
            if not isinstance(body, dict):
                raise ValueError("Send a JSON object containing review text.")
            result = analyze_review(body.get("text"), body.get("review_id"))
        except (UnicodeError, ValueError, TypeError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        except (TimeoutError, socket.timeout):
            self._json(HTTPStatus.REQUEST_TIMEOUT, {"error": "The request took too long to arrive."})
            return
        except ResourceError as error:
            self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(error)})
            return
        except BatchBusyError as error:
            self._json(HTTPStatus.CONFLICT, {"error": str(error)})
            return
        # Unsupported and partial language are valid analysis results, not HTTP
        # transport errors. Their status and diagnostics remain in the payload.
        self._json(HTTPStatus.OK, result.to_dict(include_trace=True))

    def do_DELETE(self) -> None:
        if not self._local_request():
            return
        port = self.server.server_port
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}:
            self._json(HTTPStatus.FORBIDDEN, {"error": "Open the demo from its own local URL."})
            return
        match = re.fullmatch(r"/api/batches/([a-zA-Z0-9-]+)", urlsplit(self.path).path)
        if not match:
            self._json(HTTPStatus.NOT_FOUND, {"error": "Unknown batch route."})
            return
        try:
            self.server.batch_store.clear(match[1])
        except KeyError as error:
            self._json(HTTPStatus.NOT_FOUND, {"error": error.args[0]})
        else:
            self._json(HTTPStatus.OK, {"status": "cleared"})


def create_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("The demo server supports local loopback addresses only.")
    if not 0 <= port <= 65_535:
        raise ValueError("Port must be between 0 and 65535.")
    # Validate resources before reporting that the server is ready.
    load_synsets()
    server = ThreadingHTTPServer((host, port), DemoHandler)
    server.batch_store = BatchStore()
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start the local Hotel Review Compiler web demo.")
    parser.add_argument("--port", type=int, default=8000, help="Local port (default: 8000).")
    args = parser.parse_args(argv)
    try:
        server = create_server(port=args.port)
    except (OSError, ValueError, ResourceError) as error:
        print(f"Could not start the web demo: {error}")
        return 2
    print(f"Hotel Review Compiler demo: http://127.0.0.1:{server.server_port}", flush=True)
    print("Open this URL in your browser. Press Ctrl+C in this terminal to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWeb demo stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

