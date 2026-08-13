from dataclasses import dataclass
from rag.database.qdrant_setup import get_client, get_vector_store
from rag.util.config import TOP_K_RESULTS

@dataclass
class RetrievedReel:
    url: str
    summary: str
    timestamp: str
    similarity: float

def search_reel(query: str, top_k: int = TOP_K_RESULTS) -> list[RetrievedReel]:
    vector_store = get_vector_store(get_client())

    results = vector_store.similarity_search_with_score(query, top_k)

    if not results:
        return []

    top_score = results[0][1]
    
    retrieved = []
    print(results)
    for doc, score in results:
        relative_pct = round((score / top_score) * 100) if top_score > 0 else 0
        retrieved.append(RetrievedReel(
            url=doc.metadata['url'],
            summary=doc.page_content,
            timestamp=doc.metadata['timestamp'],
            similarity=relative_pct,
        ))

<<<<<<< Updated upstream
    print('Retrieved related content from your database.')
=======
    print('Retrieved related content from your database.\n')
>>>>>>> Stashed changes
    return retrieved