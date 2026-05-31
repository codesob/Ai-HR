from functools import lru_cache

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from shared.core.config import get_settings

COLLECTION_RESUMES = "resumes"
COLLECTION_JOBS = "jobs"
COLLECTION_KNOWLEDGE = "hr_knowledge"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2


@lru_cache
def get_encoder() -> SentenceTransformer:
    settings = get_settings()
    return SentenceTransformer(settings.embedding_model)


@lru_cache
def get_qdrant() -> QdrantClient:
    settings = get_settings()
    qdrant_kwargs = {"url": settings.qdrant_url}
    if settings.qdrant_api_key:
        qdrant_kwargs["api_key"] = settings.qdrant_api_key
    return QdrantClient(**qdrant_kwargs)


def ensure_collections() -> None:
    client = get_qdrant()
    for name in (COLLECTION_RESUMES, COLLECTION_JOBS, COLLECTION_KNOWLEDGE):
        if not client.collection_exists(name):
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )


def embed_text(text: str) -> list[float]:
    encoder = get_encoder()
    vector = encoder.encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    encoder = get_encoder()
    vectors = encoder.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-9))


def _point_id(key: str | int) -> int:
    if isinstance(key, int):
        return key
    return abs(hash(key)) % (2**63 - 1)


def upsert_vector(collection: str, point_id: str | int, text: str, payload: dict) -> None:
    ensure_collections()
    client = get_qdrant()
    vector = embed_text(text)
    client.upsert(
        collection_name=collection,
        points=[PointStruct(id=_point_id(point_id), vector=vector, payload=payload)],
    )


def search_similar(collection: str, query: str, limit: int = 5) -> list[dict]:
    ensure_collections()
    client = get_qdrant()
    vector = embed_text(query)
    results = client.search(collection_name=collection, query_vector=vector, limit=limit)
    return [
        {"score": hit.score, "payload": hit.payload}
        for hit in results
    ]
