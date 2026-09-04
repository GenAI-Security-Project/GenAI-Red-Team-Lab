#!/usr/bin/env python3
"""
OWASP GenAI Red Team Lab - Haystack Serialization Evasion Sandbox
Target: haystack-ai==2.27.0
Vulnerability: unsafe flag bypass via from_dict()/from_yaml()
Reference: JDP-2026-005
"""

import json
from pathlib import Path
from typing import Any, Dict

import uvicorn
import yaml
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from haystack import Pipeline

app = FastAPI(title="Haystack Serialization Evasion Sandbox")


def get_version() -> str:
    """Return the installed haystack-ai version."""
    try:
        import haystack

        return haystack.__version__
    except Exception:
        return "unknown"


@app.get("/health")
def health():
    return {"status": "ok", "haystack_version": get_version()}


@app.get("/verify")
def verify():
    """Check if framework has been compromised by searching for markers."""
    try:
        import haystack

        init_path = Path(haystack.__file__).resolve()
        content = init_path.read_text()
        markers = [
            "NUKA-AI",
            "SCOPE CHANGE",
            "CRITICAL COMPROMISE",
            "HAYSTACK SCOPE CHANGE",
        ]
        found = [m for m in markers if m.lower() in content.lower()]
        return {
            "status": "compromised" if found else "clean",
            "haystack_version": get_version(),
            "init_file": str(init_path),
            "markers_found": found,
        }
    except Exception as e:
        return JSONResponse({"error": str(e), "status": "error"})


@app.post("/chat")
async def chat(request: Request):
    """Simulate an agent that can load pipelines or read files."""
    try:
        body = await request.json()
        query = body.get("query", "")
        action, action_input = parse_query(query)
        if action == "load_pipeline":
            result = handle_load_pipeline(action_input)
            return JSONResponse({"output": result})
        elif action == "read_file":
            result = handle_read_file(action_input)
            return JSONResponse({"output": result})
        else:
            return JSONResponse(
                {"output": "Unknown action. Use load_pipeline or read_file."}
            )
    except Exception as e:
        return JSONResponse({"output": f"[ERROR] {str(e)}"})


def parse_query(query: str):
    """
    Parse a query string of the form:
    Action: load_pipeline
    Action Input: {"path": "/tmp/exploit.yaml"}

    Returns (action, action_input_dict)
    """
    lines = query.strip().split("\n")
    action = "unknown"
    action_input = {}
    for line in lines:
        if line.startswith("Action:"):
            action = line.split(":", 1)[1].strip()
        elif line.startswith("Action Input:"):
            input_str = line.split(":", 1)[1].strip()
            try:
                action_input = json.loads(input_str)
            except json.JSONDecodeError:
                try:
                    action_input = yaml.safe_load(input_str)
                except yaml.YAMLError:
                    action_input = {"path": input_str.strip()}
    return action, action_input


def handle_load_pipeline(action_input: Dict[str, Any]) -> str:
    """
    Load a pipeline from a path, a pipeline dict, or a YAML string.
    Executes the pipeline, passing the required 'trigger' input to the adapter.
    """
    # Case 1: Load from file path
    if "path" in action_input:
        path = action_input["path"]
        resolved_path = Path(path).resolve()
        if not resolved_path.exists():
            return f"[ERROR] File not found: {path}"
        try:
            # Correct method: Pipeline.load_from_yaml (not from_yaml)
            pipe = Pipeline.load_from_yaml(str(resolved_path))
            result = pipe.run(data={"adapter": {"trigger": "fire"}})
            return f"Pipeline loaded and executed. Result: {result}"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    # Case 2: Load from a pipeline dictionary
    elif "pipeline" in action_input:
        pipeline_data = action_input["pipeline"]
        try:
            if isinstance(pipeline_data, str):
                pipeline_dict = yaml.safe_load(pipeline_data)
            else:
                pipeline_dict = pipeline_data
            pipe = Pipeline.from_dict(pipeline_dict)
            result = pipe.run(data={"adapter": {"trigger": "fire"}})
            return f"Pipeline loaded and executed. Result: {result}"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    # Case 3: Load from a YAML string directly
    elif "yaml" in action_input:
        try:
            # Correct method: Pipeline.from_string (not from_dict on raw YAML)
            pipe = Pipeline.from_string(action_input["yaml"])
            result = pipe.run(data={"adapter": {"trigger": "fire"}})
            return f"Pipeline loaded and executed. Result: {result}"
        except Exception as e:
            return f"[ERROR] {str(e)}"

    else:
        return "[ERROR] No valid pipeline input. Use 'path', 'pipeline', or 'yaml'."


def handle_read_file(action_input: Dict[str, Any]) -> str:
    """Read a file from the container filesystem (used for post-exploitation checks)."""
    path = action_input.get("path", "")
    resolved_path = Path(path).resolve()
    if not resolved_path.exists():
        return f"[ERROR] File not found: {path}"
    try:
        return resolved_path.read_text()
    except Exception as e:
        return f"[ERROR] {str(e)}"


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
