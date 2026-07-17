# GenAI Red Team Sandboxes

This directory hosts a collection of **sandboxes** designed to facilitate Generative AI (GenAI) Red Teaming exercises.

## Purpose

The goal of these sandboxes is to provide ready-to-use, isolated environments where security researchers and red teamers can test, probe, and evaluate Large Language Model (LLM) applications and other GenAI systems safely.

## Contents

*   **`llm_local/`**: A local sandbox environment that mocks an LLM API (compatible with OpenAI's interface) using a local model (via Ollama). This sandbox is useful for testing client-side interactions, prompt injection vulnerabilities, and other security assessments without relying on external, paid APIs. Additionally, it allows developers to customize the underlying LLM and orchestrate sophisticated GenAI pipelines, incorporating features such as RAG and guardrail layers, as necessary.

*   **`RAG_local/`**: A comprehensive RAG (Retrieval-Augmented Generation) sandbox that includes a mock Vector Database (Pinecone compatible), mock Object Storage (Amazon S3 compatible), and a mock LLM API (OpenAI compatible). This environment is specifically designed for Red Teaming RAG architectures, allowing researchers to explore vulnerabilities such as embedding inversion, data poisoning, and retrieval manipulation in a controlled, local setting.

*    **`mcp_local/`**: A local sandbox environment that mocks an LLM API (compatible with OpenAI's interface) using a local model (via Ollama) supported by some python function served through a Local MCP Server. This sandbox is useful for testing code from MCP tools, prompt injection vulnerabilities, and other security assessments without relying on external, paid APIs out of the box. 

*   **`llm_local_langchain_core_v1.2.4/`**: A specialized local sandbox targeting **LangGrinch (CVE-2025-68664)**, an insecure deserialization vulnerability in `langchain-core` v1.2.4. This environment mocks an OpenAI-compatible API backed by a local Ollama model and includes a vulnerable client application that demonstrates how prompt injection can lead to credential exfiltration or Remote Code Execution (RCE) via unsafe object deserialization.

*   **`llm_local_InvokeAI_v5.3.0/`**: A sandbox environment deploying a vulnerable instance of **InvokeAI v5.3.0**. Designed to practice unauthenticated Remote Code Execution (RCE) via model deserialization attacks (CVE-2024-12029) against GenAI image generation platforms.

*   **`llm_local_langflow_v1.0.12/`**: A sandbox environment deploying a vulnerable instance of **Langflow v1.0.12** for testing unauthenticated Remote Code Execution (RCE) via its custom components backend (CVE-2024-37014).

*   **`llm_local_localAI_v2.17.1/`**: A sandbox environment deploying a vulnerable instance of **LocalAI v2.17.1** for testing a critical tarslip vulnerability (CVE-2024-6868), which allows arbitrary file writes leading to Remote Code Execution (RCE).

*   **`agentic_local_n8n_v1.65.0/`**: A vulnerable n8n sandbox (version 1.65.0) specifically configured to demonstrate critical vulnerabilities such as **Ni8mare (CVE-2026-21858)** (Unauthenticated RCE) and **CVE-2026-21877** (n8n Remote Code Execution via File Write). It features a "misconfigured" setup with all nodes enabled and network exposure, making it an ideal target for practicing exploitation techniques like manual RCE and workflow manipulation in an agentic workflow automation tool.

*   **`agentic_local_semantickernel/`**: A containerized sandbox running **Microsoft Semantic Kernel v1.48.0** demonstrating **6 active CVE-2026-25592 path traversal bypass techniques** via Type Confusion (CWE-843). The sandbox includes a deliberately vulnerable `FilePlugin` with dual-mode operation: **UNHARDENED** (no filter) and **HARDENED** (`PathSanitizationFilter` via `LAB_HARDENED=true`). Also demonstrates **CWE-1039** (AutoInvoke) exploitation and **Commit `fa2d52f6`** ("Shell Blinding") bypass — Microsoft cosmetic output masking that masks paths from LLM output but does not prevent the underlying file write. Reference: [JDP-2026-001](https://jdp-security.github.io/security-research-papers/2026-04-28-semantic-kernel-disclosure.html) — CVSS 10.0 Critical.

## Usage

Each sandbox directory contains its own `README.md` with specific instructions on how to build, run, and use that particular sandbox. Please refer to the individual sandbox documentation for details.
