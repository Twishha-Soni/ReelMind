from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode # type: ignore
from langchain_huggingface import HuggingFaceEmbeddings # type: ignore
from qdrant_client import QdrantClient # type: ignore
from qdrant_client.models import Distance, VectorParams, SparseVectorParams, SparseIndexParams # type: ignore
from rag.util.config import EMBEDDING_MODEL

COLLECTION_NAME = 'reels'
DENSE_VECTOR_NAME = 'dense'
SPARSE_VECTOR_NAME = 'sparse'
DENSE_VECTOR_SIZE = 384
QDRANT_HOST = 'localhost'
QDRANT_PORT = 6333

def get_client() -> QdrantClient:
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

def ensure_collection(client: QdrantClient) -> None:
    """
    Create the 'reels' collection if it doesn't exist yet.
    Safe to call repeatedly — mirrors get_or_create_collection() from ChromaDB.
    """
    existing = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME in existing:
        print(f"Collection '{COLLECTION_NAME}' already exists.")
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            DENSE_VECTOR_NAME: VectorParams(
                size=DENSE_VECTOR_SIZE,
                distance=Distance.COSINE,
            )
        },
        sparse_vectors_config={
            SPARSE_VECTOR_NAME: SparseVectorParams(
                index=SparseIndexParams(on_disk=False)
            )
        }
    )

    print(f"Created collection '{COLLECTION_NAME}' with dense + sparse vectors.")

def get_vector_store(client: QdrantClient) -> QdrantVectorStore:
    """
    The LangChain-wrapped equivalent of everything you did by hand:
    embed dense, embed sparse, build the point, upsert.

    This object is what embedder.py and retriever.py will both use —
    one for add_documents(), the other for similarity_search().
    """
    dense_embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    sparse_embeddings = FastEmbedSparse(model_name='Qdrant/bm25')

    return QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=dense_embeddings,
        sparse_embedding=sparse_embeddings,
        retrieval_mode=RetrievalMode.HYBRID,
        vector_name=DENSE_VECTOR_NAME,
        sparse_vector_name=SPARSE_VECTOR_NAME,
    )