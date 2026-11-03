"""Tool-definition digests.

A digest pins the exact tool definition a user approved. It is computed over
canonical JSON of the definition as received from the MCP server, with the
top-level ``_meta`` object removed (the MCP specification reserves ``_meta`` for
protocol and implementation metadata, so a client may reasonably exclude it).

The invariant the lab teaches is: every field rendered to the model must be
covered by the digest. ``_meta`` is safe to exclude only while the gateway never
renders it (see ``app.gateway.render``).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

EXCLUDED_FROM_DIGEST = frozenset({"_meta"})


def canonical_json(value: Any) -> str:
    """Serialise ``value`` deterministically.

    Sorted keys, no insignificant whitespace, UTF-8 preserved. This is close to
    RFC 8785 for the string/object/array/bool/integer values that appear in tool
    definitions; it does not normalise floating-point numbers.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_input(tool: dict[str, Any]) -> dict[str, Any]:
    """Return the part of a tool definition that the digest covers."""
    return {key: val for key, val in tool.items() if key not in EXCLUDED_FROM_DIGEST}


def tool_digest(tool: dict[str, Any]) -> str:
    """Return ``sha256:<hex>`` over the canonical definition without ``_meta``."""
    payload = canonical_json(digest_input(tool)).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()
