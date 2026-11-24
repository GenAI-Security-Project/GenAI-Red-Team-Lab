# RAG Local ChromaDB v1.5.9 Sandbox

## Overview

A reproduction target for CVE-2026-45829: in the ChromaDB Python FastAPI
server, a client-supplied embedding-function configuration is processed
before the authentication check runs. An unauthenticated request can point the
server at an attacker-controlled model with `trust_remote_code: true`, and the
model module executes.

This sandbox pins the vulnerable server (ChromaDB 1.5.9), enables token
authentication, and ships a benign payload model that writes a marker file
instead of doing anything harmful.

## What the sandbox shows

1. Token authentication is active. A control request without credentials gets
   `401`.
2. The same endpoint accepts an unauthenticated create-collection request when
   it carries an `embedding_function` configuration.
3. Chroma deserializes that configuration before calling the auth check, builds
   the embedding function, and transformers imports the model module from
   `auto_map`.
4. The module writes `/evidence/marker.json`. The request then fails, but the
   code already ran.

The finding is the execution order, not a missing authentication feature. The
authentication exists; it runs too late.

## Layout

- `models/benign_autoload/`: minimal `auto_map` model. The `modeling_*` module
  writes the marker at import time. No weights, no network, no shell.
- `exploit/attack.py`: control request, exploit request, marker check.
- `Makefile`: build, up, attack, stop.
- `Containerfile`: Python 3.11, ChromaDB 1.5.9, CPU torch,
  sentence-transformers.

## Running

```bash
make build
make up
make attack
make stop
```

With Docker instead of Podman:

```bash
make PODMAN=docker all
```

The container sets `CHROMA_SERVER_AUTHN_PROVIDER` to the token provider,
`CHROMA_SERVER_AUTHN_CREDENTIALS=test-token`, and mounts `./evidence` at
`/evidence`.

Expected output:

```text
[PASS] authentication is enabled (control request) | 403 ...
[PASS] unauthenticated request is rejected | 500 ...
[PASS] model module executed before authentication
marker: {"module": ".../modeling_benign.py", "pid": ..., "utc": "..."}
0 failure(s)
```

## Why the exploit request returns 500

The benign model has no tokenizer or weights. The embedding function is
constructed after the remote module executes and then fails to finish
loading, so the request errors before reaching the auth check. That failure
order is the evidence: the code ran while the request was still
unauthenticated. A real attacker would ship a model that loads cleanly; the
lab intentionally does not.

## Mitigations

- Do not accept client-supplied embedding-function configuration over an
  unauthenticated surface. Build embedding functions server-side.
- Keep `trust_remote_code` false and treat any model loading path that accepts
  it as code execution.
- Use the Rust server, which does not go through this code path, until a fixed
  Python build is available.
- Put the API behind an authenticating proxy and restrict network access.

## Scope

- The advisory describes `POST /api/v2/tenants/{tenant}/databases/{db}/collections`
  with a configuration blob. This sandbox uses only that path.
- This is not an "authentication disabled by default" lab. The auth provider is
  configured and enforced for requests that reach it.
- Version pinned to 1.5.9, which the advisory lists as still vulnerable.

## References

- HiddenLayer, CVE-2026-45829 (ChromaToast):
  https://hadrian.io/vulnerability-alerts/cve-2026-45829----chromadb-python-server-hands-you-rce-before-it-asks-who-you-are
- CSA research note:
  https://labs.cloudsecurityalliance.org/research/csa-research-note-chromadb-rce-ai-infrastructure-security-20/
- BleepingComputer coverage:
  https://www.bleepingcomputer.com/news/security/max-severity-flaw-in-chromadb-for-ai-apps-allows-server-hijacking/
