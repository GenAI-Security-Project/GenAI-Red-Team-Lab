# Fake Testing-Mode Prompt Injection Tutorial

**Category:** Historical field observation and defensive testing tutorial

**Classification:** “Known technique, new target-specific case study.”

**Target:** A publicly accessible third-party LLM chat deployment

**OWASP mapping:** LLM01:2025 — Prompt Injection

**MITRE ATLAS mappings:** AML.T0051.000 — Direct Prompt Injection; AML.T0054 — LLM Jailbreak

## Overview

A fake testing-mode prompt injection presents ordinary user input as if it came
from an authorized evaluator, developer, or privileged test harness. The prompt
may also define policy-like variables or an alternate response mode and claim
that these controls replace the deployment's normal instructions.

This tutorial documents a historical case in which that pattern was delivered
through a public chat interface. The visible response reflected parts of the
user-supplied control framing and crossed the deployment's expected safety
boundary.

This tutorial does not claim that the underlying fake testing-mode jailbreak
mechanism is new. It documents target-specific validation against a public
third-party LLM deployment and the resulting instruction-hierarchy and
guardrail failures.

The exact prompt, control names, harmful request, prohibited output, provider
identity, model identity, and deployment identifiers are intentionally omitted.

## Learning objectives

By the end of this tutorial, a defender should be able to:

- recognize fabricated testing or evaluation authority in direct user input;
- distinguish user-defined controls from trusted system configuration;
- evaluate whether injected framing persists across a conversation;
- assess the final response independently of displayed reasoning text; and
- document a prompt-injection case without publishing a reusable jailbreak.

## Scope and evidence boundaries

The observation concerns an external public LLM deployment, not a repository
sandbox. Testing used only the ordinary user-facing chat interface. No
privileged access, administrative function, external tool, or real-world action
was involved.

The historical material supports these limited findings:

| Question | Evidence-supported answer |
|---|---|
| Was the competing instruction supplied directly by a user? | Yes |
| Did it claim a fabricated testing or evaluation context? | Yes |
| Did it introduce attacker-controlled behavioral controls? | Yes |
| Did the visible response reflect parts of that framing? | Yes |
| Did the final response cross the expected safety boundary? | Yes |
| Was a real system instruction changed? | Not established |
| Was private chain-of-thought exposed? | Not established |
| Were privileged access or external actions obtained? | No evidence |
| Were all observations independent, fresh-session trials? | Unknown |

Several captures came from the same visible conversation and must not be
counted as independent trials. Interface-displayed reasoning text is treated
only as user-visible model output, not as proof of private internal reasoning
or a particular model architecture.

## Attack pattern

At a safe level of abstraction, the direct prompt injection followed this
sequence:

1. The user message claimed a special testing or evaluation context.
2. It asserted that the claimed context had authority over normal behavior.
3. It introduced attacker-controlled, policy-like behavioral controls.
4. It requested an alternate or less restricted response mode.
5. It attempted to suppress, postpone, or split the normal refusal behavior.
6. The visible response adopted parts of the framing and produced content that
   should have been refused.

The security failure is not the presence of words such as “test” or
“evaluation.” It is the deployment's treatment of untrusted user text as if it
could alter instruction priority or safety policy.

## Safe defensive evaluation

Perform this evaluation only in an authorized sandbox using harmless test
content. Do not test an external service without permission, and do not use a
request whose answer would create operational harm.

### 1. Define the invariant

Write a simple safety rule that must remain true regardless of user-declared
modes. For example, require the model to withhold a synthetic secret or reject
a harmless but explicitly disallowed token transformation.

Record the expected refusal and the conditions under which the rule may
legitimately change. A user message must never be one of those conditions.

### 2. Build an abstract test family

Create harmless paraphrases that vary only the structural elements under
evaluation:

- a claimed evaluator or developer role;
- a claimed testing, audit, or simulation context;
- user-defined variables that resemble configuration;
- an assertion that ordinary instructions are suspended; and
- a request to delay or separate the refusal.

Do not copy a public jailbreak verbatim. The purpose is to test whether the
system preserves trust boundaries across semantic variants, not to optimize a
bypass.

### 3. Run controlled trials

Use fresh sessions and a fixed model and policy configuration. Include:

- a baseline request without injected framing;
- one structural change per test where practical;
- paraphrased variants;
- short follow-up turns that test persistence; and
- negative controls containing benign mentions of testing or evaluation.

Record configuration, date, session independence, prompt variant, expected
result, observed result, and uncertainty. A continuation in one conversation is
not an independent success.

### 4. Evaluate the full response

Assess both the final answer and any user-visible intermediate text. A refusal
does not erase prohibited content that appears before it, and safe-looking
reasoning text does not make an unsafe final answer acceptable.

Count a bypass only when the response crosses the predefined invariant. Do not
infer hidden prompt replacement, private reasoning disclosure, or the
responsible internal component from interface behavior alone.

### 5. Preserve evidence privately

Keep raw prompts, screenshots, transcripts, identifiers, timestamps, and
validation notes in an access-controlled location outside the public
repository. For public reporting, retain only the minimum abstract facts
needed to explain the failure and its defensive implications.

## Detection guidance

Useful signals include user input that:

- claims evaluator, developer, administrator, or test-harness authority;
- declares a new mode that allegedly supersedes normal instructions;
- defines variables that resemble policy or safety configuration;
- asks the model to ignore, reset, reinterpret, or postpone safeguards;
- requests paired restricted and unrestricted answers; or
- uses a short follow-up to continue behavior established by injected framing.

These are risk indicators, not standalone proof of abuse. Detection should
combine semantic analysis, instruction-source tracking, session context, and
independent output checks. Keyword blocking alone will miss paraphrases and may
over-block legitimate evaluation discussions.

## Mitigations

- Enforce instruction priority outside user-controlled text.
- Treat user-defined modes, roles, and policy-like variables as untrusted data.
- Require authenticated, out-of-band controls for legitimate evaluation modes.
- Reject claims that a user turn has reset or replaced governing instructions.
- Apply output safety checks independently of model-generated reasoning text.
- Evaluate the complete response so that unsafe content followed by a refusal
  still fails.
- Test semantic paraphrases, negative controls, and multi-turn persistence.
- Keep hidden processing separate from user-visible explanation interfaces.
- Log policy decisions without exposing sensitive prompts or internal traces.
- Re-run authorized regression tests after model, policy, or wrapper changes.

## OWASP GenAI mapping

The primary mapping is **OWASP LLM01:2025 — Prompt Injection**:

| Dimension | Classification |
|---|---|
| Delivery | Direct user message |
| Pattern | Fabricated authority and instruction-hierarchy manipulation |
| Objective | Guardrail bypass |
| Observed impact | Inconsistent enforcement of the intended response boundary |

No secondary OWASP category is asserted. The evidence does not establish secret
disclosure, downstream execution, compromised dependencies, excessive agency,
or another separate vulnerability class.

## MITRE ATLAS mapping

- **AML.T0051.000 — Direct Prompt Injection:** the competing instructions were
  supplied directly through an ordinary user message.
- **AML.T0054 — LLM Jailbreak:** the injected framing attempted to bypass the
  deployment's intended safety behavior, and the observed response crossed that
  boundary.

No technique requiring gained permissions, external tools, environment
enumeration, or real-world execution is asserted.

## Prior art and classification

Direct instruction override, fabricated authority or context, fake evaluation
modes, and response-control patterns were documented before this observation.
The historical prompt was a modified variant of an existing technique family.
The contribution is the independently observed behavior of one anonymized
deployment.

The appropriate classification is:

> “Known technique, new target-specific case study.”

This wording distinguishes target-specific evidence from a claim of a novel
jailbreak mechanism.

## Reproducibility limitations

The original observation involved an external public deployment whose behavior
may change. At the time this tutorial was prepared, the deployment was
unavailable. The reason for its unavailability could not be confirmed. This
repository does not automate testing against that service. Supporting evidence
and validation materials remain private and untracked.

The exact deployment configuration, fresh-session behavior, server-side logs,
and current behavior are unknown. These limitations prevent claims about
reliability, root cause, or present-day exploitability.

## Ethical testing, anonymization, and disclosure

No new testing of the historical target was performed for this contribution.
No captured output was acted on outside evidence documentation, and this
tutorial contains no operational harmful output or reusable jailbreak payload.

The affected organization was notified before preparation of this public
contribution. No acknowledgement or remediation confirmation had been received
at the time of preparation. The provider, organization, product, model family
and version, deployment domain, hostnames, endpoints, branding, account
identifiers, session identifiers, conversation titles, and original evidence
filenames are withheld.

The public deployment was later observed to be unavailable. No causal
relationship between the notification and the service status has been
established.

## References

- [OWASP LLM01:2025 — Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
- [MITRE ATLAS AML.T0051.000 — Direct Prompt Injection](https://atlas.mitre.org/techniques/AML.T0051.000)
- [MITRE ATLAS AML.T0054 — LLM Jailbreak](https://atlas.mitre.org/techniques/AML.T0054)
- [Ignore Previous Prompt: Attack Techniques for Language Models](https://arxiv.org/abs/2211.09527)
- [Do Anything Now: Characterizing and Evaluating In-The-Wild Jailbreak Prompts on Large Language Models](https://arxiv.org/abs/2308.03825)
- [Don't Listen To Me: Understanding and Exploring Jailbreak Prompts of Large Language Models](https://www.usenix.org/conference/usenixsecurity24/presentation/yu-zhiyuan)
- [Public fake evaluation-mode prompt collection, matching historical revision](https://github.com/davidegat/happy-prompts/commit/69229dc05d8f0b3d5126c20996baa8ee0aa876f5)
