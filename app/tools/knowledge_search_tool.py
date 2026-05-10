from typing import Any, Dict

from sqlalchemy.orm import Session

from app.rag.simple_retriever import SimpleKnowledgeRetriever
from app.tools.base import BaseTool, ToolResult


class KnowledgeSearchTool(BaseTool):
    name = "KnowledgeSearchTool"
    description = "Search internal knowledge docs: FAQ, runbooks, metric definitions, sales playbooks."

    def __init__(self, db: Session):
        self.retriever = SimpleKnowledgeRetriever(db)

    def run(self, payload: Dict[str, Any]) -> ToolResult:
        chunks = self.retriever.search(
            query=payload.get("query", ""),
            domain=payload.get("domain"),
            doc_types=payload.get("doc_types"),
            top_k=int(payload.get("top_k", 5)),
        )
        return ToolResult(ok=True, data={"chunks": chunks})

