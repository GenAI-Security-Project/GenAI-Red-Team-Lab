"""Behavioral tests for the lab's stated tenant-private model policy."""

import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.server import create_handler


class BoundaryTests(unittest.TestCase):
    def request(self, mode, path, token=None, model=None, method="GET", raw_body=None):
        server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(mode))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            headers = {"Content-Type": "application/json"}
            if token is not None:
                headers["Authorization"] = f"Bearer {token}"
            data = raw_body
            if model is not None:
                data = json.dumps({"model": model, "messages": []}).encode("utf-8")
            req = Request(
                f"http://127.0.0.1:{server.server_port}{path}",
                data=data,
                headers=headers,
                method=method,
            )
            try:
                with urlopen(req, timeout=3) as response:
                    return response.status, json.loads(response.read())
            except HTTPError as error:
                with error:
                    return error.code, json.loads(error.read())
        finally:
            server.shutdown()
            thread.join(timeout=3)
            server.server_close()

    def test_anonymous_listing_blocked_in_hardened_mode(self):
        status, _ = self.request("hardened", "/v1/models")
        self.assertEqual(status, 401)

    def test_invalid_token_cannot_list_models(self):
        status, _ = self.request("hardened", "/v1/models", token="wrong")
        self.assertEqual(status, 401)

    def test_model_listing_scoped_to_alpha(self):
        status, body = self.request("hardened", "/v1/models", token="lab-token-alpha")
        self.assertEqual(status, 200)
        self.assertEqual([model["id"] for model in body["data"]], ["alpha-private"])

    def test_model_listing_scoped_to_beta(self):
        status, body = self.request("hardened", "/v1/models", token="lab-token-beta")
        self.assertEqual(status, 200)
        self.assertEqual([model["id"] for model in body["data"]], ["beta-private"])

    def test_cross_tenant_invocation_blocked(self):
        status, _ = self.request(
            "hardened",
            "/v1/chat/completions",
            "lab-token-alpha",
            "beta-private",
            "POST",
        )
        self.assertEqual(status, 403)

    def test_reverse_cross_tenant_invocation_blocked(self):
        status, _ = self.request(
            "hardened",
            "/v1/chat/completions",
            "lab-token-beta",
            "alpha-private",
            "POST",
        )
        self.assertEqual(status, 403)

    def test_own_model_invocation_succeeds(self):
        for token, model in (
            ("lab-token-alpha", "alpha-private"),
            ("lab-token-beta", "beta-private"),
        ):
            with self.subTest(tenant=token):
                status, body = self.request(
                    "hardened", "/v1/chat/completions", token, model, "POST"
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["model"], model)

    def test_missing_token_cannot_invoke_model(self):
        status, _ = self.request(
            "hardened", "/v1/chat/completions", model="alpha-private", method="POST"
        )
        self.assertEqual(status, 401)

    def test_unknown_model_returns_not_found(self):
        status, _ = self.request(
            "hardened", "/v1/chat/completions", "lab-token-alpha", "missing", "POST"
        )
        self.assertEqual(status, 404)

    def test_malformed_json_returns_bad_request(self):
        status, _ = self.request(
            "hardened", "/v1/chat/completions", token="lab-token-alpha",
            method="POST", raw_body=b"{bad json",
        )
        self.assertEqual(status, 400)

    def test_vulnerable_mode_allows_anonymous_discovery(self):
        status, body = self.request("intentionally-vulnerable", "/v1/models")
        self.assertEqual(status, 200)
        self.assertEqual(
            {model["id"] for model in body["data"]},
            {"alpha-private", "beta-private"},
        )

    def test_vulnerable_mode_allows_cross_tenant_invocation(self):
        status, body = self.request(
            "intentionally-vulnerable",
            "/v1/chat/completions",
            "lab-token-alpha",
            "beta-private",
            "POST",
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["model"], "beta-private")

    def test_invalid_mode_rejected(self):
        with self.assertRaises(ValueError):
            create_handler("nonexistent")


if __name__ == "__main__":
    unittest.main()
