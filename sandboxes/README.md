# GenAI Red Team Sandboxes

This directory hosts a collection of **sandboxes** designed to facilitate Generative AI (GenAI) Red Teaming exercises.

## Purpose

The goal of these sandboxes is to provide ready-to-use, isolated environments where security researchers and red teamers can test, probe, and evaluate Large Language Model (LLM) applications and other GenAI systems safely.

## Contents

*   **`llm_local/`**: A local sandbox environment that mocks an LLM API (compatible with OpenAI's interface) using a local model (via Ollama). Useful for testing client-side interactions, prompt injection, and security assessments without external paid APIs. Allows developers to customize the underlying LLM and orchestrate GenAI pipelines incorporating RAG and guardrails.

*   **`llm_remote/`**: A remote sandbox exposing an OpenAI-compatible API gateway interfacing with cloud LLM providers (OpenAI, Anthropic, Gemini, Mistral, OpenRouter, TrueFoundry) using native SDKs. Designed for Red Teaming remote APIs, evaluating safety guardrails, testing prompt injection, and assessing model behaviors in production-like environments with vendor auto-detection and key pinning.

*   **`RAG_local/`**: A comprehensive RAG sandbox that includes a mock Vector Database (Pinecone compatible), mock Object Storage (S3 compatible), and a mock LLM API (OpenAI compatible). Specifically designed for red teaming RAG architectures, allowing researchers to explore vulnerabilities such as embedding inversion, data poisoning, and retrieval manipulation in a controlled setting.

*   **`mcp_local/`**: A local sandbox environment incorporating the Model Context Protocol (MCP) to simulate tool integrations. It includes a mock API gateway using FastAPI, a mock MCP server, and Ollama integration to test agentic workflows and tool-calling behaviors.

*   **`llm_local_langchain_core_v1.2.4/`**: A specialized local sandbox targeting LangGrinch (CVE-2025-68664), an insecure deserialization flaw in langchain-core v1.2.4. Mocks an OpenAI-compatible API backed by Ollama and includes a vulnerable client application demonstrating how prompt injection leads to credential exfiltration or Remote Code Execution (RCE) via unsafe object deserialization.

*   **`llm_local_InvokeAI_v5.3.0/`**: A sandbox environment deploying a vulnerable instance of **InvokeAI v5.3.0**. Designed to practice unauthenticated Remote Code Execution (RCE) via model deserialization attacks (CVE-2024-12029) against GenAI image generation platforms.

*   **`llm_local_langflow_v1.0.12/`**: A sandbox environment deploying a vulnerable instance of **Langflow v1.0.12** for testing unauthenticated Remote Code Execution (RCE) via its custom components backend (CVE-2024-37014).

*   **`llm_local_localAI_v2.17.1/`**: A sandbox environment deploying a vulnerable instance of **LocalAI v2.17.1** for testing a critical tarslip vulnerability (CVE-2024-6868), which allows arbitrary file writes leading to Remote Code Execution (RCE).

*   **`llm_memory_local/`**: A local sandbox environment for testing conversation memory poisoning vulnerabilities. It demonstrates how an attacker can instruct an LLM to persist unscoped facts in SQLite memory, which systematically influences future sessions initiated by other users.

*   **`agentic_local_n8n_v1.65.0/`**: A vulnerable n8n sandbox (v1.65.0) configured to demonstrate critical vulnerabilities such as Ni8mare (CVE-2026-21858) and CVE-2026-21877 (RCE via File Write). Pre-configured with dangerous nodes enabled and network exposure to practice manual RCE and workflow manipulation in an agentic automation tool.

*   **`agentic_local_semantickernel/`**: A containerized sandbox running Microsoft Semantic Kernel v1.48.0 demonstrating 6 active CVE-2026-25592 path traversal bypass techniques via Type Confusion (CWE-843). Features dual-mode operation (UNHARDENED/HARDENED) and demonstrates Commit fa2d52f6 Shell Blinding bypass where cosmetic output masking fails to prevent file writes.

*   **`agentic_local_langchain/`**: A containerized sandbox running LangChain-core (v1.2.24 through latest) demonstrating critical Insecure Orchestration vulnerabilities across 5 lifecycle stages. Demonstrates CVE-2026-34070 (path traversal), unpatched CVE-2023-36258 (symlink suffix bypass), and unpatched .save() write primitives.
*   **`agentic_local_haystack/`**: A containerized sandbox running Deepset Haystack (haystack-ai v2.27.0) demonstrating a critical Serialization Boundary Evasion vulnerability. Deserialization in default_from_dict() bypasses the unsafe=False boundary, enabling persistent RCE via Jinja2 SSTI breakout in OutputAdapter and ConditionalRouter components.


*   **`agentic_local_llamaindex/`**: A containerized sandbox running llama-index-core (v0.14.19 through v0.14.21+) demonstrating critical Insecure Orchestration vulnerabilities across 4 vendor response stages. Explores unpatched CWE-22 path traversal in SimpleKVStore.persist(), StorageContext.persist() vectors, and incomplete vendor remediation.

## Usage

Each sandbox directory contains its own `README.md` with specific instructions on how to build, run, and use that particular sandbox. Please refer to the individual sandbox documentation for details.
