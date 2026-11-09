# Agentic Local Skill Runtime

A standard-library, in-process target runtime for agent skill evaluations. It
loads `SKILL.md` instructions, runs an agent/tool loop against a scripted or
OpenAI-compatible model, and constrains file reads to `data/`. Shell calls are
recorded only; no command is executed. The target CSV is synthetic, and the
credential sentinel is created locally at runtime and ignored by Git.

## Layout

- `app/agent.py` — agent loop and defensive system prompt.
- `app/tools.py` — file access, tool allowlists, and record-only shell tool.
- `app/skills_loader.py` — `SKILL.md` loader and instruction extraction.
- `app/model_backends.py` — deterministic and HTTP model adapters.
- `app/models.py` — shared runtime and evaluation data models.
- `data/data.csv` — synthetic target file; `data/.env` is generated on demand.
- `tests/` — filesystem boundary and record-only tool tests.

## Use

```sh
make build
make test-unit
make attack
```

The attack target delegates to
[`exploitation/agentic_skill_poisoning/`](../../exploitation/agentic_skill_poisoning/README.md).
See that module for the synthetic corpus, defenses, scoring, and reports.
