import asyncio
import logging
import uuid

from shared.core.config import get_settings
from shared.services.embeddings import (
    COLLECTION_KNOWLEDGE,
    embed_batch,
    ensure_collections,
    get_qdrant,
    point_id,
    search_similar,
)
from shared.services.nvidia_reranker import rerank_documents
from shared.services.ai_llm import get_llm
from qdrant_client.models import PointStruct

logger = logging.getLogger(__name__)

DEFAULT_KNOWLEDGE = [
    {
        "id": "leave-001",
        "text": "Annual leave: Full-time employees receive 20 days paid annual leave per year. Leave requests require manager approval at least 3 business days in advance.",
        "category": "leave",
    },
    {
        "id": "leave-002",
        "text": "Sick leave: Up to 10 days paid sick leave per year. Medical certificate required for absences exceeding 3 consecutive days.",
        "category": "leave",
    },
    {
        "id": "payroll-001",
        "text": "Payroll schedule: Salaries are processed on the last business day of each month. Direct deposit is the default payment method.",
        "category": "payroll",
    },
    {
        "id": "benefits-001",
        "text": "Health benefits: Medical, dental, and vision coverage begin on the first day of the month following 30 days of employment.",
        "category": "benefits",
    },
    {
        "id": "remote-001",
        "text": "Remote work policy: Employees may work remotely up to 3 days per week with manager approval. Core collaboration hours are 10am-3pm local time.",
        "category": "policy",
    },
    {
        "id": "hiring-001",
        "text": "Interview process: Standard pipeline includes application review, skills assessment, two technical interviews, and final culture fit interview. All AI scores require human recruiter review before rejection.",
        "category": "recruiting",
    },
    {
        "id": "onboarding-001",
        "text": "Onboarding: New hires complete ID verification, policy acknowledgements, equipment setup, and security training within the first week.",
        "category": "onboarding",
    },
]


def seed_knowledge_base() -> None:
    """Idempotent: point ids are deterministic, so re-seeding overwrites rather than duplicates."""
    ensure_collections()
    vectors = embed_batch([item["text"] for item in DEFAULT_KNOWLEDGE])
    points = [
        PointStruct(
            id=point_id(item["id"]),
            vector=vector,
            payload={"text": item["text"], "category": item["category"], "doc_id": item["id"]},
        )
        for item, vector in zip(DEFAULT_KNOWLEDGE, vectors, strict=True)
    ]
    get_qdrant().upsert(collection_name=COLLECTION_KNOWLEDGE, points=points)


def retrieve_context(query: str, top_k: int = 3) -> list[dict]:
    return search_similar(COLLECTION_KNOWLEDGE, query, limit=top_k)


async def retrieve_context_with_reranking(query: str, top_k: int = 3, initial_k: int = 10) -> list[dict]:
    """
    Retrieve documents with NVIDIA reranking for better relevance.

    Args:
        query: User query
        top_k: Number of final results to return
        initial_k: Number of candidates to rerank from (retrieve more, then rerank down)

    Returns:
        Reranked context documents
    """
    # Get more candidates initially for reranking
    candidates = await asyncio.to_thread(search_similar, COLLECTION_KNOWLEDGE, query, initial_k)

    if not candidates:
        return []

    # Prepare for reranking
    doc_texts = [
        {
            "text": c["payload"].get("text", ""),
            "payload": c.get("payload", {}),
            "id": c.get("id"),
            "score": c.get("score", 0.0),
        }
        for c in candidates
    ]

    # Rerank with NVIDIA model
    try:
        reranked = await rerank_documents(query, doc_texts, top_k)
        return reranked
    except Exception:
        # Fallback to original results if reranking fails
        return candidates[:top_k]


def generate_reply(query: str, contexts: list[dict]) -> tuple[str, list[str]]:
    """RAG response without mandatory external LLM — template + context for MVP."""
    sources = [c["payload"].get("text", "")[:120] + "..." for c in contexts if c.get("payload")]
    if not contexts:
        return (
            "I don't have specific policy information on that yet. "
            "Please contact HR at hr@company.com or ask your manager.",
            [],
        )

    best = contexts[0]["payload"].get("text", "")
    category = contexts[0]["payload"].get("category", "policy")
    reply = (
        f"Based on our {category} policies:\n\n{best}\n\n"
        "If you need more detail or an exception, please escalate to your HR business partner. "
        "All AI-assisted HR guidance should be verified by a human for legal or compensation matters."
    )
    return reply, sources


async def generate_ai_reply(query: str, contexts: list[dict]) -> tuple[str, list[str]]:
    """Generate AI-powered HR chatbot response using LLM."""
    sources = [c["payload"].get("text", "")[:120] + "..." for c in contexts if c.get("payload")]
    
    if not contexts:
        llm = await get_llm()
        try:
            system = """You are an AI HR assistant. Provide helpful, professional responses about HR policies, 
benefits, and employment practices. Always suggest contacting HR for complex matters."""
            
            response = await llm.generate(
                f"HR Question: {query}",
                system=system,
                max_tokens=200,
                temperature=0.7
            )
            return response, []
        except Exception:
            return (
                "I don't have specific policy information on that yet. "
                "Please contact HR at hr@company.com or ask your manager.",
                [],
            )

    # Build context for LLM
    context_text = "\n".join([
        f"- {c['payload'].get('text', '')}"
        for c in contexts if c.get("payload")
    ])

    llm = await get_llm()
    try:
        system = """You are an expert HR assistant. Use the provided policy information to answer 
employee questions accurately and professionally. Keep responses concise and actionable."""
        
        prompt = f"""
Policy Context:
{context_text}

Employee Question: {query}

Provide a clear, helpful answer based on the policies above. If information isn't complete, suggest next steps.
"""
        
        response = await llm.generate(prompt, system=system, max_tokens=300, temperature=0.5)
        return response, sources
    except Exception:
        logger.exception("LLM reply failed; using template answer")
        return generate_reply(query, contexts)


async def chat(message: str, session_id: str | None = None) -> tuple[str, list[str], str]:
    sid = session_id or str(uuid.uuid4())
    settings = get_settings()
    try:
        if settings.nvidia_api_key:
            contexts = await retrieve_context_with_reranking(message, top_k=3)
        else:
            contexts = await asyncio.to_thread(retrieve_context, message, 3)
    except Exception:
        logger.exception("Knowledge retrieval failed")
        contexts = []
    if settings.groq_api_key:
        reply, sources = await generate_ai_reply(message, contexts)
    else:
        reply, sources = generate_reply(message, contexts)
    return reply, sources, sid
