"""A company's own HR handbook: split into passages, indexed per organization, searched by the HR agent.

Workspaces that haven't uploaded anything get the sample policies (stored with organization_id 0).
"""

import asyncio
import re

from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.handbook import PolicyDocument
from shared.services.embeddings import (
    COLLECTION_KNOWLEDGE,
    embed_batch,
    ensure_collections,
    get_qdrant,
    point_id,
    search_similar,
)

SAMPLE_POLICIES_ORG = 0
CHUNK_CHARS = 900
OVERLAP_CHARS = 150


def chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    """Passages of about `size` characters, broken at paragraph or sentence ends, overlapping a little so a
    rule split across a boundary is still found whole in one of them."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            window = text[start:end]
            cut = max(window.rfind("\n\n"), window.rfind(". "), window.rfind("\n"))
            if cut > size // 2:
                end = start + cut + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _upsert(points: list[PointStruct]) -> None:
    ensure_collections()
    get_qdrant().upsert(collection_name=COLLECTION_KNOWLEDGE, points=points)


def _delete(organization_id: int, document_id: int) -> None:
    ensure_collections()
    get_qdrant().delete(
        collection_name=COLLECTION_KNOWLEDGE,
        points_selector=Filter(must=[
            FieldCondition(key="organization_id", match=MatchValue(value=organization_id)),
            FieldCondition(key="document_id", match=MatchValue(value=document_id)),
        ]),
    )


def _search(organization_id: int, query: str, limit: int) -> list[dict]:
    return search_similar(COLLECTION_KNOWLEDGE, query, limit=limit, organization_id=organization_id)


def index_document(doc: PolicyDocument, chunks: list[str]) -> None:
    """Blocking (embeds on CPU); call it in a thread."""
    vectors = embed_batch(chunks)
    _upsert([
        PointStruct(
            id=point_id(f"org{doc.organization_id}-doc{doc.id}-{i}"),
            vector=vector,
            payload={
                "organization_id": doc.organization_id, "document_id": doc.id, "doc_id": f"doc-{doc.id}",
                "title": doc.title, "category": "handbook", "text": chunk, "chunk": i,
            },
        )
        for i, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
    ])


def remove_document(doc: PolicyDocument) -> None:
    _delete(doc.organization_id, doc.id)


async def search(db: AsyncSession, organization_id: int, query: str, limit: int = 4) -> list[dict]:
    """Passages from the company's own handbook, or from the sample policies if it hasn't uploaded one."""
    own = (await db.execute(
        select(func.count()).select_from(PolicyDocument).where(PolicyDocument.organization_id == organization_id)
    )).scalar_one()
    scope = organization_id if own else SAMPLE_POLICIES_ORG
    hits = await asyncio.to_thread(_search, scope, query, limit)
    return [
        {
            "source": h["payload"].get("title") or h["payload"].get("doc_id"),
            "text": h["payload"].get("text", ""),
            "from_company_handbook": bool(own),
        }
        for h in hits
    ]
