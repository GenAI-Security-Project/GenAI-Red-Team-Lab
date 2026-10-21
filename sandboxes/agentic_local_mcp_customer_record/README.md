# Agentic Local MCP Customer Record Sandbox

This local-only sandbox demonstrates an indirect prompt injection that reaches a destructive MCP tool. A refund-desk agent reads attacker-controlled text from a customer record and may issue:

```text
delete_customer_record(customer_id="ALL", confirm_bulk_delete=true)
```

All records are synthetic and all actions remain inside disposable Podman containers. The success oracle reads the MCP audit log rather than trusting the model's final answer.

## Architecture

```mermaid
graph LR
    Operator --> Agent[OpenAI-compatible agent API]
    Agent --> Ollama[Local Ollama model]
    Agent -->|MCP over SSE| Records[Customer-record tools]
    Attacker[Injected return_reason] -.-> Records
    Records -->|Untrusted tool result| Agent
    Agent -->|Potential bulk delete| Records
```

The baseline intentionally combines an over-capable delete tool with untrusted record text. Four independent profiles demonstrate different controls:

| Profile | Control |
|---|---|
| `strip_control_tokens` | Removes known chat-template and tool delimiters from data fields |
| `least_privilege` | Exposes a single-record delete surface with no bulk parameter |
| `scoped_erasure` | Authorizes deletion only from a trusted per-record erasure flag |
| `bulk_approval` | Requires a human-held token for bulk or irreversible deletion |

`strip_control_tokens` is input hardening, not an authorization boundary. The structural controls remain effective even if the model follows an injection.

## Run

Prerequisites: Linux or WSL2, Podman, Ollama, `uv`, Make, and the local `gpt-oss:20b` model.

```bash
make ollama-pull
make test-unit
make build
make up
make test
make attack
make stop
```

`make attack` runs the companion module in [`../../exploitation/agentic_bulk_delete`](../../exploitation/agentic_bulk_delete/README.md). `make replay` demonstrates the controls without a model or container.

The API binds to `localhost:8011` by default; the MCP service is reachable only on the private Podman network. Override `HOST_PORT` if needed. Do not expose this deliberately vulnerable sandbox to untrusted networks.

On a rootless Linux host without an active systemd user session, pass Podman's cgroup manager explicitly:

```bash
make PODMAN="podman --cgroup-manager=cgroupfs" build up test
PODMAN="podman --cgroup-manager=cgroupfs" make attack
```

## Security mappings

- OWASP LLM01: Prompt Injection
- OWASP LLM06: Excessive Agency
- OWASP Agentic Top 10 ASI01: Agent Goal Hijack
- OWASP Agentic Top 10 ASI02: Tool Misuse and Exploitation
- MITRE ATLAS AML.T0051.001: LLM Prompt Injection — Indirect
