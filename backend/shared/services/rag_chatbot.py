import uuid
from pathlib import Path

from shared.core.config import get_settings
from shared.services.embeddings import COLLECTION_KNOWLEDGE, embed_text, ensure_collections, get_qdrant
from qdrant_client.models import PointStruct

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
    settings = get_settings()
    knowledge_dir = Path(settings.knowledge_dir)
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    ensure_collections()
    client = get_qdrant()
    points = []
    for item in DEFAULT_KNOWLEDGE:
        from shared.services.embeddings import _point_id

        vector = embed_text(item["text"])
        points.append(
            PointStruct(
                id=_point_id(item["id"]),
                vector=vector,
                payload={"text": item["text"], "category": item["category"], "doc_id": item["id"]},
            )
        )
    client.upsert(collection_name=COLLECTION_KNOWLEDGE, points=points)


def retrieve_context(query: str, top_k: int = 3) -> list[dict]:
    from shared.services.embeddings import search_similar

    return search_similar(COLLECTION_KNOWLEDGE, query, limit=top_k)


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


_sessions: dict[str, list[dict]] = {}


def chat(message: str, session_id: str | None = None) -> tuple[str, list[str], str]:
    sid = session_id or str(uuid.uuid4())
    contexts = retrieve_context(message, top_k=3)
    reply, sources = generate_reply(message, contexts)
    history = _sessions.setdefault(sid, [])
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    return reply, sources, sid
