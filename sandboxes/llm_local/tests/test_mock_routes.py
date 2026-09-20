"""Route tests for the llm_local mock API.

These run with no Ollama backend up: GET /v1/models answers from the sandbox's own
configuration, and every auth path is decided before any backend call is made.
"""

import importlib
import os
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.mocks import openai as mock_openai


def build_client(module=mock_openai) -> TestClient:
    """A TestClient serving only the mock router, with no application around it."""
    app = FastAPI()
    app.include_router(module.router)
    return TestClient(app, raise_server_exceptions=False)


class ModelsEndpointTest(TestCase):
    """GET /v1/models — the liveness route clients call before their first request."""

    def test_returns_openai_model_list_shape(self):
        response = build_client().get(
            "/v1/models", headers={"Authorization": "Bearer sk-mock-key"}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["object"], "list")
        self.assertEqual(len(body["data"]), 1)
        entry = body["data"][0]
        self.assertEqual(entry["object"], "model")
        self.assertEqual(entry["owned_by"], "ollama")

    def test_lists_the_configured_model(self):
        with patch.dict(os.environ, {"OLLAMA_MODEL": "llama3.2:1b"}):
            response = build_client().get(
                "/v1/models", headers={"Authorization": "Bearer sk-mock-key"}
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"][0]["id"], "llama3.2:1b")

    def test_answers_without_a_backend(self):
        """The route must not consult Ollama: a sandbox still pulling a model is up."""
        with patch.object(
            mock_openai.client.chat.completions,
            "create",
            side_effect=AssertionError("the models route must not call the backend"),
        ):
            response = build_client().get(
                "/v1/models", headers={"Authorization": "Bearer sk-mock-key"}
            )
        self.assertEqual(response.status_code, 200)


class AuthTest(TestCase):
    """The four ways a request can present (or fail to present) the mock key."""

    def test_missing_header_gets_a_401_that_names_no_credential(self):
        """A red-teaming tool reads a named credential in an error body as a leak.

        The detail used to be "Missing Authorization header, expected: Bearer sk-mock-key".
        agent0 and tools like it flag that as secret leakage, which is a false positive
        against a sandbox whose key is public by design. The 401 still answers the question
        a client has, which is that the header is missing.
        """
        response = build_client().get("/v1/models")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Missing Authorization header")
        self.assertNotIn("sk-mock-key", response.text)

    def test_non_bearer_scheme_is_rejected(self):
        response = build_client().get(
            "/v1/models", headers={"Authorization": "Basic sk-mock-key"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid authentication scheme")

    def test_wrong_key_is_rejected(self):
        response = build_client().get(
            "/v1/models", headers={"Authorization": "Bearer sk-wrong-key"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid API key")

    def test_correct_key_is_accepted(self):
        response = build_client().get(
            "/v1/models", headers={"Authorization": "Bearer sk-mock-key"}
        )
        self.assertEqual(response.status_code, 200)


class ModuleImportTest(TestCase):
    """The module must import with no backend reachable and no API key set."""

    def test_imports_without_ollama(self):
        self.assertIsNotNone(importlib.reload(mock_openai).router)
