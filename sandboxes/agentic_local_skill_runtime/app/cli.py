"""Run one skill against the local runtime and emit a JSON trace."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .agent import run_agent
from .model_backends import HttpModel, ScriptedModel
from .models import Defense
from .skills_loader import load_skill
from .tools import SECRET_SENTINEL, Allowlist, ToolRegistry


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skill-dir", required=True, help="directory containing SKILL.md"
    )
    parser.add_argument("--skill-file", default="SKILL.md", help="skill markdown filename")
    parser.add_argument(
        "--defense",
        choices=[defense.value for defense in Defense],
        default=Defense.NONE.value,
    )
    parser.add_argument("--backend", choices=("scripted", "http"), default="scripted")
    parser.add_argument("--base-url", default="http://localhost:11434/v1")
    parser.add_argument("--model", default="llama3.1:8b")
    parser.add_argument("--api-key", default="not-needed")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    data_dir = args.data_dir.resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    secret_file = data_dir / ".env"
    if not secret_file.exists():
        secret_file.write_text(
            f"SECRET_TOKEN={SECRET_SENTINEL}\nDB_PASSWORD=synthetic-sentinel-placeholder\n",
            encoding="utf-8",
        )

    defense = Defense(args.defense)
    target_file = data_dir / "data.csv"
    allowlist = Allowlist()
    if defense == Defense.TOOL_ALLOWLIST:
        allowlist = Allowlist(
            allowed_tools={"read_file", "write_file"},
            read_roots=[str(target_file)],
        )
    model = (
        ScriptedModel()
        if args.backend == "scripted"
        else HttpModel(args.base_url, args.model, api_key=args.api_key)
    )
    skill = load_skill(args.skill_dir, md_name=args.skill_file)
    trace = run_agent(skill, model, ToolRegistry(data_dir, allowlist), defense)
    result = asdict(trace)
    result["defense"] = trace.defense.value
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
