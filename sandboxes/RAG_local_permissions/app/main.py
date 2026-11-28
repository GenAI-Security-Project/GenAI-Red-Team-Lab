"""RAG permissions sandbox: FastAPI app.

Models a retrieval-augmented assistant with per-user groups, document ACLs,
access revocation, a naive answer cache, and optional content-integrity
verification. The point of the sandbox is to make "respects source
permissions" a testable property, including after revocation.

The `/admin/tamper` endpoint simulates an out-of-band write so the integrity
check has something to catch. It is gated behind RAG_PERMISSIONS_ALLOW_TAMPER=1
and returns 403 unless that variable is set, so the write path is off by
default.
"""

import os
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from app.store import DocumentStore

USERS: Dict[str, str] = {"alice": "group-a", "bob": "group-b"}

SEED_DOCS = [
    {
        "id": "policy-a",
        "text": "Password Policy: all passwords must be at least 12 characters "
        "with uppercase, lowercase, numbers, and special characters. "
        "Change every 90 days.",
        "acl": "group-a",
    },
    {
        "id": "policy-b",
        "text": "Vendor Policy: third-party vendors must complete a yearly "
        "security review before contract renewal.",
        "acl": "group-b",
    },
    {
        "id": "policy-all",
        "text": "Travel Policy: all employees must file travel expenses within "
        "30 days of the trip.",
        "acl": "all",
    },
]

app = FastAPI(title="RAG Permissions Sandbox")
store = DocumentStore()


class ChatState:
    def __init__(self) -> None:
        self.cache_enabled = True
        self.verify_integrity = False
        self.answer_cache: Dict[Any, str] = {}
        self.evidence: List[Dict[str, Any]] = []

    def clear(self) -> None:
        self.cache_enabled = True
        self.verify_integrity = False
        self.answer_cache.clear()
        self.evidence.clear()


state = ChatState()


class Doc(BaseModel):
    id: str
    text: str
    acl: str = "all"
    source: Optional[str] = None


class IngestRequest(BaseModel):
    documents: List[Doc] = Field(default_factory=list)


class QueryRequest(BaseModel):
    query: str
    top_k: int = 3


class RevokeRequest(BaseModel):
    doc_id: str
    acl: str = "revoked"


class TamperRequest(BaseModel):
    doc_id: str
    new_text: str


class ToggleRequest(BaseModel):
    enabled: bool


def _group_of(user: str) -> str:
    group = USERS.get(user)
    if not group:
        raise HTTPException(status_code=401, detail="Unknown user")
    return group


def _record(**fields: Any) -> None:
    fields["ts"] = time.time()
    state.evidence.append(fields)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/admin/reset")
def reset(seed: bool = True) -> Dict[str, Any]:
    store.reset()
    state.clear()
    if seed:
        store.ingest(SEED_DOCS)
    return {"reset": True, "seeded": seed}


@app.post("/admin/ingest")
def ingest(request: IngestRequest) -> Dict[str, int]:
    count = store.ingest([doc.model_dump() for doc in request.documents])
    return {"ingested": count}


@app.post("/admin/revoke")
def revoke(request: RevokeRequest) -> Dict[str, Any]:
    ok = store.set_acl(request.doc_id, request.acl)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"doc_id": request.doc_id, "acl": request.acl}


@app.post("/admin/tamper")
def tamper(request: TamperRequest) -> Dict[str, Any]:
    if os.environ.get("RAG_PERMISSIONS_ALLOW_TAMPER") != "1":
        raise HTTPException(
            status_code=403,
            detail="tamper is disabled; set RAG_PERMISSIONS_ALLOW_TAMPER=1 to enable",
        )
    ok = store.tamper(request.doc_id, request.new_text)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"doc_id": request.doc_id, "tampered": True}


@app.post("/admin/cache")
def set_cache(request: ToggleRequest) -> Dict[str, Any]:
    state.cache_enabled = request.enabled
    if not request.enabled:
        state.answer_cache.clear()
    return {"cache_enabled": state.cache_enabled}


@app.post("/admin/verify")
def set_verify(request: ToggleRequest) -> Dict[str, Any]:
    state.verify_integrity = request.enabled
    return {"verify_integrity": state.verify_integrity}


@app.get("/evidence")
def evidence() -> Dict[str, Any]:
    return {"count": len(state.evidence), "entries": state.evidence}


@app.post("/query")
def query(request: QueryRequest, x_user: str = Header(...)) -> Dict[str, Any]:
    """Retrieval-only endpoint. Returns chunks plus the authorization trail."""
    group = _group_of(x_user)
    matches = store.query(request.query, [group], request.top_k)
    if state.verify_integrity:
        matches = [m for m in matches if m["integrity_ok"]]
    _record(
        kind="query",
        user=x_user,
        group=group,
        query=request.query,
        returned=[m["id"] for m in matches],
        acls={m["id"]: m["acl"] for m in matches},
        integrity={m["id"]: m["integrity_ok"] for m in matches},
    )
    return {
        "user": x_user,
        "group": group,
        "authorized": True,
        "chunks": matches,
    }


@app.post("/chat")
def chat(request: QueryRequest, x_user: str = Header(...)) -> Dict[str, Any]:
    """Chat endpoint with a naive answer cache.

    The generator is stubbed: the answer echoes the retrieved context. This
    keeps the sandbox dependency-free while preserving the property under
    test, namely whether cached answers survive an access revocation.
    """
    group = _group_of(x_user)
    cache_key = (x_user, request.query)

    if state.cache_enabled and cache_key in state.answer_cache:
        answer = state.answer_cache[cache_key]
        _record(
            kind="chat",
            user=x_user,
            group=group,
            query=request.query,
            cache_hit=True,
            answer_chars=len(answer),
        )
        return {"user": x_user, "answer": answer, "cache_hit": True}

    matches = store.query(request.query, [group], request.top_k)
    if state.verify_integrity:
        matches = [m for m in matches if m["integrity_ok"]]
    context = " ".join(m["text"] for m in matches)
    answer = (
        f"According to the retrieved policy: {context}"
        if context
        else "No context found."
    )
    if state.cache_enabled:
        state.answer_cache[cache_key] = answer

    _record(
        kind="chat",
        user=x_user,
        group=group,
        query=request.query,
        cache_hit=False,
        returned=[m["id"] for m in matches],
        answer_chars=len(answer),
    )
    return {
        "user": x_user,
        "answer": answer,
        "cache_hit": False,
        "chunks": matches,
    }
