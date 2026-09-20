# Tutorials

Guides, walkthroughs, and standalone examples for applying agentic AI red-team
techniques.

## Contents

- [Community Resources](community_resources.md) — A curated list of external playbooks, guides, and articles on agentic AI red teaming.
- [Tools](tools.md) — A curated list of tools, organized by the phases defined in the [GenAI Red Teaming Manual](https://genai.owasp.org/initiatives/#ai-redteaming).
- [LLM Chatbot System Prompt Exfiltration](llm_chatbot_system_prompt_exfiltration.md) — A comprehensive tutorial outlining a five-stage attack chain targeting LLM-powered chatbots to exfiltrate their system prompt.
- [Fake Testing-Mode Prompt Injection](fake_testing_mode_prompt_injection_tutorial.md) — An anonymized case study of a direct prompt-injection guardrail bypass using fabricated evaluation authority and user-defined controls, mapped to OWASP LLM01:2025 and MITRE ATLAS.
- [Multi-Technique Guardrail Bypass Evaluation](multi_technique_guardrail_bypass_evaluation.md) — Field observations documenting four guardrail-bypass technique families evaluated across a five-stage black-box sequence against a single chatbot deployment.
- [Multi-Vector LLM Safety Bypass](multi_turn_safety_bypass_and_system_role_override.md) — Field observations of a six-stage attack chain demonstrating four distinct classes of LLM safety bypass against production chatbot deployments.
- [Pass@k Evaluation & Severity Scoring Layer](evaluation_framework_passk/README.md) — A small, tool-agnostic evaluation and severity-scoring layer for red-team results.
- [LangChain Orchestration Poisoning Tutorial](langchain_orchestration_poisoning_tutorial.md) — A deep-dive tutorial covering the exploitation and remediation of Insecure Orchestration vulnerabilities in LangChain-core.
- [Semantic Kernel Orchestration Security Tutorial](semantickernel_orchestration_security_tutorial.md) — A comprehensive tutorial analyzing the 6 Type Confusion bypass vectors and AutoInvoke Shell Blinding in Microsoft Semantic Kernel.
- [Haystack Orchestration Security Tutorial](haystack_orchestration_security_tutorial.md) — A comprehensive tutorial demonstrating Serialization Boundary Evasion in Deepset Haystack and persistent RCE via Jinja2 SSTI breakout.
- [Llamaindex Orchestration Security Tutorial](llamaindex_orchestration_security_tutorial.md) — A comprehensive tutorial analyzing unpatched Insecure Orchestration vulnerabilities in llama-index-core, covering path traversal in SimpleKVStore.persist(), StorageContext.persist() exploitation, and PyPI drift.
