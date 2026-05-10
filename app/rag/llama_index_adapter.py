from typing import Any, Dict, List


class LlamaIndexKnowledgeAdapter:
    """Production extension point for LlamaIndex.

    The project uses SimpleKnowledgeRetriever by default so the graduation demo
    can run locally without vector database setup. Replace that retriever with
    this adapter when you add LlamaIndex, embeddings, metadata filters, and a
    vector store such as pgvector, Qdrant, or Chroma.
    """

    def __init__(self, *_: Any, **__: Any) -> None:
        self.enabled = False

    def search(self, query: str, domain: str, doc_types: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        raise NotImplementedError(
            "Install llama-index extras and wire this adapter to a VectorStoreIndex."
        )

