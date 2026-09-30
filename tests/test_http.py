"""Loopback HTTP tests; all model behavior is mocked."""
import concurrent.futures
import http.client
import json
import threading
import unittest

from test_core import Fixture
from workbench.server import MAX_BODY, make_server


class HTTPTests(Fixture):
    def setUp(self):
        super().setUp()
        self.static = self.root / "static"
        self.static.mkdir()
        for name in ("index.html", "app.js", "styles.css"):
            (self.static / name).write_text("synthetic static " + name, encoding="utf-8")
        self.server = make_server(self.store, port=0, static_dir=self.static)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port
        self.tokens = {p: self.store.session(p)["token"] for p in ("A-it", "A-operator", "A-reviewer", "B-reviewer")}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        super().tearDown()

    def request(self, method, path, body=None, profile="A-it", extra=None, raw=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {}
        if profile:
            headers["Authorization"] = "Bearer " + self.tokens[profile]
        if body is not None:
            raw = json.dumps(body)
            headers["Content-Type"] = "application/json"
        if extra:
            headers.update(extra)
        connection.request(method, path, body=raw, headers=headers)
        response = connection.getresponse()
        payload = response.read()
        status, response_headers = response.status, dict(response.getheaders())
        connection.close()
        if response_headers.get("Content-Type", "").startswith("application/json"):
            payload = json.loads(payload)
        return status, payload, response_headers

    def test_host_allowlist_rejects_external_host(self):
        status,_,_=self.request("GET","/api/health",profile=None,extra={"Host":"attacker.invalid"})
        self.assertEqual(status,403)
        status,_,_=self.request("POST","/api/session",{"profile":"A-reviewer"},profile=None,extra={"Host":"attacker.invalid"})
        self.assertEqual(status,403)

    def test_loopback_health_and_static_exact_whitelist(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        status, body, headers = self.request("GET", "/api/health", profile=None)
        self.assertEqual(status, 200)
        self.assertTrue(body["synthetic"])
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        for path in ("/", "/index.html", "/app.js", "/styles.css"):
            self.assertEqual(self.request("GET", path, profile=None)[0], 200)
        for path in ("/docs/contract.md", "/../data/corpus.json", "/%2e%2e/data/corpus.json",
                     "/data/corpus.json", "/workbench/core.py", "/app.js/"):
            self.assertEqual(self.request("GET", path, profile=None)[0], 404)

    def test_sessions_and_no_header_identity_spoofing(self):
        status, body, _ = self.request("POST", "/api/session", {"profile": "A-operator"}, profile=None)
        self.assertEqual(status, 200)
        self.assertEqual(body["principal"]["role"], "operator")
        self.assertEqual(self.request("POST", "/api/session", {"profile": "superuser"}, profile=None)[0], 400)
        self.assertEqual(self.request("GET", "/api/incidents", profile=None,
                                      extra={"X-Site": "A", "X-Role": "reviewer"})[0], 403)
        self.assertEqual(self.request("GET", "/api/incidents", extra={"Authorization": "Bearer bad"})[0], 403)
        status, payload, _ = self.request("GET", "/api/incidents", profile="A-operator", extra={"X-Site": "B"})
        self.assertEqual(status, 200)
        self.assertTrue(all(i["site"] == "A" for i in payload["incidents"]))

    def test_http_acl_on_every_protected_surface(self):
        analysis = self.store.analyze(self.it, "a1", "")
        requests = [("GET", "/api/incidents/b1", None),
                    ("GET", "/api/evidence?incident_id=b1", None),
                    ("GET", "/api/evidence/b-private", None),
                    ("GET", "/api/citations/b-private?quote=secret", None),
                    ("POST", "/api/incidents/b1/analyze", {"mode": "baseline"}),
                    ("GET", "/api/audit?incident_id=b1", None)]
        for method, path, body in requests:
            with self.subTest(path=path):
                self.assertEqual(self.request(method, path, body)[0], 404)
        for profile in ("B-reviewer", "A-operator"):
            self.assertEqual(self.request("GET", "/api/analyses/" + analysis["id"], profile=profile)[0], 404)
        self.assertEqual(self.request("POST", "/api/analyses/" + analysis["id"] + "/review",
                                      {"decision": "approved"}, profile="B-reviewer")[0], 404)
        self.assertEqual(self.request("POST", "/api/analyses/" + analysis["id"] + "/review",
                                      {"decision": "approved"}, profile="A-it")[0], 403)
        status, payload, _ = self.request("GET", "/api/audit?incident_id=a1", profile="A-operator")
        self.assertEqual(status, 200)
        self.assertEqual(payload["events"], [])

    def test_revision_quote_validation_and_retrieval(self):
        for profile in ("A-it", "A-operator"):
            self.assertEqual(self.request("GET", "/api/evidence/restricted-old", profile=profile)[0], 404)
        self.assertEqual(self.request("GET", "/api/evidence/restricted-latest", profile="A-operator")[0], 404)
        self.assertEqual(self.request("GET", "/api/citations/a-log?quote=fabrication")[0], 400)
        status, payload, _ = self.request("GET", "/api/citations/a-log?quote=E101")
        self.assertEqual(status, 200)
        self.assertEqual(payload["citation"]["quote"], "E101")
        status, payload, _ = self.request("GET", "/api/evidence?incident_id=a1&q=E101", profile="A-operator")
        self.assertEqual(status, 200)
        self.assertNotIn("restricted-latest", {d["id"] for d in payload["documents"]})

    def test_bounded_json_and_cross_origin_rejected(self):
        self.assertEqual(self.request("POST", "/api/session", raw="{}", profile=None)[0], 400)
        self.assertEqual(self.request("POST", "/api/session", raw="{", profile=None,
                                      extra={"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.request("POST", "/api/session", raw="[]", profile=None,
                                      extra={"Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.request("POST", "/api/session", raw="x" * (MAX_BODY + 1), profile=None,
                                      extra={"Content-Type": "application/json"})[0], 413)
        self.assertEqual(self.request("GET", "/api/incidents", extra={"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.request("GET", "/api/evidence?incident_id=a1&incident_id=b1")[0], 400)

    def test_http_model_timeout_degraded_and_review_blocked(self):
        context, adapter = self.model_patch(error=TimeoutError("internal secret"))
        with context:
            status, body, _ = self.request("POST", "/api/incidents/a1/analyze", {"mode": "model", "question": "E101"})
        self.assertEqual(status, 200)
        analysis = body["analysis"]
        self.assertEqual(analysis["mode"], "degraded")
        self.assertFalse(analysis["gate"]["passed"])
        self.assertNotIn("internal secret", json.dumps(body))
        self.assertEqual(self.request("POST", "/api/analyses/" + analysis["id"] + "/review",
                                      {"decision": "approved"}, profile="A-reviewer")[0], 400)

    def test_concurrent_http_review_retries_idempotent(self):
        status, body, _ = self.request("POST", "/api/incidents/a1/analyze", {"mode": "baseline"})
        self.assertEqual(status, 200)
        analysis_id = body["analysis"]["id"]
        def submit(index):
            return self.request("POST", "/api/analyses/" + analysis_id + "/review",
                                {"decision": "approved", "comment": "review " + str(index)}, profile="A-reviewer")
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(submit, range(16)))
        self.assertEqual({result[0] for result in results}, {200})
        self.assertEqual(sum(not result[1]["duplicate"] for result in results), 1)
        self.assertEqual(len({result[1]["review"]["id"] for result in results}), 1)
        status, audit, _ = self.request("GET", "/api/audit?incident_id=a1", profile="A-reviewer")
        self.assertEqual(sum(event["action"] == "analysis_reviewed" for event in audit["events"]), 1)


if __name__ == "__main__":
    unittest.main()
