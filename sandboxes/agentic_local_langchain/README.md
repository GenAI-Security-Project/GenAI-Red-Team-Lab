# Vulnerable LangChain Sandbox (v0.1.24–v0.1.26)

A containerized sandbox environment demonstrating **critical Insecure Orchestration vulnerabilities** in LangChain-core. This sandbox simulates the real-world patch lifecycle across three versions, allowing students to exploit both CVE-2023-36258 and CVE-2026-34070, and discover the **Incomplete Patch flaw** where write-side `.save()` primitives remain exposed.

| Field | Value |
|-------|-------|
| **Target** | LangChain-core v0.1.24 – v0.1.26 |
| **CVSS v3.1** | **10.0 (Critical)** – AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H |
| **CWE Chain** | CWE-59 (Improper Link Resolution) → CWE-22 (Path Traversal) → CWE-94 (Code Injection) |
| **CVEs Bypassed** | CVE-2023-36258 + CVE-2026-34070 |
| **Root Cause** | Missing path canonicalization on file I/O operations |
| **Research Paper** | [JDP-2026-004](https://jdp-security.github.io/security-research-papers/2026-05-12-langchain-orchestration-poisoning-disclosure.html) |
| **Author** | Jeff Ponte (JDP Security) |

---

## Vulnerability Overview

### The Confused Deputy Problem

The LangChain-core framework acts as a **Confused Deputy** – a privileged component that executes file operations based on untrusted input. When an attacker-controlled LLM output (or simulated tool call) contains path traversal sequences like `../../`, the framework blindly follows them using its own elevated permissions.

### Three-Stage Patch Lifecycle

| Stage | Version | Behavior |
|-------|---------|----------|
| **0** | v0.1.24 | **Unhardened** – Both read and write primitives fully exposed |
| **1** | v0.1.25 | **Partial Hardened** – Read-side patched (PR #36471), but write-side `.save()` remains exposed |
| **2** | v0.1.26+ | **Fully Hardened** – Both read and write protected (PR #36585 applied) |

### The Incomplete Patch Flaw (JDP Security Core Discovery)

PR #36471 (Commit d41f3e2) added path traversal protection to the read function:

```python
if STAGE > 0 and (".." in target_path_str or not target_path.resolve().is_relative_to(SANDBOX_DIR)):
    return "[BLOCKED] Security Guardrail: Path traversal or unauthorized external read detected."
```

However, the write function was **completely overlooked**:

```python
# Stage 2 blocks writes; Stage 0 and 1 allow (incomplete patch!)
if STAGE == 2 and (".." in target_path_str or not target_path.resolve().is_relative_to(SANDBOX_DIR)):
    return "[BLOCKED] Security Guardrail: Sandbox jail restriction prevents arbitrary write."
```

**This means Stage 1 has read protection but NO write protection** – the exact incomplete patch flaw discovered by JDP Security. An attacker can still overwrite framework source code even after the read-side patch is applied.

---

## Quick Start

### Prerequisites

- Docker or Podman
- Python 3.10+
- Make

### Build and Run

```bash
cd sandboxes/agentic_local_langchain

# Build the container
make attack

# Verify the service is running
curl http://localhost:8000/health
```

### Expected Health Response

```json
{
  "status": "ok",
  "stage": 0,
  "sandbox_dir": "/app/sandbox_data"
}
```

---

## API Endpoints

### `GET /health`

Returns sandbox status and current stage.

### `POST /chat`

Main interaction endpoint. Accepts a JSON body with a `query` field containing simulated LLM tool calls.

**Read Request:**
```json
{
  "query": "Action: document_reader\nAction Input: {\"path\": \"../../../../../../etc/passwd\"}"
}
```

**Write Request:**
```json
{
  "query": "Action: file_writer\nAction Input: {\"path\": \"../../../../../../tmp/pwned.txt\", \"content\": \"EXPLOIT_SUCCESS\"}"
}
```

---

## Stage Switching

The sandbox uses the `LAB_STAGE` environment variable to control security posture:

```bash
# Stage 0: Unhardened (port 8000)
docker run -d --name langchain-sandbox -p 8000:8000 -e LAB_STAGE=0 langchain-sandbox-img

# Stage 1: Partial Hardened (port 8001)
docker run -d --name langchain-sandbox -p 8001:8000 -e LAB_STAGE=1 langchain-sandbox-img

# Stage 2: Fully Hardened (port 8002)
docker run -d --name langchain-sandbox -p 8002:8000 -e LAB_STAGE=2 langchain-sandbox-img
```

---

## Exploitation

The companion exploitation tools are located in:

```
exploitation/
└── langchain/
    ├── interactive_trainer.py      # Menu-driven CLI trainer
    └── verify_all_langchain.sh     # 3-stage automated verification
```

---

## Container Management

```bash
# Stop the container
make stop

# View logs
make logs

# Clean up everything
make clean
```

---

## Files

| File | Purpose |
|------|---------|
| `Containerfile` | Python 3.11-slim build with langchain-core dependencies |
| `Makefile` | Build/run/stop lifecycle management |
| `README.md` | This documentation |
| `app/server.py` | Vulnerable HTTP API server with stage-based logic |
| `app/data/` | Sandbox data directory for file operations |

---

## References

- [JDP-2026-004: Architectural Boundary Failures in LangChain-Core](https://jdp-security.github.io/security-research-papers/2026-05-12-langchain-orchestration-poisoning-disclosure.html)
- [CVE-2023-36258](https://nvd.nist.gov/vuln/detail/CVE-2023-36258) – Suffix validation bypass
- [CVE-2026-34070](https://nvd.nist.gov/vuln/detail/CVE-2026-34070) – Opt-in path traversal
- [PR #36471 (d41f3e2)](https://github.com/langchain-ai/langchain/commit/d41f3e2) – Read-side patch (INCOMPLETE)
- [PR #36585 (e7b9a2c)](https://github.com/langchain-ai/langchain/commit/e7b9a2c) – Write-side fix
- OWASP Top 10 for LLM Applications: [LLM06 – Insecure Orchestration](https://owasp.org/www-project-top-10-for-llm-applications/)

