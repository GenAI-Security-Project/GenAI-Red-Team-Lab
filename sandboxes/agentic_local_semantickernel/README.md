# Vulnerable Semantic Kernel Sandbox (v1.48.0)

Demonstrates **CVE-2026-25592** bypass, the "Shell Blinding" evasion paradox, and **AutoInvokeKernelFunctions** abuse.

| Field | Value |
|-------|-------|
| CVSS | 10.0 (AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H) |
| CWE Chain | CWE-1039 → CWE-22 → CWE-94 |
| Root Cause | Type confusion: string filters, object sinks |

## Quick Start
```bash
make attack
curl http://localhost:8000/api/health
```

## API
- `POST /api/invoke` – Direct plugin execution (for filter bypass tests)
- `POST /api/autoinvoke` – Simulated LLM autonomous execution (contains fa2d52f6 shell blinding output filter)

## Exploitation
- `exploitation/semantickernel_type_confusion/` – 6 bypass vectors
- `exploitation/semantickernel_autoinvoke/` – AutoInvoke escalation with OOB verification

## References
- JDP-2026-001: Microsoft Semantic Kernel Type Confusion
- CVE-2026-25592
