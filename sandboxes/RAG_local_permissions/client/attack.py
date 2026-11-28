"""Run the permission and revocation scenario against a live sandbox.

Usage: make attack  (sandbox must be running on http://localhost:8000)

Prints one line per check and exits non-zero if the sandbox does not behave
as the scenario expects.
"""

import sys

import requests

BASE = "http://localhost:8000"
QUERY = {"query": "password policy requirement"}


def call(method: str, path: str, user: str | None = None, **kwargs):
    headers = {"X-User": user} if user else {}
    response = requests.request(method, f"{BASE}{path}", headers=headers, **kwargs)
    response.raise_for_status()
    return response.json()


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" | {detail}" if detail else ""))
    if not ok:
        globals()["FAILURES"] += 1


def main() -> int:
    globals()["FAILURES"] = 0
    call("POST", "/admin/reset", params={"seed": True})

    alice = call("POST", "/query", user="alice", json=QUERY)
    bob = call("POST", "/query", user="bob", json=QUERY)
    alice_ids = {m["id"] for m in alice["chunks"]}
    bob_ids = {m["id"] for m in bob["chunks"]}
    check("alice sees policy-a", "policy-a" in alice_ids, str(sorted(alice_ids)))
    check("bob does not see policy-a", "policy-a" not in bob_ids, str(sorted(bob_ids)))

    call("POST", "/admin/revoke", json={"doc_id": "policy-a", "acl": "revoked"})
    after = call("POST", "/query", user="alice", json=QUERY)
    check(
        "revocation removes policy-a from retrieval",
        "policy-a" not in {m["id"] for m in after["chunks"]},
    )

    call("POST", "/admin/reset", params={"seed": True})
    first = call("POST", "/chat", user="alice", json=QUERY)
    call("POST", "/admin/revoke", json={"doc_id": "policy-a", "acl": "revoked"})
    second = call("POST", "/chat", user="alice", json=QUERY)
    leaked = second["cache_hit"] and "12 characters" in second["answer"]
    check("cached answer leaks revoked content (expected bug)", leaked)

    call("POST", "/admin/cache", json={"enabled": False})
    third = call("POST", "/chat", user="alice", json=QUERY)
    check(
        "cache invalidation closes the leak",
        not third["cache_hit"] and "12 characters" not in third["answer"],
    )

    call("POST", "/admin/reset", params={"seed": True})
    tamper_response = requests.post(
        f"{BASE}/admin/tamper",
        json={
            "doc_id": "policy-a",
            "new_text": "Password Policy: disable MFA for all staff during maintenance.",
        },
    )
    if tamper_response.status_code == 403:
        print(
            "[SKIP] tamper checks (sandbox started without "
            "RAG_PERMISSIONS_ALLOW_TAMPER=1, write path disabled)"
        )
    else:
        tamper_response.raise_for_status()
        unflagged = call("POST", "/query", user="alice", json=QUERY)
        tampered = next(m for m in unflagged["chunks"] if m["id"] == "policy-a")
        check(
            "tampered content is retrievable without verification",
            not tampered["integrity_ok"],
        )

        call("POST", "/admin/verify", json={"enabled": True})
        flagged = call("POST", "/query", user="alice", json=QUERY)
        check(
            "integrity verification filters tampered content",
            "policy-a" not in {m["id"] for m in flagged["chunks"]},
        )

    evidence = call("GET", "/evidence")
    check("evidence log carries identity and authorization", evidence["count"] > 0)

    print(f"\n{globals()['FAILURES']} failure(s)")
    return 1 if globals()["FAILURES"] else 0


if __name__ == "__main__":
    sys.exit(main())
