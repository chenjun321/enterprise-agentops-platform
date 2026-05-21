import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import KnowledgeDocument


TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+")


def tokenize(text: str) -> List[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def score_text(query: str, text: str) -> float:
    q_tokens = set(tokenize(query))
    t_tokens = tokenize(text)
    token_score = 0.0
    if q_tokens and t_tokens:
        overlap = sum(1 for token in t_tokens if token in q_tokens)
        token_score = overlap / max(len(q_tokens), 1)

    q_chars = {char for char in query if "\u4e00" <= char <= "\u9fff"}
    t_chars = {char for char in text if "\u4e00" <= char <= "\u9fff"}
    char_score = len(q_chars & t_chars) / max(len(q_chars), 1) if q_chars else 0.0
    return max(token_score, char_score)


class SimpleKnowledgeIndexer:
    """Small local RAG indexer.

    This keeps the demo runnable without external vector services. The boundary is
    intentionally compatible with replacing internals by LlamaIndex later.
    """

    def __init__(self, db: Session):
        self.db = db

    def index_directory(self, docs_dir: str) -> int:
        count = 0
        indexed_docs = []
        for path in Path(docs_dir).glob("*.md"):
            text = path.read_text(encoding="utf-8")
            metadata = self._parse_frontmatter(text)
            content = self._strip_frontmatter(text)
            doc = {
                "title": metadata.get("title", path.stem),
                "domain": metadata.get("domain", "general"),
                "doc_type": metadata.get("doc_type", "document"),
                "source": str(path),
                "content": content,
            }
            existing = self.db.execute(
                select(KnowledgeDocument).where(KnowledgeDocument.source_path == str(path))
            ).scalar_one_or_none()
            if existing:
                existing.content = doc["content"]
                existing.title = doc["title"]
                existing.domain = doc["domain"]
                existing.doc_type = doc["doc_type"]
            else:
                self.db.add(
                    KnowledgeDocument(
                        title=doc["title"],
                        domain=doc["domain"],
                        doc_type=doc["doc_type"],
                        permission_level=metadata.get("permission_level", "employee"),
                        source_path=doc["source"],
                        version=metadata.get("version", "v1"),
                        content=doc["content"],
                    )
                )
            indexed_docs.append(doc)
            count += 1
        self.db.commit()
        self._sync_vector_store(indexed_docs)
        return count

    def _sync_vector_store(self, docs: List[Dict[str, str]]) -> None:
        if get_settings().vector_store not in {"milvus", "milvus_lite"}:
            return
        try:
            from app.rag.milvus_lite_adapter import MilvusLiteKnowledgeStore

            MilvusLiteKnowledgeStore().upsert_documents(docs)
        except Exception:
            return

    def _parse_frontmatter(self, text: str) -> Dict[str, str]:
        if not text.startswith("---"):
            return {}
        parts = text.split("---", 2)
        if len(parts) < 3:
            return {}
        metadata = {}
        for line in parts[1].splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
        return metadata

    def _strip_frontmatter(self, text: str) -> str:
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) == 3:
                return parts[2].strip()
        return text.strip()


class SimpleKnowledgeRetriever:
    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        doc_types: Optional[Iterable[str]] = None,
        top_k: int = 5,
    ) -> List[Dict]:
        stmt = select(KnowledgeDocument)
        if domain:
            stmt = stmt.where(KnowledgeDocument.domain.in_([domain, "general"]))
        if doc_types:
            stmt = stmt.where(KnowledgeDocument.doc_type.in_(list(doc_types)))
        docs = self.db.execute(stmt).scalars().all()
        if get_settings().vector_store in {"milvus", "milvus_lite"}:
            try:
                from app.rag.milvus_lite_adapter import MilvusLiteKnowledgeStore

                vector_results = MilvusLiteKnowledgeStore().search(query, domain, doc_types, top_k)
                if vector_results:
                    return vector_results
            except Exception:
                pass
        scored = []
        for doc in docs:
            score = score_text(query, f"{doc.title}\n{doc.content}")
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "title": doc.title,
                "domain": doc.domain,
                "doc_type": doc.doc_type,
                "source": doc.source_path,
                "score": round(score, 4),
                "content": doc.content[:1200],
            }
            for score, doc in scored[:top_k]
        ]
