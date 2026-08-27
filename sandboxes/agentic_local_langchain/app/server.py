#!/usr/bin/env python3
"""
======================================================================================
         LangChain Exploit Lab - Mock AI Agent Server (OWASP GenAI Red Team)
======================================================================================
  This server simulates an AI agent with tools: document_reader and file_writer.
  The LLM orchestration step is SIMULATED in the trainer to provide deterministic
  results. The actual framework calls use REAL langchain-core library versions.

  Version Compatibility:
    Stage 0 - 1.2.24: VULNERABLE - No path validation at all
    Stage 1 - 1.2.25: PARTIALLY PATCHED - Read-side patched (PR #36471)
                      CVE-2026-34070 blocked, CVE-2023-36258 still works via symlink
    Stage 2 - 1.2.26: FULLY PATCHED (read side) - Both CVEs blocked for reads
    Stage 3 - 1.2.27: POST-FIX - PR #36585 applied, but write still exposed
    Stage 4 - latest: LATEST RELEASE - Auto-detected from PyPI at build time
======================================================================================
"""

import json
import os
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Try to import langchain_core
try:
    import langchain_core
    from langchain_core.prompts import PromptTemplate
    from langchain_core.prompts.loading import load_prompt_from_config

    LANGCHAIN_CORE_VERSION = langchain_core.__version__
except ImportError:
    LANGCHAIN_CORE_VERSION = "not_installed"

# Determine langchain-core version for behavior
LC_VERSION_TUPLE = (
    tuple(
        int(x)
        for x in LANGCHAIN_CORE_VERSION.split(".")[:3]
        if x.replace(".", "").isdigit()
    )
    if LANGCHAIN_CORE_VERSION != "not_installed"
    else (0, 0, 0)
)

SANDBOX_DIR = Path("/app/sandbox_data")
SAFE_DIR = Path("/app/SafeFolder")
DATA_DIR = Path("/app/data")
SAFE_DIR.mkdir(parents=True, exist_ok=True)


def handle_document_reader(target_path_str):
    """
    Simulates an agent tool that reads file contents via langchain-core.

    Version-specific behavior:
      1.2.24: VULNERABLE - No path validation. Direct read with os.path.realpath.
      1.2.25: PARTIALLY PATCHED - Uses load_prompt_from_config with
              allow_dangerous_paths=False. CVE-2026-34070 blocked.
              CVE-2023-36258 still works via .txt symlink bypass.
      1.2.26+: FULLY PATCHED - Symlinks resolved before extension check.
              Both CVEs blocked for reads.
    """
    try:
        # Generate unique symlink name to prevent race conditions
        symlink_name = f"exploit_bypass_{uuid.uuid4().hex[:8]}.txt"
        target_path = Path(target_path_str)

        if LC_VERSION_TUPLE < (1, 2, 25):
            # Stage 0: 1.2.24 - No path validation at all
            resolved = target_path.resolve()
            if resolved.exists():
                with open(resolved, "r") as f:
                    return f.read()
            return f"[ERROR] File not found: {resolved}"

        elif LC_VERSION_TUPLE < (1, 2, 26):
            # Stage 1: 1.2.25 - Read-side partially patched
            # CVE-2026-34070 blocked, but CVE-2023-36258 still works via symlink
            if os.path.exists(symlink_name):
                os.remove(symlink_name)
            os.symlink(str(target_path.resolve()), symlink_name)

            config = {
                "_type": "prompt",
                "template_path": symlink_name,
                "template_format": "f-string",
                "input_variables": [],
            }
            try:
                result = load_prompt_from_config(config, allow_dangerous_paths=False)
                return result.template
            except ValueError as e:
                return f"[BLOCKED] ValueError: {str(e)}"
            finally:
                if os.path.exists(symlink_name):
                    os.remove(symlink_name)

        else:
            # Stage 2+: 1.2.26+ - Both CVEs fully patched on read side
            if os.path.exists(symlink_name):
                os.remove(symlink_name)
            os.symlink(str(target_path.resolve()), symlink_name)

            config = {
                "_type": "prompt",
                "template_path": symlink_name,
                "template_format": "f-string",
                "input_variables": [],
            }
            try:
                result = load_prompt_from_config(config, allow_dangerous_paths=False)
                return result.template
            except ValueError as e:
                return f"[BLOCKED] ValueError: {str(e)}"
            finally:
                if os.path.exists(symlink_name):
                    os.remove(symlink_name)

    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {str(e)}"


def handle_file_writer(target_path_str, content):
    """
    Simulates an agent tool that writes file contents via langchain-core.

    Uses PromptTemplate.save() which writes .json or .yaml files.
    The write primitive is STILL EXPOSED in ALL versions.
    PR #36585 only checks resolved file extension, NOT write destination.
    """
    try:
        # Generate unique symlink name to prevent race conditions
        symlink_name = f"exploit_{uuid.uuid4().hex[:8]}.json"
        target_path = Path(target_path_str)

        if target_path.suffix in (".json", ".yaml", ".yml"):
            prompt = PromptTemplate(template=content, input_variables=[])
            prompt.save(str(target_path))
            return f"SUCCESS: Content successfully written to {target_path_str}"
        else:
            # For non-.json paths, use symlink technique
            if os.path.exists(symlink_name):
                os.remove(symlink_name)
            os.symlink(str(target_path.resolve()), symlink_name)

            prompt = PromptTemplate(template=content, input_variables=[])
            prompt.save(symlink_name)

            if os.path.exists(symlink_name):
                os.remove(symlink_name)

            return f"SUCCESS: Content successfully written to {target_path_str}"

    except Exception as e:
        return f"[ERROR] {type(e).__name__}: {str(e)}"


class AgentHandler(BaseHTTPRequestHandler):
    """HTTP handler for the mock AI agent server."""

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "status": "ok",
                        "langchain_core_version": LANGCHAIN_CORE_VERSION,
                        "sandbox_dir": str(SANDBOX_DIR),
                    }
                ).encode()
            )
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())

    def do_POST(self):
        if self.path == "/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")

            try:
                data = json.loads(body)
                query = data.get("query", "")
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
                return

            # Parse the query for tool calls
            result = None
            if "Action: document_reader" in query:
                import re

                match = re.search(r'Action Input: \{"path": "([^"]+)"\}', query)
                if match:
                    path = match.group(1)
                    result = handle_document_reader(path)
                else:
                    result = "[ERROR] Could not parse path from document_reader input"

            elif "Action: file_writer" in query:
                import re

                path_match = re.search(r'Action Input: \{"path": "([^"]+)"', query)
                content_match = re.search(r'"content": "([^"]+)"', query)
                if path_match and content_match:
                    path = path_match.group(1)
                    content = content_match.group(1)
                    result = handle_file_writer(path, content)
                else:
                    result = (
                        "[ERROR] Could not parse path/content from file_writer input"
                    )

            else:
                result = "[ERROR] Unknown action"

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"output": result}).encode())

        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())


def main():
    port = 8000
    server = HTTPServer(("0.0.0.0", port), AgentHandler)
    print(f"[*] Server listening on port {port}")
    print(f"[*] langchain-core version: {LANGCHAIN_CORE_VERSION}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
