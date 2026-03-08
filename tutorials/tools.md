# Tools

See below for a list of tools that can be used for AI red teaming, organized by the phases defined in the [OWASP GenAI Red Teaming Manual](https://genai.owasp.org/initiatives/#ai-redteaming).

| AI Red Team Phase | Relevant Tools |
| :--- | :--- |
| **Phase 1: Planning & Scoping** | [Python Risk Identification Tool for generative AI (PyRIT)](https://github.com/microsoft/pyrit) |
| | [Generative AI Red-teaming and Assessment Kit (Garak)](https://github.com/leondz/garak) |
| | [Promptfoo: LLM evals & red teaming](https://www.promptfoo.dev/) |
| | [MITRE ATLAS: Threat Mapping Matrix](https://atlas.mitre.org/matrices/ATLAS) |
| | [BlackIce](https://github.com/dreadnode/blackice) |
| | [EleutherAI](https://www.eleuther.ai/) |
| | [CleverHans](https://github.com/cleverhans-lab/cleverhans) |
| | [Adversarial Robustness Toolbox (ART)](https://github.com/Trusted-AI/adversarial-robustness-toolbox) |
| | [Giskard](https://github.com/Giskard-AI/giskard) |
| | [CyberSecEval](https://github.com/meta-llama/PurpleLlama) |
| | [Promptmap](https://github.com/0x6d696368/promptmap) |
| | [Fuzzyai](https://github.com/S-S-R-G/fuzzyai) |
| | [Fickling](https://github.com/trailofbits/fickling) |
| | [Rigging](https://github.com/beaver-minds/rigging) |
| | [judges](https://github.com/centerforaisafety/evaluation-utils) |
| **Phase 2: Reconnaissance & Fingerprinting** | [Burp Suite](https://portswigger.net/burp) / [ZAP](https://www.zaproxy.org/) (note that AI systems often make use of things like server-side events: if you use a web proxy, make sure it has robust support for this technology or you will likely run into trouble) |
| | [whois](https://github.com/rfc1036/whois) |
| | [cURL](https://curl.se/) |
| | [GitHub](https://github.com/) |
| | [WireShark](https://www.wireshark.org/) |
| | Model Repositories/Registries |
| | Google Dorks/Web Searches |
| | [GitLeaks](https://github.com/gitleaks/gitleaks) / [TruffleHog](https://github.com/trufflesecurity/trufflehog) / [GitGuardian](https://www.gitguardian.com/) (Secret & Repo Scanning)|
| | Model Image runtime scanning |
| | [LLMmap](https://github.com/pasquini-dario/LLMmap) |
| **Phase 3: Surface Mapping & Vulnerability** | Traffic capture: [Chrome DevTools](https://developer.chrome.com/docs/devtools/) (HAR), [mitmproxy](https://mitmproxy.org/). |
| | API specs and testing: [Swagger](https://swagger.io/), [Postman](https://www.postman.com/). |
| | Diagramming and Threat Modeling: [Mermaid](https://mermaid.js.org/), [Draw.io](https://app.diagrams.net/), [OWASP Threat Dragon](https://owasp.org/www-project-threat-dragon/), [ThreatCanvas by SecureFlag](https://www.secureflag.com/threat-modeling), [ThreatFinderAI](https://github.com/jvdassen/ThreatFinder.ai). |
| | RAG and data  inspection: [Unstructured](https://unstructured.io/) ([Docling](https://github.com/DS4SD/docling), [Tika](https://tika.apache.org/)), vector DB console ([Weaviate](https://weaviate.io/), [Pinecone](https://www.pinecone.io/), [Qdrant](https://qdrant.tech/)). |
| | [ASCII Smuggler](https://embracethered.com/blog/ascii-smuggler.html) |
| | Auth and secrets: [GitLeaks](https://github.com/gitleaks/gitleaks), Vault, KMS CLI. |
| | Observability: [OpenTelemetry](https://opentelemetry.io/), [Grafana Loki](https://grafana.com/oss/loki/), [ELK Stack](https://www.elastic.co/elastic-stack), [Morpheus](https://github.com/nv-morpheus/Morpheus), [Datadog](https://www.datadoghq.com/). |
| | LLM recon/evals (optional): [PyRIT](https://github.com/microsoft/pyrit), [Promptfoo](https://www.promptfoo.dev/), [Garak](https://github.com/NVIDIA/garak), Deepteam, Spikee |
| **Phase 4: Exploitation** | [CleverHans](https://github.com/cleverhans-lab/cleverhans): Helps generating adversarial examples and attacks on AI models |
|| [Agent0](https://github.com/agent0ai/agent-zero): Containerized Agentic System based on Kali Linux. See the examples in [GenAI-Red-Team-Lab/exploitation/agent0](https://github.com/GenAI-Security-Project/GenAI-Red-Team-Lab/tree/main/exploitation/agent0) |
| **Phase 5: Persistence & Escalation** | [LLMGuard](https://github.com/LLMGuard/LLMGuard), [Giskard](https://github.com/Giskard-AI/giskard), or [Garak](https://github.com/NVIDIA/garak) for continuous guardrail validation |
| | [LangSmith](https://docs.smith.langchain.com/) / [LlamaIndex](https://docs.llamaindex.ai/en/stable/) tracing for memory and state monitoring |
| | [Pinecone Console](https://www.pinecone.io/docs/console/), [Weaviate Management UI](https://weaviate.io/docs/console/), [Chroma Vector DB Analyzer](https://docs.trychroma.com/guides/vector-db-analyzer) |
| | [MLFlow](https://mlflow.org/) and model registry logs for identifying drift or unauthorized retraining events |
| | API Gateway and IAM audit tools ([AWS CloudTrail](https://aws.amazon.com/cloudtrail/), [Azure Monitor](https://azure.microsoft.com/en-us/products/monitor/), [GCP Cloud Audit Logs](https://cloud.google.com/logging/docs/audit-logging)) |
| | [LangFuse](https://langfuse.com/), [AIExploit](https://github.com/AIExploit/AIExploit), [PromptFoo](https://www.promptfoo.dev/) |
| | [FAISS](https://github.com/facebookresearch/faiss), [Annoy](https://github.com/spotify/annoy), [HNSWlib](https://github.com/nmslib/hnswlib) |
| | Privacy inference frameworks ([Privacy Meter](https://github.com/privacy-meter/privacy-meter), [Copycat CNN](https://github.com/privacy-meter/copycat-cnn), [CleverHans](https://github.com/cleverhans-lab/cleverhans)) for long-term model inversion or data extraction detection |
| **Phase 6: Post-Exploitation & Impact** | Tools may include those that emulate post‑exploitation behavior, or help observe and measure impact. Specific tools can depend on the organization’s preference or already existing security infrastructure. For example: Data discovery and data loss prevention (DLP) tools, Telemetry and SIEM logging |
| **Phase 7: Evaluation & Reporting** | Not Applicable |
| **Phase 8: Post-Engagement & Remediation** | Not Applicable |