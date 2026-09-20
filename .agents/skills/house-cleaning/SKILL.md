---
name: house-cleaning
description: >-
  Performs repository maintenance, documentation consistency audits, index synchronization,
  and project hygiene tasks. Use whenever auditing, updating, or maintaining repository structure,
  documentation indexes, or enforcing formatting compliance across project assets.
---

# House Cleaning Skill

This skill provides procedures and automated tooling to maintain repository health, documentation integrity, and structural consistency across the codebase.

It is designed with an extensible, modular structure to accommodate incremental maintenance routines over time without requiring updates to the skill definition itself.

---

## Skill Architecture & Extensibility

Maintenance routines are organized into discrete **Modules**. When introducing new house-cleaning tasks in the future:
1. Add a new **Module Section** in this file outlining the rules, targets, and expected outcomes.
2. (Optional) Add an automated utility under [`scripts/`](./scripts/) implementing `--check` (audit/dry-run) and `--fix` (apply changes) modes.
3. Update the [Maintenance Checklist](#maintenance-checklist) below.

---

## Maintenance Checklist

- [ ] **Module 1: README Index Synchronization & Compliance** (Active)
- [ ] **Module 2: Dead Link & Relative Path Verification** (Planned)
- [ ] **Module 3: Sandbox & Tool Metadata Validation** (Planned)
- [ ] **Module 4: Temporary & Scratch Artifact Cleanup** (Planned)

---

## Module 1: README Index Synchronization & Compliance

### Scope & Target Files

The following README files maintain indexes of sub-projects, sandboxes, exploits, or tutorials:
- [`README.md`](../../README.md) (Root index)
- [`exploitation/README.md`](../../exploitation/README.md)
- [`sandboxes/README.md`](../../sandboxes/README.md)
- [`tutorials/README.md`](../../tutorials/README.md)

### Compliance Rules for Index Entries

Every indexed item across all target README files must adhere to the following rules:

1. **Format & Structural Layout**:
   - Each directory entry must be an item followed by a line break and an **indented paragraph** (not a subitem):
     ```markdown
     *   **`dir_name/`** (or `*   **[Title](path)**`)

         [Indented summary paragraph]
     ```
   - **Line Break**: Include a blank line between the item header and the indented summary paragraph for clean visual separation.
   - **Not a subitem**: The summary must **never** be a bulleted subitem (do not use `*   summary` or `-   summary`). It must be an indented paragraph belonging to the parent list item.

2. **Length & Paragraph Constraint**:
   - The description must be at most **400 characters**.
   - The description must fit into a **single paragraph** with **no line breaks** or nested bullet lists within the summary block.

3. **No Redundant Prefixes**:
   - The description must **not** start with `"Summary:"`, `"**Summary**:"`, or typographical variations (e.g., `"**Sumamary**:"`).
   - If present, remove the prefix entirely while preserving the rest of the text.

4. **Standardized Security Taxonomies Only**:
   - Index summaries should strictly use recognized industry-standard security identifiers (such as **CWE**, **CVE**, **OWASP**, and **MITRE ATLAS**).
   - Omit proprietary tracking codes, private advisory identifiers, and external paper citation clauses from index summaries; reserve detailed citations and disclosures for the sub-project's dedicated README.

5. **Completeness / Synchronization**:
   - Any subdirectories or tutorial documents in `sandboxes/`, `exploitation/`, or `tutorials/` must be cataloged in their respective section index and in the root `README.md`.

6. **Directory Structure Tree Synchronization**:
   - The `## Directory Structure` code block in the root [`README.md`](../../README.md) must accurately reflect the repository layout up to depth 2 (including all sub-projects in `exploitation/`, `sandboxes/`, and tutorials/files in `tutorials/`).
   - The tree must be kept up to date whenever new directories, sandboxes, exploits, or tutorials are added, renamed, or deleted.
   - Standard format: Case-insensitive alphabetical sorting, standard tree glyphs (`├──`, `└──`, `│   `), excluding hidden files/directories (`.*`), caches (`__pycache__`), and virtual environments.

---

### Execution Procedures

#### Automated Execution (Recommended)

Use the dedicated Python helper script:

```bash
# 1. Audit compliance, missing entries, and directory structure tree (dry-run / check mode):
python3 .agents/skills/house-cleaning/scripts/clean_readme_indexes.py --check

# 2. Automatically apply fixes, strip prefixes, insert missing entries, and synchronize tree:
python3 .agents/skills/house-cleaning/scripts/clean_readme_indexes.py --fix
```

#### Manual Verification Procedure

When auditing or adjusting entries manually:

1. **Verify Sandbox Index**:
   - List subdirectories in `sandboxes/`.
   - Ensure each sandbox is present in both `sandboxes/README.md` and `README.md` under `### sandboxes/`.
   - Ensure descriptions are $\le 400$ characters, single paragraph, without `Summary:` prefix.

2. **Verify Exploitation Index**:
   - List subdirectories in `exploitation/`.
   - Ensure each exploit is present in both `exploitation/README.md` and `README.md` under `### exploitation/`.
   - Ensure descriptions are $\le 400$ characters, single paragraph, without `Summary:` prefix.

3. **Verify Tutorials Index**:
   - List `.md` files and subdirectories in `tutorials/` (excluding `README.md`).
   - Ensure each tutorial is present in both `tutorials/README.md` and `README.md` under `### tutorials/`.
   - Ensure descriptions are $\le 400$ characters, single paragraph, without `Summary:` prefix.

4. **Verify Root Directory Structure Tree**:
   - Verify that the `## Directory Structure` text block in root `README.md` accurately reflects all current files and subdirectories in `exploitation/`, `sandboxes/`, and `tutorials/`.
   - Ensure the tree is sorted alphabetically (case-insensitive) using standard tree glyphs (`├──`, `└──`, `│   `).

---

## Adding Future Modules

To extend this skill with additional maintenance tasks:
1. Create a helper script in `scripts/<module_name>.py` supporting `--check` and `--fix`.
2. Document the module requirements under a new `## Module <N>: <Name>` section.
3. Add the module to the [Maintenance Checklist](#maintenance-checklist).
