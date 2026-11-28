"""Benign payload for the ChromaDB config-ordering sandbox.

This module executes when transformers dynamically imports remote code from
the model directory (trust_remote_code=True). It writes a marker file and
does nothing else: no network calls, no shell, no persistence.

The point is to prove execution order: the marker exists even when the HTTP
request that triggered the model load is rejected with 403.
"""

import datetime
import json
import os

from transformers import PreTrainedModel

MARKER_PATH = os.environ.get("MARKER_PATH", "/evidence/marker.json")


def _write_marker() -> None:
    try:
        os.makedirs(os.path.dirname(MARKER_PATH), exist_ok=True)
        with open(MARKER_PATH, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "module": __file__,
                    "pid": os.getpid(),
                    "utc": datetime.datetime.now(datetime.UTC).isoformat(),
                },
                handle,
            )
    except Exception:
        pass


_write_marker()


class BenignModel(PreTrainedModel):
    """Stub so dynamic loading can resolve the class after the marker write."""
