from pathlib import Path
import hashlib
from typing import Any, Dict, Iterable, List, Optional

from app.core.config import get_settings
from app.rag.embeddings import deterministic_embedding


class MilvusLiteKnowledgeStore:
    collection_name = "knowledge_chunks"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.dim = self.settings.embedding_dim
        self.client = self._create_client()
        self._ensure_collection()

    @classmethod
    def enabled(cls) -> bool:
        return get_settings().vector_store in {"milvus", "milvus_lite"}

    def upsert_documents(self, docs: List[Dict[str, Any]]) -> None:
        if not docs:
            return

        rows = []
        for doc in docs:
            source = str(doc["source"])
            content = str(doc["content"])
            rows.append(
                {
                    "id": self._stable_id(source),
                    "vector": deterministic_embedding(f"{doc['title']}\n{content}", self.dim),
                    "title": str(doc["title"])[:512],
                    "domain": str(doc["domain"])[:80],
                    "doc_type": str(doc["doc_type"])[:80],
                    "source": source[:512],
                    "content": content[:8000],
                }
            )
        self.client.upsert(collection_name=self.collection_name, data=rows)

    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        doc_types: Optional[Iterable[str]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        filters = []
        if domain:
            filters.append(f'domain in ["{domain}", "general"]')
        if doc_types:
            quoted = ", ".join(f'"{item}"' for item in doc_types)
            filters.append(f"doc_type in [{quoted}]")
        filter_expr = " and ".join(filters) if filters else ""
        results = self.client.search(
            collection_name=self.collection_name,
            data=[deterministic_embedding(query, self.dim)],
            filter=filter_expr,
            limit=top_k,
            output_fields=["title", "domain", "doc_type", "source", "content"],
        )
        return [
            {
                "title": item["entity"]["title"],
                "domain": item["entity"]["domain"],
                "doc_type": item["entity"]["doc_type"],
                "source": item["entity"]["source"],
                "score": round(float(item.get("distance", 0.0)), 4),
                "content": item["entity"]["content"][:1200],
            }
            for item in (results[0] if results else [])
        ]

    def _create_client(self):
        from pymilvus import MilvusClient

        uri = self.settings.milvus_uri if self.settings.vector_store == "milvus" else self.settings.milvus_lite_uri
        if self.settings.vector_store == "milvus_lite":
            Path(uri).parent.mkdir(parents=True, exist_ok=True)
        kwargs = {"uri": uri}
        if self.settings.milvus_token:
            kwargs["token"] = self.settings.milvus_token
        return MilvusClient(**kwargs)

    def _ensure_collection(self) -> None:
        if self.client.has_collection(self.collection_name):
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            dimension=self.dim,
            metric_type="COSINE",
            auto_id=False,
        )

    def _stable_id(self, source: str) -> int:
        digest = hashlib.sha256(source.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big") % (2**63)
