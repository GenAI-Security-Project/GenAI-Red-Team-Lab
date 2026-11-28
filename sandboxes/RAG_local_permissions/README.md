# RAG Local Permissions Sandbox

## Overview

A local RAG target for testing whether source-document permissions survive the
retrieval path. It models a common enterprise failure: documents carry a read
ACL in the source system, but the retrieval layer either flattens permissions
or caches answers past the point where access changes.

Two properties are testable here:

1. **Scoped retrieval.** A user only receives chunks their group may read.
2. **Revocation.** After access is revoked, retrieval stops returning the
   document, and no cached answer keeps serving its content.

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

The generator is stubbed: answers echo the retrieved context. This keeps the
sandbox offline and deterministic. The property under test lives in retrieval
and caching, not in model behaviour, so a stub is sufficient. Swap in a real
model if you need model-level behaviour.

Integrity verification (stored-hash vs retrieved-text check) and an evidence
trail are planned as a follow-up PR; this PR keeps the core authorization
scenario reviewable on its own.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness |
| POST | `/admin/reset` | Reset and reseed the store |
| POST | `/admin/ingest` | Add documents with ACLs |
| POST | `/admin/revoke` | Change a document ACL (default `revoked`) |
| POST | `/admin/cache` | Enable or disable the answer cache |
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

## Limitations

- Embeddings are hashed bag of words, not a semantic model. Retrieval quality
  is not the subject of the test.
- The generator is a stub.
- Storage is a local directory; the sandbox is single-process.
