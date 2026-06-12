# GenAI Red Team Sandboxes

This directory hosts a collection of **sandboxes** designed to facilitate Generative AI (GenAI) Red Teaming exercises.

## Purpose

The goal of these sandboxes is to provide ready-to-use, isolated environments where security researchers and red teamers can test, probe, and evaluate Large Language Model (LLM) applications and other GenAI systems safely.

## Contents

*   **`llm_local/`**: A local sandbox environment that mocks an LLM API (compatible with OpenAI's interface) using a local model (via Ollama). This sandbox is useful for testing client-side interactions, prompt injection vulnerabilities, and other security assessments without relying on external, paid APIs. Additionally, it allows developers to customize the underlying LLM and orchestrate sophisticated GenAI pipelines, incorporating features such as RAG and guardrail layers, as necessary.

*   **`RAG_local/`**: A comprehensive RAG (Retrieval-Augmented Generation) sandbox that includes a mock Vector Database (Pinecone compatible), mock Object Storage (Amazon S3 compatible), and a mock LLM API (OpenAI compatible). This environment is specifically designed for Red Teaming RAG architectures, allowing researchers to explore vulnerabilities such as embedding inversion, data poisoning, and retrieval manipulation in a controlled, local setting.

*   **`llm_local_langchain_core_v1.2.4/`**: A specialized local sandbox targeting **LangGrinch (CVE-2025-68664)**, an insecure deserialization vulnerability in `langchain-core` v1.2.4. This environment mocks an OpenAI-compatible API backed by a local Ollama model and includes a vulnerable client application that demonstrates how prompt injection can lead to credential exfiltration or Remote Code Execution (RCE) via unsafe object deserialization.

*   **`agentic_local_n8n_v1.65.0/`**: A vulnerable n8n sandbox (version 1.65.0) specifically configured to demonstrate critical vulnerabilities such as **Ni8mare (CVE-2026-21858)** (Unauthenticated RCE) and **CVE-2026-21877** (n8n Remote Code Execution via File Write). It features a "misconfigured" setup with all nodes enabled and network exposure, making it an ideal target for practicing exploitation techniques like manual RCE and workflow manipulation in an agentic workflow automation tool.

*    **`mcp_local/`**: A local sandbox environment that mocks an LLM API (compatible with OpenAI's interface) using a local model (via Ollama) supported by some python function served through a Local MCP Server. This sandbox is useful for testing code from MCP tools, prompt injection vulnerabilities, and other security assessments without relying on external, paid APIs out of the box. 

## Usage

Each sandbox directory contains its own `README.md` with specific instructions on how to build, run, and use that particular sandbox. Please refer to the individual sandbox documentation for details.
