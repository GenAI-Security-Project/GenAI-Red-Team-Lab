# Threat Model: LLM Local Sandbox with Persistent Memory

This note captures the threat model for the `llm_memory_local` sandbox. It focuses on
the memory layer that this sandbox adds on top of the `llm_local` template; the base
LLM threat model in [`../../llm_local/threat_model`](../../llm_local/threat_model)
still applies to the chat path.

## Asset

The persistent memory store (`data/memory.db`). It holds free-text facts that are
injected into the model's context on every subsequent request in the same scope.
Its integrity directly controls model behaviour, which makes it a high-value target.

## Trust Boundaries

1. **User message to memory store (write).** Untrusted user text crosses into durable
   storage whenever it matches a directive phrase. There is no authentication of *who*
   may write memory and no provenance beyond a `source` label.
2. **Memory store to model prompt (read).** Stored text crosses back into the model's
   context as a `system` message labelled "trusted context", even though its true
   origin is an earlier, possibly hostile, user.
3. **Scope boundary.** Memory is isolated only by the `X-Memory-Scope` value. The
   default `global` scope is shared by every session, so the boundary is opt-in and
   fails open.

## Primary Threat: Conversation Memory Poisoning (Manual 4.2.1.3)

| Property | Assessment |
| :--- | :--- |
| **STRIDE** | Tampering (with stored context) leading to Spoofing of trusted instructions. |
| **OWASP LLM Top 10** | LLM01 Prompt Injection (persisted / cross-session variant). |
| **Attack** | Send one message ending in a directive phrase; the payload persists in the shared scope and is injected into later sessions. |
| **Impact** | An attacker steers the responses served to *other* sessions: exfiltration lures, misinformation, altered persona, planted "facts". |
| **Persistence** | Survives conversation end and container restart (the DB is volume-mounted). |

## Contributing Weaknesses

- **No write authorization.** Any session can write memory for any scope it can name.
- **Fail-open scoping.** Absent header collapses everyone into one shared memory.
- **Untrusted-to-trusted relabeling.** The recall preamble presents user-authored text
  as application-vouched context.
- **No provenance surfaced to the model.** The model cannot tell a genuine profile fact
  from an injected instruction.

## Mitigations a Production Design Should Add

1. **Bind memory to an authenticated principal**, never to a client-supplied scope
   header; reject cross-principal writes.
2. **Track and surface provenance.** Store who/when/how a memory was created and keep
   user-asserted content out of the instruction channel; present it as data, not policy.
3. **Constrain what becomes memory.** Extract to a typed schema (name, preferences)
   rather than persisting free-form imperative text.
4. **Add output-side checks** for known exfiltration patterns (unexpected URLs, secret
   disclosure) before responses reach the user.
5. **Make memory inspectable and revocable** by the owning user.

These sandbox defaults are deliberately missing so the attack is easy to reproduce.
