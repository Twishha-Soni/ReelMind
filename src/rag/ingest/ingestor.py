import hashlib
from datetime import datetime
from qdrant_client.models import PointStruct, SparseVector # type: ignore
from src.rag.database.qdrant_setup import get_vector_store, COLLECTION_NAME, get_client, DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME
from ..util.config import EMBEDDING_MODEL
from src.rag.models.model import VideoAnalysis

def _url_to_id(url: str) -> str:
    """
    Derive a stable, unique ID from a URL using SHA-256 hashing.
    This is your free duplicate detection.
    """
    return int(hashlib.sha256(url.encode()).hexdigest()[:16], 16)

def store_reel(url: str, analysis: VideoAnalysis) -> None:
    vector_store = get_vector_store()

    dense_vector = vector_store.embeddings.embed_quert(analysis.summary)

    keywords_text = " ".join(analysis.keywords)
    sparse_result = vector_store.sparse_embeddings.embed_query(keywords_text)

    point = PointStruct(
        id=_url_to_id(url),
        vector={
            DENSE_VECTOR_NAME: dense_vector,
            SPARSE_VECTOR_NAME: SparseVector(
                indices=sparse_result.indices,
                values=sparse_result.values,
            ),
        },
        payload={
            'url': url,
            'summary': analysis.summary,
            'keywords': analysis.keywords,
            'timestamp': datetime.now().isoformat(timespec='seconds')
        }
    )

    get_client().upsert(collection_name=COLLECTION_NAME, points=[point])    

    print(f"Stored reel: {url}")

def is_already_indexed(url: str) -> bool:
    result = get_client().retrieve(collection_name=COLLECTION_NAME, ids=[_url_to_id(url)])
    return len(result) > 0

def get_stats() -> dict:
    count_result = get_client().count(collection_name=COLLECTION_NAME)
    total = count_result.count

    if total == 0:
        return {
            "total": 0,
            "earliest": None,
            "latest": None
        }
    
    points, _ = get_client().scroll(
        collection_name=COLLECTION_NAME,
        limit=total,
        with_payload=['timestamp']
    )

    timestamps = [p.payload["timestamp"] for p in points]

    return {
        "total": total,
        "earliest": min(timestamps),
        "latest": max(timestamps),
    }