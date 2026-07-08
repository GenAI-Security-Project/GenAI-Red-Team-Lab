# Tutorial: Semantic Kernel Orchestration Security Testing

**Author:** Jeff Ponte (JDP Security Research)

**Target:** Microsoft Semantic Kernel v1.47.0 – v1.48.0, Agent Framework 1.0

**Classification:** CVSS 10.0 (Critical) — AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H

**Reference:** [JDP-2026-001 White Paper](https://jdp-security.github.io/security-research-papers/2026-04-28-semantic-kernel-disclosure.html)

## Overview

This lab demonstrates two distinct vulnerability classes within AI orchestration frameworks:

1. **CVE-2026-25592 Remediation Evasion (Type Confusion):** 6 encoding and type-coercion vectors that bypass Microsoft's official path traversal filter.

2. **CWE-1039 AutoInvoke Abuse (Insecure Automated Optimizations):** Autonomous privilege escalation via `ToolCallBehavior.AutoInvokeKernelFunctions`.

3. **Defensive Hardening:** Validating a centralized `IFunctionInvocationFilter` with recursive canonicalization.

The lab uses a **double-pass architecture** — first running unhardened (all attacks succeed), then hardened (some blocked, some bypassed — proving the thesis).

## Critical Architectural Findings (JDP-2026-001)

### 1. The AllowedDirectories "Opt-In" Sandbox Paradox (PR #13683)

Microsoft addressed directory containment via `AllowedDirectories`, but categorized it as a **Breaking Change**, rendering it **strictly opt-in**. Default deployments remain unanchored and fully traversable.

### 2. "Shell Blinding" Output Redaction Failure (Commit fa2d52f6)

Microsoft masked terminal outputs of file write calls. This is a **purely cosmetic fix**. The execution sink remains fully vulnerable; attackers verify Blind RCE **out-of-band** (OOB) via filesystem inspection.

### 3. Supply Chain "SCA Blindness" Risks

Standard Software Composition Analysis (SCA) scanners (Trivy, Snyk, Dependabot) rely on CVE records. Microsoft classified the type confusion bypasses as **"Developer Error"** rather than issuing a subsequent CVE. Your scanners will register SK v1.48.0 as **completely secure**, leaving this CVSS 10.0 vector hidden during audits.

## The 6 Type Confusion Bypass Vectors

| Vector | Technique | Why It Bypasses Microsoft's Filter | 
 | ----- | ----- | ----- | 
| 1 | JSON Array `["..","..","config.txt"]` | `arg is string` evaluates to `false` for `JsonElement` | 
| 2 | Object Reflection `{"path":"../../config.txt"}` | `arg is string` skips objects; sink uses reflection | 
| 3 | Base64 Encoding `"Li4vLi4vY29uZmlnLnR4dA=="` | No `".."` or `"/"` in encoded string | 
| 4 | URL Encoding `"..%2f..%2fconfig.txt"` | No literal `"/"` — `%2f` decoded at sink | 
| 5 | Unicode Homoglyph `"..⁄..⁄config.txt"` | `U+2044` not recognized as `"/"` by filter | 
| 6 | Hybrid (Base64 inside JSON Array) | Nested encoding exhausts non-recursive validation | 

## Setup

```
git clone https://github.com/GenAI-Security-Project/GenAI-Red-Team-Lab.git
cd GenAI-Red-Team-Lab
git checkout semantic-kernel-orchestration-vulns
```

Ensure dependencies are installed:

* `podman` or `docker`
* `.NET SDK 8.0` container images (pulled automatically)
* `curl`, `jq`, `python3`

## Exercise 1: Run the Full Double-Pass Audit

This is the primary entry point. It executes all 10 attack scenarios twice:

```
cd exploitation/semantickernel
chmod +x verify_all.sh
./verify_all.sh
```

### What happens:

**PASS 1 (Unhardened):**

* `LAB_HARDENED` is NOT set
* `PathSanitizationFilter` is NOT registered
* All 6 type confusion vectors → **SUCCEED**
* All 4 AutoInvoke scenarios → **SUCCEED** (Shell Blinding bypassed OOB)
* Payloads verified via container exec commands

**PASS 2 (Hardened):**

* `LAB_HARDENED=true` is set
* `PathSanitizationFilter` IS active
* Vectors 1, 2, 4, 5 → **BLOCKED**
* Vectors 3, 6 → **BYPASS** (Base64 has no `".."` in encoded form)
* AutoInvoke 1-4 → **BLOCKED**

### Expected output — the Teaching Moment box:

```
  ┌──────────────────────────────────────────────────────────┐
  │  [❌] SECURITY FAILURE (INTENTIONAL TEACHING MOMENT)     │
  │  Payload bypassed the hardening filters!                 │
  │  The PathSanitizationFilter did NOT block the attack.    │
  │                                                          │
  │  🔬 WHY THIS IS EXPECTED (TOCTOU):                       │
  │  The filter checks the argument BEFORE decoding.         │
  │  Base64-encoded paths contain no ".." or "/" characters. │
  │  The plugin decodes them AFTER the filter check.         │
  │                                                          │
  │  This proves the JDP-2026-001 thesis:                    │
  │  Filter-based security is WHACK-A-MOLE.                  │
  │  Even an improved ToString() filter is not enough.       │
  │  Only ARCHITECTURAL changes (SafeRoot, type-safe sinks,  │
  │  compute isolation) can fully resolve this vulnerability.│
  └──────────────────────────────────────────────────────────┘
```

## Exercise 2: Verify OOB Payload Landing Manually

After PASS 1 completes, confirm the Shell Blinding bypass by reading the container filesystem directly. Use the command matching your container system:

**For Podman:**

```
podman exec sk-vulnerable cat /config.txt
```

**For Docker:**

```
docker exec sk-vulnerable cat /config.txt
```

Expected Output:

```
BYPASS1_SUCCESS
BYPASS2_SUCCESS
...
AUTOINVOKE4_OOB_LANDED
```

This proves that Microsoft's commit `fa2d52f6` (output masking) is cosmetic. The file write executes; the masking only hides the path from the LLM context.

## Exercise 3: Run Individual Components

If you want to debug or inspect specific components outside of the main automation script, navigate to the specific exploit folders and use their local Makefiles:

### Type Confusion Tests Only:

```
cd exploitation/semantickernel/semantickernel_type_confusion

# Execute all 6 type confusion vectors
make attack

# Test ONLY the Base64 bypass (Vector 3)
make vector-3
```

### AutoInvoke Tests Only:

```
cd exploitation/semantickernel/semantickernel_autoinvoke

# Execute all 4 AutoInvoke scenarios
make attack

# Run ONLY Scenario 2 (Context Manipulation)
make scenario-2
```

## The Mitigation Paradox: Band-Aids vs. Architectural Cures

> ⚠️ **CRITICAL ARCHITECTURAL NOTE** > An `IFunctionInvocationFilter` is an **operational workaround**, not a structural fix. It acts as a defensive firewall on top of a fundamentally fragile design.

### Why middleware filters cannot fully solve Insecure Orchestration (OWASP LLM06):

**1. Shared Execution Context (The Process-Space Trap)**
The filter runs in the same memory space, OS process, and privilege context as the vulnerable plugins. A bypass via encoding, type confusion, or nested serialization still executes the payload natively.

**2. The Determinism Deficit**
Filters apply deterministic rules to non-deterministic pipelines. As long as an LLM's raw output dynamically selects and populates system-level parameters (`File.WriteAllText`, `Process.Start`), defenders play infinite catch-up against prompt injection variance.

**3. TOCTOU (Time-of-Check vs Time-of-Use)**
The filter evaluates arguments BEFORE decoding. The plugin decodes arguments AFTER the filter. Every encoding scheme creates a new bypass opportunity. This is the Whack-a-Mole problem.

### What a Real Fix Requires:

| Requirement | Current State | Target State | 
 | ----- | ----- | ----- | 
| Path Anchoring | `AllowedDirectories` is OPT-IN | Mandatory `SafeRoot` enforcement | 
| Type-Safe Sinks | `object path` accepts any type | Strict `string` type enforcement | 
| Recursive Canonicalization | Decoding happens inside plugins | Full decoding BEFORE filter evaluation | 
| Compute Isolation | Plugins run in-process | Ephemeral micro-sandboxes (gVisor, microVMs) | 
| Human-in-the-Loop | `AutoInvokeKernelFunctions` default | Explicit approval for destructive ops | 

Until orchestration frameworks adopt these architectural changes, runtime filters are a mandatory corporate stopgap — but they are **not a cure**.

## References

* **White Paper:** [JDP-2026-001](https://jdp-security.github.io/security-research-papers/2026-04-28-semantic-kernel-disclosure.html)
* **CVE:** CVE-2026-25592 (Path Traversal in Semantic Kernel)
* **CWE-843:** Type Confusion
* **CWE-1039:** Insecure Automated Optimizations
* **OWASP LLM06:** Insecure Orchestration
* **Commit fa2d52f6:** Shell Blinding (cosmetic fix)
* **OWASP GenAI Red Teaming Manual:** Proposed Playbooks (June 2026)
