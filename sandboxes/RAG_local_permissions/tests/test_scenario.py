"""Scenario tests for the RAG permissions sandbox.

These run without a container and without any model download. They encode the
properties the sandbox exists to test:

1. Retrieval is scoped per user group.
2. Revocation removes the document from retrieval.
3. A naive answer cache can keep returning revoked content (the bug).
4. Cache invalidation closes the leak.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PASSWORD_QUERY = "password policy requirement"


@pytest.fixture(autouse=True)
def fresh_state():
    client.post("/admin/reset", params={"seed": True})
    yield


def test_differential_retrieval():
    alice = client.post(
        "/query", json={"query": PASSWORD_QUERY}, headers={"X-User": "alice"}
    ).json()
    bob = client.post(
        "/query", json={"query": PASSWORD_QUERY}, headers={"X-User": "bob"}
    ).json()

    alice_ids = {m["id"] for m in alice["chunks"]}
    bob_ids = {m["id"] for m in bob["chunks"]}
    assert "policy-a" in alice_ids
    assert "policy-a" not in bob_ids
    assert alice["group"] == "group-a"
    assert bob["group"] == "group-b"


def test_revocation_removes_document_from_retrieval():
    before = client.post(
        "/query", json={"query": PASSWORD_QUERY}, headers={"X-User": "alice"}
    ).json()
    assert "policy-a" in {m["id"] for m in before["chunks"]}

    client.post("/admin/revoke", json={"doc_id": "policy-a", "acl": "revoked"})

    after = client.post(
        "/query", json={"query": PASSWORD_QUERY}, headers={"X-User": "alice"}
    ).json()
    assert "policy-a" not in {m["id"] for m in after["chunks"]}


def test_cached_answer_survives_revocation():
    first = client.post(
        "/chat", json={"query": PASSWORD_QUERY}, headers={"X-User": "alice"}
    ).json()
    assert first["cache_hit"] is False
    assert "12 characters" in first["answer"]

    client.post("/admin/revoke", json={"doc_id": "policy-a", "acl": "revoked"})

    second = client.post(
        "/chat", json={"query": PASSWORD_QUERY}, headers={"X-User": "alice"}
    ).json()
    assert second["cache_hit"] is True
    assert "12 characters" in second["answer"], "vulnerable behaviour under test"


def test_cache_invalidation_is_the_fix():
    client.post("/chat", json={"query": PASSWORD_QUERY}, headers={"X-User": "alice"})
    client.post("/admin/revoke", json={"doc_id": "policy-a", "acl": "revoked"})
    client.post("/admin/cache", json={"enabled": False})

    after = client.post(
        "/chat", json={"query": PASSWORD_QUERY}, headers={"X-User": "alice"}
    ).json()
    assert after["cache_hit"] is False
    assert "12 characters" not in after["answer"]
