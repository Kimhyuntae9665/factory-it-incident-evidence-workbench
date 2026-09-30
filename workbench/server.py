"""Loopback-only, bounded synthetic evidence API."""
import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .core import Store

MAX_BODY = 32768
MAX_TARGET = 8192
STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/index.html": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/styles.css": ("styles.css", "text/css; charset=utf-8")}


def make_server(store, port=19080, static_dir=None):
    static_dir = Path(static_dir or Path(__file__).resolve().parent.parent / "static")
    class Handler(BaseHTTPRequestHandler):
        server_version = "EvidenceWorkbench"
        sys_version = ""
        def log_message(self, format, *args):
            # No URLs, query strings, bodies, tokens, or authorization in access logs.
            pass

        def _send(self, status, value, content_type="application/json; charset=utf-8"):
            body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            if self.headers.get("Transfer-Encoding"):
                raise ValueError("Unsupported body transfer")
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) != 1 or not lengths[0].isdigit():
                raise ValueError("Content-Length required")
            length = int(lengths[0])
            if length > MAX_BODY:
                self._send(413, {"error": "Request body too large"})
                return None
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                raise ValueError("JSON body required")
            payload = self.rfile.read(length)
            if len(payload) != length:
                raise ValueError("Incomplete body")
            try:
                body = json.loads(payload)
            except (ValueError, UnicodeError):
                raise ValueError("Invalid JSON")
            if not isinstance(body, dict):
                raise ValueError("JSON object required")
            return body

        def _principal(self):
            authorization = self.headers.get("Authorization", "")
            if not authorization.startswith("Bearer ") or len(authorization) > 200:
                raise PermissionError("Authentication required")
            return store.principal(authorization[7:])

        def _query(self, raw):
            query = parse_qs(raw, keep_blank_values=True, max_num_fields=8)
            if any(len(values) != 1 for values in query.values()):
                raise ValueError("Duplicate query parameter")
            return {key: values[0] for key, values in query.items()}

        def _route(self, method):
            self.connection.settimeout(15)
            if len(self.path) > MAX_TARGET:
                self._send(414, {"error": "Request target too long"})
                return
            parsed = urlsplit(self.path)
            path = parsed.path
            if parsed.scheme or parsed.netloc or "%" in path or "\\" in path:
                raise KeyError("Not found")
            hosts=self.headers.get_all("Host",[])
            allowed_hosts={"127.0.0.1:"+str(self.server.server_port),"localhost:"+str(self.server.server_port)}
            if len(hosts)!=1 or hosts[0].lower() not in allowed_hosts:
                raise PermissionError("Host not allowed")
            origin = self.headers.get("Origin")
            if origin:
                allowed = {"http://127.0.0.1:" + str(self.server.server_port),
                           "http://localhost:" + str(self.server.server_port)}
                if origin not in allowed:
                    raise PermissionError("Cross-origin requests are not allowed")
            if method == "GET" and path in STATIC:
                filename, content_type = STATIC[path]
                try:
                    data = (static_dir / filename).read_bytes()
                except OSError:
                    raise KeyError("Not found")
                self._send(200, data, content_type)
                return
            if method == "GET" and path == "/api/health":
                self._send(200, {"ok": True, "synthetic": True,
                                 "authentication": "server-allowlisted demo profiles",
                                 "workflow": "enterprise-workflow reproduction test"})
                return
            if method == "GET" and path == "/api/profiles":
                self._send(200, {"profiles": store.profiles()})
                return
            if method == "POST" and path == "/api/session":
                body = self._body()
                if body is not None:
                    self._send(200, store.session(body.get("profile")))
                return
            if not path.startswith("/api/"):
                raise KeyError("Not found")
            principal = self._principal()
            query = self._query(parsed.query)
            if method == "GET" and path == "/api/incidents":
                self._send(200, {"incidents": store.incidents(principal)})
            elif method == "GET" and re.fullmatch(r"/api/incidents/[^/]+", path):
                self._send(200, store.incident(principal, path.rsplit("/", 1)[1]))
            elif method == "GET" and path == "/api/evidence":
                self._send(200, {"documents": store.evidence(principal, query.get("incident_id"), query.get("q", ""))})
            elif method == "GET" and re.fullmatch(r"/api/evidence/[^/]+", path):
                self._send(200, {"document": store.document(principal, path.rsplit("/", 1)[1])})
            elif method == "GET" and re.fullmatch(r"/api/citations/[^/]+", path):
                self._send(200, {"citation": store.citation(principal, path.rsplit("/", 1)[1], query.get("quote", ""))})
            elif method == "POST" and re.fullmatch(r"/api/incidents/[^/]+/analyze", path):
                body = self._body()
                if body is not None:
                    self._send(200, {"analysis": store.analyze(principal, path.split("/")[3], body.get("question", ""), body.get("mode", "baseline"))})
            elif method == "GET" and re.fullmatch(r"/api/analyses/[^/]+", path):
                self._send(200, {"analysis": store.analysis(principal, path.rsplit("/", 1)[1])})
            elif method == "POST" and re.fullmatch(r"/api/analyses/[^/]+/review", path):
                body = self._body()
                if body is not None:
                    self._send(200, store.review(principal, path.split("/")[3], body.get("decision"), body.get("comment", "")))
            elif method == "GET" and path == "/api/audit":
                self._send(200, {"events": store.audit(principal, query.get("incident_id"))})
            else:
                raise KeyError("Not found")

        def _handle(self, method):
            try:
                self._route(method)
            except PermissionError:
                self._send(403, {"error": "Access denied"})
            except KeyError:
                self._send(404, {"error": "Not found"})
            except (ValueError, TypeError):
                self._send(400, {"error": "Invalid request"})
            except (TimeoutError, ConnectionError, BrokenPipeError):
                self.close_connection = True
            except Exception:
                self._send(500, {"error": "Internal request failure"})

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

        def do_OPTIONS(self):
            self._send(405, {"error": "Method not allowed"})

    class LoopbackServer(ThreadingHTTPServer):
        def get_request(self):
            connection, address = super().get_request()
            connection.settimeout(15)
            return connection, address

    server = LoopbackServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def main():
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Synthetic incident evidence workbench (loopback only)")
    parser.add_argument("--corpus", default=str(root / "data" / "corpus.json"))
    parser.add_argument("--db", default=str(root / "data" / "workbench.sqlite3"))
    parser.add_argument("--port", type=int, default=19080)
    args = parser.parse_args()
    store = Store(args.corpus, args.db)
    server = make_server(store, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        store.close()


if __name__ == "__main__":
    main()
