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
   `401`/`403`.
2. The same endpoint processes an unauthenticated create-collection request
   when it carries an `embedding_function` configuration.
3. With a public safetensors embedding model
   (`sentence-transformers/all-MiniLM-L6-v2`), the server downloads and loads
   the client-chosen model before the request is rejected by authentication.
   The Hugging Face cache gains the model directory during the request.
4. With a local `auto_map` model, transformers imports the model module, which
   writes `/evidence/marker.json`, and only afterwards does the request fail.

The finding is the execution order, not a missing authentication feature. The
authentication exists; it runs too late.

## RAG-specific reading

The controlled object is the embedding function of the vector store, which
decides how every chunk is vectorized and therefore what retrieval returns.
An unauthenticated caller can pick that function and its model. In a RAG
pipeline this is a retrieval-layer attack surface, not just a generic server
bug: the same configuration also controls model downloads and resource use
before any authorization decision.

## Why a safetensors model cannot be the RCE proof

Safetensors files contain no executable code, and models from established
publishers do not ship `auto_map` code paths. A safetensors model therefore
proves pre-auth model selection, download, and load, but not code execution.
The code-execution proof needs a module that transformers imports under
`trust_remote_code`, which is why the sandbox also ships a minimal local
`auto_map` model that only writes a marker.

## Layout

- `models/benign_autoload/`: minimal `auto_map` model. The `modeling_*` module
  writes the marker at import time. No weights, no network, no shell.
- Safe HF model case: downloads `sentence-transformers/all-MiniLM-L6-v2`
  (safetensors, public publisher) at request time to show pre-auth model
  selection. Requires network access from the container.
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

The published port binds to `127.0.0.1` on the host (see the `make up`
target), so the vulnerable server and its unauthenticated exploit path are
reachable only from the local machine.

### Safe HF model case and offline runs

The safe HF case downloads `sentence-transformers/all-MiniLM-L6-v2` from
huggingface.co at request time, so it needs outbound network access from the
container. To run offline, pre-seed a Hugging Face cache directory while
online and mount it into the container:

```bash
make up HF_CACHE=$PWD/hf-cache
```

(`HF_CACHE` adds `-v <dir>:/root/.cache/huggingface/hub`.) On an
already-seeded cache the fresh-download proof cannot repeat, so the attack
script prints a `[SKIP]` line for that check; the pre-auth 401/403 check for
the safe model still runs. Fully offline with no seeded cache, the download
fails before the auth check and the two safe-case checks do not apply.

`make attack` is single-shot: the marker is written at module import time, so
re-running the attack against the same container reports the marker check as
`FAIL` because Python has already imported the module. `make down && make up`
for a fresh run.

The container sets `CHROMA_SERVER_AUTHN_PROVIDER` to the token provider,
`CHROMA_SERVER_AUTHN_CREDENTIALS=test-token`, and mounts `./evidence` at
`/evidence`.

Expected output:

```text
[PASS] authentication is enabled (control request) | 403 ...
[PASS] safe HF model request is rejected by authentication | 403 ...
[PASS] server loaded the client-chosen HF model before auth | models--sentence-transformers--all-MiniLM-L6-v2
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
- `trust_remote_code` is set only inside the exploit request body
  (`exploit/attack.py`, `kwargs.trust_remote_code: true`). No environment
  variable, image default, or server configuration enables it. The marker
  module (`models/benign_autoload`) is reached only through that request:
  transformers imports a local `auto_map` module solely when
  `trust_remote_code=True` is passed for that specific load, so no other
  configuration in this sandbox writes the marker.

## References

- GHSA-f4j7-r4q5-qw2c (primary advisory, CVE-2026-45829):
  https://github.com/advisories/GHSA-f4j7-r4q5-qw2c
- NVD record, CVE-2026-45829:
  https://nvd.nist.gov/vuln/detail/CVE-2026-45829
- HiddenLayer, CVE-2026-45829 (ChromaToast):
  https://hadrian.io/vulnerability-alerts/cve-2026-45829----chromadb-python-server-hands-you-rce-before-it-asks-who-you-are
- CSA research note:
  https://labs.cloudsecurityalliance.org/research/csa-research-note-chromadb-rce-ai-infrastructure-security-20/
- BleepingComputer coverage:
  https://www.bleepingcomputer.com/news/security/max-severity-flaw-in-chromadb-for-ai-apps-allows-server-hijacking/
