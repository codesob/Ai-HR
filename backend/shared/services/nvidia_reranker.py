"""NVIDIA Nemotron Rerank VL integration for document reranking."""

import httpx
import logging
from typing import Any

from shared.core.config import get_settings

logger = logging.getLogger(__name__)


class NvidiaReranker:
    """Reranks documents using NVIDIA's Nemotron Rerank VL 1B V2 model."""

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.nvidia_api_key
        self.model = self.settings.nvidia_reranker_model
        self.endpoint = self.settings.nvidia_api_endpoint
        self.client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self.client

    def _ranking_url(self) -> str:
        """Hosted API: {base}/{model}/reranking. A full self-hosted NIM ranking URL is used as-is."""
        base = self.endpoint.rstrip("/")
        if base.endswith(("/reranking", "/ranking")):
            return base
        return f"{base}/{self.model}/reranking"

    async def _post_rankings(self, client: httpx.AsyncClient, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """POST to the ranking endpoint and return a validated `rankings` list; raises on any failure."""
        response = await client.post(self._ranking_url(), json=payload)
        response.raise_for_status()
        rankings = response.json().get("rankings")
        if not isinstance(rankings, list) or not rankings:
            raise ValueError("NVIDIA reranker returned no rankings")
        n = len(payload["passages"])
        for item in rankings:
            idx = item.get("index") if isinstance(item, dict) else None
            if not isinstance(idx, int) or not 0 <= idx < n or not isinstance(item.get("logit"), (int, float)):
                raise ValueError("NVIDIA reranker returned a malformed ranking entry")
        return rankings

    async def close(self):
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None

    async def rerank(
        self,
        query: str,
        documents: list[str | dict[str, Any]],
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Rerank documents based on relevance to the query.

        Args:
            query: The search query string
            documents: List of documents (strings or dicts with 'text' key)
            top_k: Number of top results to return (optional)

        Returns:
            List of reranked documents with scores, sorted by relevance
        """
        if not documents:
            return []

        if not self.api_key:
            logger.warning("NVIDIA API key not configured. Skipping reranking.")
            return self._format_documents(documents, top_k)

        try:
            client = await self._get_client()

            doc_texts = [
                d if isinstance(d, str) else d.get("text", str(d))
                for d in documents
            ]

            payload = {
                "model": self.model,
                "query": {"text": query},
                "passages": [{"text": t} for t in doc_texts],
                "truncate": "END",
            }

            rankings = await self._post_rankings(client, payload)
            rankings = sorted(rankings, key=lambda r: r["logit"], reverse=True)

            reranked = []
            for item in rankings:
                doc = documents[item["index"]]
                base = {"text": doc} if isinstance(doc, str) else dict(doc)
                reranked.append({**base, "score": item["logit"], "rank": len(reranked) + 1, "reranked": True})

            return reranked[:top_k] if top_k else reranked

        except Exception as e:
            logger.error("Error reranking documents: %s", type(e).__name__)
            return self._format_documents(documents, top_k)

    def _format_documents(
        self,
        documents: list[str | dict[str, Any]],
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fallback: keep the input order without inventing relevance scores."""
        formatted = []
        for idx, doc in enumerate(documents):
            base = {"text": doc} if isinstance(doc, str) else dict(doc)
            formatted.append({**base, "score": None, "rank": idx + 1, "reranked": False})

        return formatted[:top_k] if top_k else formatted


# Global reranker instance
_reranker_instance: NvidiaReranker | None = None


async def get_reranker() -> NvidiaReranker:
    """Get or create the reranker instance."""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = NvidiaReranker()
    return _reranker_instance


async def rerank_documents(
    query: str,
    documents: list[str | dict[str, Any]],
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """
    Convenience function to rerank documents.

    Args:
        query: The search query
        documents: List of documents to rerank
        top_k: Number of top results (optional)

    Returns:
        Reranked documents with scores
    """
    reranker = await get_reranker()
    return await reranker.rerank(query, documents, top_k)
