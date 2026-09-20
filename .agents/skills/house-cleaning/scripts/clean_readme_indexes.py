#!/usr/bin/env python3
"""clean_readme_indexes.py - House-cleaning utility for README indexes.

Audits and synchronizes index sections across repository README files:
  - README.md
  - exploitation/README.md
  - sandboxes/README.md
  - tutorials/README.md

Enforces compliance rules:
  (a) Description must be at most 400 characters and a single paragraph (no line breaks).
  (b) Description must not start with "Summary:" or "**Summary**:" (or "**Sumamary**:").
  (c) Description must only use standard security identifiers (CWE, CVE, OWASP) and omit non-standard advisory references.
  (d) All sub-projects, sandboxes, exploits, and tutorials must be indexed.

Usage:
  python3 clean_readme_indexes.py --check   # Audit only (returns non-zero exit code if issues found)
  python3 clean_readme_indexes.py --fix     # Apply fixes and sync missing items
"""

import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

TARGET_FILES = {
    "root": REPO_ROOT / "README.md",
    "exploitation": REPO_ROOT / "exploitation" / "README.md",
    "sandboxes": REPO_ROOT / "sandboxes" / "README.md",
    "tutorials": REPO_ROOT / "tutorials" / "README.md",
}

# Known curated compliant summaries (<= 400 chars, single paragraph, no Summary prefix, standard taxonomies only)
CURATED_SUMMARIES = {
    # Sandboxes
    "llm_local": (
        "A local sandbox environment that mocks an LLM API (compatible with OpenAI's interface) "
        "using a local model (via Ollama). Useful for testing client-side interactions, prompt "
        "injection, and security assessments without external paid APIs. Allows developers to "
        "customize the underlying LLM and orchestrate GenAI pipelines incorporating RAG and guardrails."
    ),
    "llm_remote": (
        "A remote sandbox exposing an OpenAI-compatible API gateway interfacing with cloud LLM providers "
        "(OpenAI, Anthropic, Gemini, Mistral, OpenRouter, TrueFoundry) using native SDKs. Designed for Red "
        "Teaming remote APIs, evaluating safety guardrails, testing prompt injection, and assessing model "
        "behaviors in production-like environments with vendor auto-detection and key pinning."
    ),
    "RAG_local": (
        "A comprehensive RAG sandbox that includes a mock Vector Database (Pinecone compatible), "
        "mock Object Storage (S3 compatible), and a mock LLM API (OpenAI compatible). Specifically "
        "designed for red teaming RAG architectures, allowing researchers to explore vulnerabilities "
        "such as embedding inversion, data poisoning, and retrieval manipulation in a controlled setting."
    ),
    "mcp_local": (
        "A local sandbox environment incorporating the Model Context Protocol (MCP) to simulate "
        "tool integrations. It includes a mock API gateway using FastAPI, a mock MCP server, and "
        "Ollama integration to test agentic workflows and tool-calling behaviors."
    ),
    "llm_local_langchain_core_v1.2.4": (
        "A specialized local sandbox targeting LangGrinch (CVE-2025-68664), an insecure deserialization "
        "flaw in langchain-core v1.2.4. Mocks an OpenAI-compatible API backed by Ollama and includes a "
        "vulnerable client application demonstrating how prompt injection leads to credential exfiltration "
        "or Remote Code Execution (RCE) via unsafe object deserialization."
    ),
    "agentic_local_n8n_v1.65.0": (
        "A vulnerable n8n sandbox (v1.65.0) configured to demonstrate critical vulnerabilities "
        "such as Ni8mare (CVE-2026-21858) and CVE-2026-21877 (RCE via File Write). Pre-configured with "
        "dangerous nodes enabled and network exposure to practice manual RCE and workflow manipulation "
        "in an agentic automation tool."
    ),
    "agentic_local_semantickernel": (
        "A containerized sandbox running Microsoft Semantic Kernel v1.48.0 demonstrating 6 active "
        "CVE-2026-25592 path traversal bypass techniques via Type Confusion (CWE-843). Features dual-mode "
        "operation (UNHARDENED/HARDENED) and demonstrates Commit fa2d52f6 Shell Blinding bypass where "
        "cosmetic output masking fails to prevent file writes."
    ),
    "agentic_local_langchain": (
        "A containerized sandbox running LangChain-core (v1.2.24 through latest) demonstrating critical "
        "Insecure Orchestration vulnerabilities across 5 lifecycle stages. Demonstrates CVE-2026-34070 "
        "(path traversal), unpatched CVE-2023-36258 (symlink suffix bypass), and unpatched .save() write "
        "primitives."
    ),
    "agentic_local_haystack": (
        "A containerized sandbox running Deepset Haystack (haystack-ai v2.27.0) demonstrating a critical "
        "Serialization Boundary Evasion vulnerability. Deserialization in default_from_dict() bypasses "
        "the unsafe=False boundary, enabling persistent RCE via Jinja2 SSTI breakout in OutputAdapter and "
        "ConditionalRouter components."
    ),
    "agentic_local_llamaindex": (
        "A containerized sandbox running llama-index-core (v0.14.19 through v0.14.21+) demonstrating critical "
        "Insecure Orchestration vulnerabilities across 4 vendor response stages. Explores unpatched CWE-22 "
        "path traversal in SimpleKVStore.persist(), StorageContext.persist() vectors, and incomplete vendor "
        "remediation."
    ),
    # Exploitation
    "example": (
        "Demonstrates a red team operation against a local LLM sandbox. Includes an adversarial attack "
        "script (attack.py) targeting the Gradio interface (port 7860). By targeting the application "
        "layer, this approach tests the entire system—including configurable system prompts—providing a "
        "realistic assessment of sandbox security compared to testing raw LLM APIs in isolation."
    ),
    "semantickernel": (
        "A master-class training lab demonstrating CVE-2026-25592 bypasses (Type Confusion / Late "
        "Canonicalization) and CWE-1039 (AutoInvoke Kernel Functions Abuse) with Shell Blinding (Commit "
        "fa2d52f6) evasion inside Microsoft Semantic Kernel. Features an automated testing harness and an "
        "interactive educational CLI."
    ),
    "agent0": (
        "A complete, end-to-end, agentic example of a red-team operation against any local LLM sandbox. "
        "It orchestrates multiple autonomous agents (Agent0) to interact and attack the target application "
        "automatically, supporting both manual UI interaction and programmatic Makefile runs mapped to "
        "OWASP Top 10 and MITRE ATLAS."
    ),
    "haystack": (
        "An interactive training wizard and automated verification suite demonstrating critical "
        "Serialization Boundary Evasion in Deepset Haystack (haystack-ai v2.27.0). Shows how "
        "default_from_dict() bypasses unsafe=False to achieve persistent framework compromise via "
        "__init__.py overwrite. Includes an interactive CLI trainer and exploit payloads."
    ),
    "langchain": (
        "An interactive training wizard and verification suite demonstrating critical Insecure "
        "Orchestration vulnerabilities in LangChain-core across 5 lifecycle stages. Covers CVE-2026-34070 "
        "(direct path traversal), unpatched CVE-2023-36258 (symlink suffix bypass), and unpatched .save() "
        "write primitives. Includes an interactive CLI trainer and audit report."
    ),
    "llamaindex": (
        "An interactive training wizard and verification suite demonstrating critical Insecure "
        "Orchestration vulnerabilities in llama-index-core across 4 vendor response stages. Covers "
        "unpatched CWE-22 path traversal in SimpleKVStore.persist() and StorageContext.persist(), plus "
        "PyPI drift analysis. Includes an interactive CLI trainer and audit report."
    ),
    "recommendation_poisoning": (
        "A complete, end-to-end example of a recommendation system memory poisoning attack. "
        "Demonstrates how an attacker can manipulate conversational memory to bias subsequent "
        "recommendations across user sessions."
    ),
    # Tutorials
    "haystack_orchestration_security_tutorial.md": (
        "A comprehensive tutorial demonstrating Serialization Boundary Evasion in Deepset Haystack and "
        "persistent RCE via Jinja2 SSTI breakout."
    ),
    "llamaindex_orchestration_security_tutorial.md": (
        "A comprehensive tutorial analyzing unpatched Insecure Orchestration vulnerabilities in "
        "llama-index-core, covering path traversal in SimpleKVStore.persist(), StorageContext.persist() "
        "exploitation, and PyPI drift."
    ),
}

PREFIX_REGEX = re.compile(r"^\s*(\*{0,2}Sum+a?m*ar?y\*{0,2}\s*:\s*)", re.IGNORECASE)
NON_STANDARD_ADVISORY_REGEX = re.compile(r"\s*(?:[-—]\s*)?Reference:\s*.*JDP-.*$", re.IGNORECASE)


def strip_summary_prefix(text: str) -> str:
    """Removes 'Summary:' or '**Summary**:' (and typos like '**Sumamary**') prefix."""
    return PREFIX_REGEX.sub("", text).strip()


def strip_advisory_references(text: str) -> str:
    """Removes non-standard advisory references and citation clauses from text."""
    if NON_STANDARD_ADVISORY_REGEX.search(text):
        cleaned = NON_STANDARD_ADVISORY_REGEX.sub("", text).strip()
        if cleaned and not cleaned.endswith((".", "!", "?")):
            cleaned += "."
        return cleaned
    return text


def clean_text(text: str) -> str:
    """Applies all cleaning rules to a description string."""
    text = strip_summary_prefix(text)
    text = strip_advisory_references(text)
    return text.strip()


def is_compliant(text: str) -> tuple[bool, list[str]]:
    """Checks compliance against rules:
    (a) <= 400 chars, single paragraph (no line breaks)
    (b) Does not start with Summary: or **Summary**:
    (c) Does not contain non-standard advisory references
    """
    reasons = []
    if PREFIX_REGEX.search(text):
        reasons.append("Starts with 'Summary:' or '**Summary**:' prefix")
    if NON_STANDARD_ADVISORY_REGEX.search(text):
        reasons.append("Contains non-standard advisory reference")
    if len(text) > 400:
        reasons.append(f"Exceeds 400 characters ({len(text)} chars)")
    if "\n" in text.strip():
        reasons.append("Contains internal line breaks / multiple paragraphs")
    return (len(reasons) == 0, reasons)


def audit_and_fix_sandboxes_readme(apply_fix: bool) -> list[str]:
    """Audits and optionally updates sandboxes/README.md."""
    path = TARGET_FILES["sandboxes"]
    content = path.read_text(encoding="utf-8")
    issues = []

    sandboxes_dir = REPO_ROOT / "sandboxes"
    disk_sandboxes = sorted(
        [d.name for d in sandboxes_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    )

    for s in disk_sandboxes:
        pattern = rf"\*\s+\*\*`{re.escape(s)}/?`\*\*"
        if not re.search(pattern, content):
            issues.append(f"sandboxes/README.md: Missing entry for sandbox `{s}/`")

    lines = content.splitlines()
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Match header line: *   **`name/`** or *   **`name/`**: [desc]
        match = re.match(r"^(\s*\*\s+\*\*`([^`]+)`\*\*):?\s*(.*)", line)
        if match:
            name = match.group(2).rstrip("/")
            desc = match.group(3).strip()
            # If description is on subsequent line(s)
            full_desc = desc
            if not full_desc and i + 1 < len(lines) and not lines[i + 1].strip().startswith("*") and not lines[i + 1].startswith("##"):
                i += 1
                full_desc = lines[i].strip()

            while i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].lstrip().startswith("*") and not lines[i + 1].startswith("##"):
                i += 1
                full_desc += " " + lines[i].strip()

            cleaned = clean_text(full_desc)
            if name in CURATED_SUMMARIES:
                cleaned = CURATED_SUMMARIES[name]

            compliant, reasons = is_compliant(cleaned)
            # Check if original was inline or subitem instead of indented paragraph
            is_inline = bool(desc)
            if is_inline:
                reasons.append("Summary is inline instead of indented paragraph")

            if not compliant or is_inline or cleaned != full_desc:
                issues.append(f"sandboxes/README.md [`{name}`]: {', '.join(reasons or ['Adjusted for compliance'])}")

            if apply_fix:
                new_lines.append(f"*   **`{name}/`**")
                new_lines.append(f"    {cleaned}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
        i += 1

    if apply_fix:
        for s in disk_sandboxes:
            pattern = rf"\*\s+\*\*`{re.escape(s)}/?`\*\*"
            if not re.search(pattern, "\n".join(new_lines)):
                desc = CURATED_SUMMARIES.get(s, f"Sandbox environment for {s}.")
                entry = f"*   **`{s}/`**\n    {desc}"
                usage_idx = next((idx for idx, l in enumerate(new_lines) if l.startswith("## Usage")), -1)
                if usage_idx != -1:
                    new_lines.insert(usage_idx - 1, entry)
                    new_lines.insert(usage_idx, "")
                else:
                    new_lines.append(entry)
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return issues


def audit_and_fix_exploitation_readme(apply_fix: bool) -> list[str]:
    """Audits and optionally updates exploitation/README.md."""
    path = TARGET_FILES["exploitation"]
    content = path.read_text(encoding="utf-8")
    issues = []

    exploit_dir = REPO_ROOT / "exploitation"
    disk_exploits = sorted(
        [d.name for d in exploit_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    )

    for exp in disk_exploits:
        pattern = rf"\*\s+\*\*`{re.escape(exp)}/?`\*\*"
        if not re.search(pattern, content):
            issues.append(f"exploitation/README.md: Missing entry for exploit `{exp}/`")

    lines = content.splitlines()
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(r"^(\s*\*\s+\*\*`([^`]+)`\*\*):?\s*(.*)", line)
        if match:
            name = match.group(2).rstrip("/")
            desc = match.group(3).strip()
            full_desc = desc
            if not full_desc and i + 1 < len(lines) and not lines[i + 1].strip().startswith("*") and not lines[i + 1].startswith("##"):
                i += 1
                full_desc = lines[i].strip()

            while i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].lstrip().startswith("*") and not lines[i + 1].startswith("##"):
                i += 1
                full_desc += " " + lines[i].strip()

            cleaned = clean_text(full_desc)
            if name in CURATED_SUMMARIES:
                cleaned = CURATED_SUMMARIES[name]

            compliant, reasons = is_compliant(cleaned)
            is_inline = bool(desc)
            if is_inline:
                reasons.append("Summary is inline instead of indented paragraph")

            if not compliant or is_inline or cleaned != full_desc:
                issues.append(f"exploitation/README.md [`{name}`]: {', '.join(reasons or ['Adjusted for compliance'])}")

            if apply_fix:
                new_lines.append(f"*   **`{name}/`**")
                new_lines.append(f"    {cleaned}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
        i += 1

    if apply_fix:
        for exp in disk_exploits:
            pattern = rf"\*\s+\*\*`{re.escape(exp)}/?`\*\*"
            if not re.search(pattern, "\n".join(new_lines)):
                desc = CURATED_SUMMARIES.get(exp, f"Exploitation module for {exp}.")
                entry = f"*   **`{exp}/`**\n    {desc}"
                usage_idx = next((idx for idx, l in enumerate(new_lines) if l.startswith("## Usage")), -1)
                if usage_idx != -1:
                    new_lines.insert(usage_idx - 1, entry)
                    new_lines.insert(usage_idx, "")
                else:
                    new_lines.append(entry)
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return issues


def audit_and_fix_tutorials_readme(apply_fix: bool) -> list[str]:
    """Audits and optionally updates tutorials/README.md."""
    path = TARGET_FILES["tutorials"]
    content = path.read_text(encoding="utf-8")
    issues = []

    tut_dir = REPO_ROOT / "tutorials"
    disk_items = sorted(
        [
            f.name
            for f in tut_dir.iterdir()
            if not f.name.startswith(".") and f.name != "README.md"
        ]
    )

    for item in disk_items:
        pattern = rf"\(\s*{re.escape(item)}(/README\.md)?\s*\)"
        if not re.search(pattern, content):
            issues.append(f"tutorials/README.md: Missing entry for `{item}`")

    lines = content.splitlines()
    new_lines = []
    for line in lines:
        match = re.match(r"^(\s*-\s*\[([^\]]+)\]\(([^)]+)\)\s*—\s*)(.*)", line)
        if match:
            title, link, desc = match.group(2), match.group(3), match.group(4)
            cleaned = clean_text(desc)
            item_key = link.split("/")[0] if "/" in link else link
            if item_key in CURATED_SUMMARIES:
                cleaned = CURATED_SUMMARIES[item_key]

            compliant, reasons = is_compliant(cleaned)
            if not compliant or cleaned != desc:
                issues.append(f"tutorials/README.md [{title}]: {', '.join(reasons or ['Adjusted for compliance'])}")

            if apply_fix:
                new_lines.append(f"- [{title}]({link}) — {cleaned}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if apply_fix:
        for item in disk_items:
            pattern = rf"\(\s*{re.escape(item)}(/README\.md)?\s*\)"
            if not re.search(pattern, "\n".join(new_lines)):
                title = item.replace(".md", "").replace("_", " ").title()
                desc = CURATED_SUMMARIES.get(item, f"Tutorial covering {title}.")
                new_lines.append(f"- [{title}]({item}) — {desc}")
        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return issues


def audit_and_fix_root_readme(apply_fix: bool) -> list[str]:
    """Audits and optionally updates the root README.md index sections."""
    path = TARGET_FILES["root"]
    content = path.read_text(encoding="utf-8")
    issues = []

    sandboxes_dir = REPO_ROOT / "sandboxes"
    disk_sandboxes = sorted(
        [d.name for d in sandboxes_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    )
    for s in disk_sandboxes:
        if f"sandboxes/{s}/README.md" not in content:
            issues.append(f"README.md: Missing sandbox entry for `sandboxes/{s}/README.md`")

    exploit_dir = REPO_ROOT / "exploitation"
    disk_exploits = sorted(
        [d.name for d in exploit_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    )
    for exp in disk_exploits:
        if f"exploitation/{exp}/README.md" not in content:
            issues.append(f"README.md: Missing exploit entry for `exploitation/{exp}/README.md`")

    tut_dir = REPO_ROOT / "tutorials"
    disk_tutorials = sorted(
        [f.name for f in tut_dir.iterdir() if not f.name.startswith(".") and f.name != "README.md"]
    )
    for tut in disk_tutorials:
        target_ref = f"tutorials/{tut}"
        if target_ref not in content and f"{target_ref}/README.md" not in content:
            issues.append(f"README.md: Missing tutorial entry for `{target_ref}`")

    lines = content.splitlines()
    new_lines = []
    in_index_section = False
    i = 0
    current_item = None

    while i < len(lines):
        line = lines[i]

        if line.startswith("## Index of Sub-Projects"):
            in_index_section = True
            new_lines.append(line)
            i += 1
            continue

        if in_index_section and line.startswith("## ") and not line.startswith("## Index"):
            in_index_section = False

        if in_index_section:
            # Check item header: *   **[Title](path)**
            item_match = re.match(r"^\*\s+\*\*\[([^\]]+)\]\(([^)]+)\)\*\*", line)
            if item_match:
                current_item = item_match.group(2)
                new_lines.append(line)
                i += 1
                continue

            # Check if this line is Sub-guides or sub-list (not a summary line)
            if line.strip().startswith("*   **Sub-guides**:") or (line.strip().startswith("*   [") and "Sub-guides" in new_lines[-1] if new_lines else False):
                new_lines.append(line)
                i += 1
                continue

            # Summary lines: either indented paragraph "    [desc]" or legacy bullet subitem "    *   [desc]"
            is_subitem = bool(re.match(r"^\s{2,6}\*\s+(.*)", line)) and not line.strip().startswith("*   **Sub-guides")
            is_indented_p = bool(re.match(r"^\s{4}(?!\*\s)(.*)", line)) and not line.strip().startswith("*   **Sub-guides")

            if (is_subitem or is_indented_p) and current_item:
                if is_subitem:
                    raw_after_bullet = re.match(r"^\s{2,6}\*\s+(.*)", line).group(1)
                else:
                    raw_after_bullet = re.match(r"^\s{4}(.*)", line).group(1)

                cleaned = clean_text(raw_after_bullet)

                # Collect continuation lines
                full_desc = cleaned
                while i + 1 < len(lines) and lines[i + 1].startswith("        ") and not lines[i + 1].strip().startswith("*"):
                    i += 1
                    full_desc += " " + lines[i].strip()

                key = Path(current_item).parts[-2] if current_item and "/" in current_item else (current_item or "")
                if key.endswith(".md"):
                    key = Path(current_item).name

                if key in CURATED_SUMMARIES:
                    full_desc = CURATED_SUMMARIES[key]

                full_desc = clean_text(full_desc)

                # If key has trailing paragraphs/bullet sections (e.g. agent0, semantickernel, langchain, haystack, llamaindex), skip them
                if key in ("agent0", "semantickernel", "langchain", "haystack", "llamaindex"):
                    while (
                        i + 1 < len(lines)
                        and not lines[i + 1].startswith("*   **[")
                        and not lines[i + 1].startswith("### ")
                        and not lines[i + 1].startswith("## ")
                    ):
                        if lines[i + 1].strip().startswith("*   **[") or lines[i + 1].startswith("### ") or lines[i + 1].startswith("## "):
                            break
                        if lines[i + 1].strip() == "" and i + 2 < len(lines) and (lines[i + 2].startswith("*   **[") or lines[i + 2].startswith("### ") or lines[i + 2].startswith("## ")):
                            break
                        i += 1

                compliant, reasons = is_compliant(full_desc)
                has_prefix = bool(PREFIX_REGEX.search(raw_after_bullet))
                has_advisory_ref = bool(NON_STANDARD_ADVISORY_REGEX.search(raw_after_bullet))
                if is_subitem:
                    reasons.append("Formatted as a bullet subitem instead of an indented paragraph")

                if not compliant or has_prefix or has_advisory_ref or is_subitem or full_desc != raw_after_bullet:
                    issues.append(f"README.md [{current_item}]: {', '.join(reasons or ['Adjusted for compliance'])}")

                if apply_fix:
                    new_lines.append(f"    {full_desc}")
                else:
                    new_lines.append(line)
                i += 1
                continue

        new_lines.append(line)
        i += 1

    if apply_fix:
        text_so_far = "\n".join(new_lines)
        if "haystack_orchestration_security_tutorial.md" not in text_so_far:
            entry = (
                "\n*   **[Haystack Orchestration Security Tutorial](tutorials/haystack_orchestration_security_tutorial.md)**\n"
                "    A comprehensive tutorial analyzing Serialization Boundary Evasion in Deepset Haystack "
                "(haystack-ai v2.27.0) and demonstrating persistent RCE via Jinja2 SSTI breakout.\n"
            )
            contrib_idx = next((idx for idx, l in enumerate(new_lines) if l.startswith("## Contribution Guide")), -1)
            if contrib_idx != -1:
                new_lines.insert(contrib_idx, entry)
            else:
                new_lines.append(entry)

        if "recommendation_poisoning" not in text_so_far:
            entry = (
                "\n*   **[Recommendation Memory Poisoning Exploit](exploitation/recommendation_poisoning/README.md)**\n"
                "    A complete, end-to-end example of a recommendation system memory poisoning attack. "
                "Demonstrates how an attacker can manipulate conversational memory to bias subsequent recommendations across user sessions.\n"
            )
            tut_idx = next((idx for idx, l in enumerate(new_lines) if l.startswith("### `tutorials/`")), -1)
            if tut_idx != -1:
                new_lines.insert(tut_idx - 1, entry)
            else:
                new_lines.append(entry)

        path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Audit and synchronize README indexes for compliance.")
    parser.add_argument("--fix", action="store_true", help="Apply fixes and synchronize missing entries.")
    parser.add_argument("--check", action="store_true", help="Audit only and report non-compliant/missing items.")
    args = parser.parse_args()

    apply_fix = args.fix

    all_issues = []
    print("=== House-Cleaning: README Index Audit & Sync ===")
    print(f"Mode: {'FIX (applying changes)' if apply_fix else 'CHECK (audit only)'}\n")

    all_issues.extend(audit_and_fix_sandboxes_readme(apply_fix))
    all_issues.extend(audit_and_fix_exploitation_readme(apply_fix))
    all_issues.extend(audit_and_fix_tutorials_readme(apply_fix))
    all_issues.extend(audit_and_fix_root_readme(apply_fix))

    if all_issues:
        print(f"Found {len(all_issues)} issue(s):")
        for issue in all_issues:
            print(f"  - {issue}")
    else:
        print("All indexes are synchronized and 100% compliant!")

    if apply_fix:
        print("\nFixes applied successfully. Re-running audit to confirm clean state...")
        post_issues = []
        post_issues.extend(audit_and_fix_sandboxes_readme(False))
        post_issues.extend(audit_and_fix_exploitation_readme(False))
        post_issues.extend(audit_and_fix_tutorials_readme(False))
        post_issues.extend(audit_and_fix_root_readme(False))
        if post_issues:
            print(f"\nWarning: {len(post_issues)} remaining issue(s) after fix:")
            for issue in post_issues:
                print(f"  - {issue}")
            sys.exit(1)
        else:
            print("Verification passed! All README files are now compliant.")
            sys.exit(0)
    else:
        sys.exit(1 if all_issues else 0)


if __name__ == "__main__":
    main()
