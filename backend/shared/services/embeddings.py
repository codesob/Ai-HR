import logging
import uuid
from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, VectorParams

from shared.core.config import get_settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

COLLECTION_RESUMES = "resumes"
COLLECTION_JOBS = "jobs"
COLLECTION_KNOWLEDGE = "hr_knowledge"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2
_POINT_NAMESPACE = uuid.UUID("6f1c7a52-3d0e-4b8a-9a57-0c2a1e6e9b11")


@lru_cache
def get_encoder() -> "SentenceTransformer":
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(get_settings().embedding_model)


@lru_cache
def get_qdrant() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=10)


_collections_ready = False


def ensure_collections() -> None:
    global _collections_ready
    if _collections_ready:
        return
    client = get_qdrant()
    for name in (COLLECTION_RESUMES, COLLECTION_JOBS, COLLECTION_KNOWLEDGE):
        if not client.collection_exists(name):
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            client.create_payload_index(name, field_name="organization_id", field_schema="integer")
    _collections_ready = True


def embed_text(text: str) -> list[float]:
    return get_encoder().encode(text, normalize_embeddings=True).tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in get_encoder().encode(texts, normalize_embeddings=True)]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-9))


def point_id(key: str | int) -> str:
    return str(uuid.uuid5(_POINT_NAMESPACE, str(key)))


def _point_id(key: str | int) -> str:
    return point_id(key)


def _org_filter(organization_id: int | None) -> Filter | None:
    if organization_id is None:
        return None
    return Filter(must=[FieldCondition(key="organization_id", match=MatchValue(value=organization_id))])


def upsert_vector(collection: str, key: str | int, text: str, payload: dict) -> None:
    try:
        ensure_collections()
        get_qdrant().upsert(
            collection_name=collection,
            points=[PointStruct(id=_point_id(key), vector=embed_text(text), payload=payload)],
        )
    except Exception:
        logger.exception("Vector upsert failed", extra={"collection": collection})


def search_similar(
    collection: str, query: str, limit: int = 5, organization_id: int | None = None
) -> list[dict]:
    ensure_collections()
    result = get_qdrant().query_points(
        collection_name=collection,
        query=embed_text(query),
        query_filter=_org_filter(organization_id),
        limit=limit,
        with_payload=True,
    )
    return [{"id": hit.id, "score": hit.score, "payload": hit.payload or {}} for hit in result.points]
