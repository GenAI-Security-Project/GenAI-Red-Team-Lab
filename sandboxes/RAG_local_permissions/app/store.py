"""Vector store wrapper for the permissions sandbox.

Uses a local ChromaDB collection with string metadata only, so the sandbox
runs without Ollama or any external embedding service. Embeddings are a
deterministic hashed bag of words: good enough to test retrieval scoping,
permissions, cache behaviour, and integrity checks, without model downloads.
"""

import hashlib
import math
import threading
from typing import Any, Dict, List, Optional

import chromadb

EMBED_DIM = 256
ACL_ALL = "all"
ACL_REVOKED = "revoked"


def embed(text: str) -> List[float]:
    """Deterministic hashed bag-of-words embedding."""
    vec = [0.0] * EMBED_DIM
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:8]
        vec[int(digest, 16) % EMBED_DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DocumentStore:
    """Chroma-backed store with per-document ACL metadata and hashes."""

    def __init__(self, path: str = "./data/chromadb") -> None:
        self._client = chromadb.PersistentClient(path=path)
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            try:
                self._client.delete_collection("documents")
            except Exception:
                pass
            self._collection = self._client.get_or_create_collection("documents")

    def ingest(self, docs: List[Dict[str, Any]]) -> int:
        """Ingest documents with an ACL label. Each doc: id, text, acl."""
        with self._lock:
            ids, texts, embeddings, metadatas = [], [], [], []
            for doc in docs:
                text = doc["text"]
                ids.append(doc["id"])
                texts.append(text)
                embeddings.append(embed(text))
                metadatas.append(
                    {
                        "text": text,
                        "acl": doc.get("acl", ACL_ALL),
                        "source": doc.get("source", "synthetic"),
                        "sha256": sha256_of(text),
                    }
                )
            self._collection.upsert(
                ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas
            )
            return len(ids)

    def _get_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        res = self._collection.get(ids=[doc_id], include=["metadatas"])
        metas = res.get("metadatas") or []
        return metas[0] if metas else None

    def set_acl(self, doc_id: str, acl: str) -> bool:
        """Set a document's ACL label. Revocation is acl='revoked'."""
        with self._lock:
            meta = self._get_metadata(doc_id)
            if not meta:
                return False
            meta = dict(meta)
            meta["acl"] = acl
            self._collection.update(ids=[doc_id], metadatas=[meta])
            return True

    def tamper(self, doc_id: str, new_text: str) -> bool:
        """Replace stored text without updating the recorded hash.

        Simulates a write that bypasses the ingestion path (for example a
        direct vector DB write). The stored sha256 no longer matches.
        """
        with self._lock:
            res = self._collection.get(
                ids=[doc_id], include=["metadatas", "embeddings"]
            )
            metas = res.get("metadatas") or []
            embeddings = res.get("embeddings")
            if not metas or embeddings is None:
                return False
            meta = dict(metas[0])
            meta["text"] = new_text
            self._collection.update(
                ids=[doc_id],
                embeddings=[list(embeddings[0])],
                documents=[new_text],
                metadatas=[meta],
            )
            return True

    def query(
        self, text: str, groups: List[str], top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Query with an ACL filter applied inside the store."""
        allowed = [g for g in groups if g] + [ACL_ALL]
        with self._lock:
            res = self._collection.query(
                query_embeddings=[embed(text)],
                n_results=top_k,
                where={"acl": {"$in": allowed}},
                include=["metadatas", "distances", "documents"],
            )
        matches: List[Dict[str, Any]] = []
        ids = res.get("ids") or [[]]
        for i, doc_id in enumerate(ids[0]):
            meta = (res.get("metadatas") or [[{}]])[0][i] or {}
            dist = (res.get("distances") or [[0.0]])[0][i]
            matches.append(
                {
                    "id": doc_id,
                    "score": 1.0 - float(dist),
                    "acl": meta.get("acl"),
                    "text": meta.get("text", ""),
                    "sha256": meta.get("sha256"),
                    "integrity_ok": meta.get("sha256")
                    == sha256_of(meta.get("text", "")),
                }
            )
        return matches
