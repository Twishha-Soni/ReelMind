from dataclasses import dataclass
from src.rag.database.qdrant_setup import get_vector_store
from src.rag.util.config import TOP_K_RESULTS

@dataclass
class RetrievedReel:
    url: str
    summary: str
    timestamp: str
    similarity: float

def search_reel(query: str, top_k: int = TOP_K_RESULTS) -> list[RetrievedReel]:
    vector_store = get_vector_store()

    results = vector_store.similarity_search_with_score(query, top_k)

    if not results:
        return []

    top_score = results[0][1]
    
    retrieved = []
    for doc, score in results:
        relative_pct = round((score / top_score) * 100) if top_score > 0 else 0
        retrieved.append(RetrievedReel(
            url=doc.metadata['url'],
            summary=doc.metadata['summary'],
            timestamp=doc.metadata['timestamp'],
            similarity=relative_pct,
        ))

    return retrieved