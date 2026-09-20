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

1. **Length & Paragraph Constraint**:
   - The description must be at most **400 characters**.
   - The description must fit into a **single paragraph** with **no line breaks** or nested bullet lists within the summary block.

2. **No Redundant Prefixes**:
   - The description must **not** start with `"Summary:"`, `"**Summary**:"`, or typographical variations (e.g., `"**Sumamary**:"`).
   - If present, remove the prefix entirely while preserving the rest of the text.

3. **Standardized Security Taxonomies Only**:
   - Index summaries should strictly use recognized industry-standard security identifiers (such as **CWE**, **CVE**, **OWASP**, and **MITRE ATLAS**).
   - Omit proprietary tracking codes, private advisory identifiers, and external paper citation clauses from index summaries; reserve detailed citations and disclosures for the sub-project's dedicated README.

4. **Completeness / Synchronization**:
   - Any subdirectories or tutorial documents in `sandboxes/`, `exploitation/`, or `tutorials/` must be cataloged in their respective section index and in the root `README.md`.

---

### Execution Procedures

#### Automated Execution (Recommended)

Use the dedicated Python helper script:

```bash
# 1. Audit compliance and detect missing entries (dry-run / check mode):
python3 .agents/skills/house-cleaning/scripts/clean_readme_indexes.py --check

# 2. Automatically apply fixes, strip prefixes, and insert missing entries:
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

---

## Adding Future Modules

To extend this skill with additional maintenance tasks:
1. Create a helper script in `scripts/<module_name>.py` supporting `--check` and `--fix`.
2. Document the module requirements under a new `## Module <N>: <Name>` section.
3. Add the module to the [Maintenance Checklist](#maintenance-checklist).
