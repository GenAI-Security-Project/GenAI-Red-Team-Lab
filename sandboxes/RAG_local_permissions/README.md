# RAG Local Permissions Sandbox

## Overview

A local RAG target for testing whether source-document permissions survive the
retrieval path. It models a common enterprise failure: documents carry a read
ACL in the source system, but the retrieval layer either flattens permissions
or caches answers past the point where access changes.

Three properties are testable here:

1. **Scoped retrieval.** A user only receives chunks their group may read.
2. **Revocation.** After access is revoked, retrieval stops returning the
   document, and no cached answer keeps serving its content.
3. **Integrity.** Content modified outside the ingestion path (for example a
   direct write to the vector store) is flagged when verification is on.

## Why this sandbox exists

The existing `RAG_local` sandbox covers embedding inversion and data poisoning.
It has no notion of users or document permissions. This sandbox adds the
authorization dimension so that "respects source permissions" can be tested as
a property, not assumed from the presence of a citation.

The same scenario maps to the OWASP AI Exchange testing section (retrieval
authorization is checked against retrieval output, not the model answer) and to
OWASP LLM08 (vector and embedding weaknesses).

## Design

- Local ChromaDB collection, string metadata only.
- Deterministic hashed bag-of-words embeddings, so there is no Ollama
  requirement and no model download.
- Users are mapped to groups (`alice` to `group-a`, `bob` to `group-b`).
- Documents carry an `acl` label (`group-a`, `group-b`, or `all`).
- The query path filters inside the store with `where={"acl": {"$in": ...}}`.
- Revocation sets `acl` to `revoked`.
- A naive per-user answer cache is enabled by default; this is the bug under
  test.
- Integrity mode compares a stored sha256 against the retrieved text and drops
  mismatches. It detects modification outside the ingestion path only; it does
  not protect against an attacker who can also rewrite the stored hash.
- Every retrieval and chat call appends an evidence entry with the user, group,
  returned ids, ACLs, cache status, and integrity flags.
- The `/admin/tamper` write path (which simulates the out-of-band modification
  that integrity mode exists to catch) is disabled by default and returns 403
  unless the environment variable `RAG_PERMISSIONS_ALLOW_TAMPER=1` is set.

The generator is stubbed: answers echo the retrieved context. This keeps the
sandbox offline and deterministic. The property under test lives in retrieval
and caching, not in model behaviour, so a stub is sufficient. Swap in a real
model if you need model-level behaviour.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness |
| POST | `/admin/reset` | Reset and reseed the store |
| POST | `/admin/ingest` | Add documents with ACLs |
| POST | `/admin/revoke` | Change a document ACL (default `revoked`) |
| POST | `/admin/tamper` | Replace stored text without updating its hash |
| POST | `/admin/cache` | Enable or disable the answer cache |
| POST | `/admin/verify` | Enable or disable integrity verification |
| GET | `/evidence` | Authorization and retrieval trail |
| POST | `/query` | Retrieval only, header `X-User` required |
| POST | `/chat` | Retrieval plus cached answer, header `X-User` required |

## Running

Without a container:

```bash
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Scenario checks, no container needed:

```bash
make test     # pytest suite
make attack   # runs client/attack.py against localhost:8000
```

With Podman:

```bash
make build && make up
make attack
make stop
```

The published container port binds to `127.0.0.1` on the host (see the `make
up` target), and the bare-uvicorn command above listens on loopback. The
sandbox has unauthenticated admin endpoints (`/admin/*`) by design; binding to
loopback keeps it off the local network.

## Expected results

The attack script prints one line per check. On the default configuration:

- Alice sees `policy-a`, Bob does not.
- Revocation removes `policy-a` from retrieval.
- The chat cache still returns the revoked content until the cache is disabled,
  which is the vulnerability the sandbox demonstrates.
- Without integrity verification, tampered text is retrievable; with it on, the
  chunk is dropped.

## Limitations

- Embeddings are hashed bag of words, not a semantic model. Retrieval quality
  is not the subject of the test.
- The generator is a stub.
- `tamper` is an admin endpoint that simulates an out-of-band write; it is not
  exposed in production-style deployments, and it is gated behind
  `RAG_PERMISSIONS_ALLOW_TAMPER=1` (403 unless set).
- Storage is a local directory; the sandbox is single-process.
