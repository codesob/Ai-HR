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

    async def _post_with_fallback(self, client: httpx.AsyncClient, payload: dict[str, Any]) -> dict[str, Any]:
        """Try multiple NVIDIA rerank endpoint paths until one succeeds."""
        base = self.endpoint.rstrip("/")
        candidates = [
            f"{base}/rankings",
            f"{base}/ranking",
            f"{base}/rank",
        ]
        if not base.endswith("/v1"):
            candidates.extend([
                f"{base}/v1/rankings",
                f"{base}/v1/ranking",
                f"{base}/v1/rank",
            ])

        last_error: Exception | None = None
        for url in candidates:
            try:
                response = await client.post(url, json=payload)
                if response.status_code == 404:
                    logger.debug(f"NVIDIA reranker endpoint {url} returned 404. Trying next candidate.")
                    continue
                response.raise_for_status()
                logger.debug(f"NVIDIA reranker using endpoint: {url}")
                return response.json()
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 404:
                    logger.debug(f"NVIDIA reranker endpoint {url} returned 404. Trying next candidate.")
                    continue
                raise
            except Exception as e:
                last_error = e
                logger.debug(f"NVIDIA reranker endpoint {url} failed with {type(e).__name__}: {e}. Trying next candidate.")
                continue

        if last_error:
            raise RuntimeError(
                f"NVIDIA reranker endpoint not found. Tried: {', '.join(candidates)}. "
                f"Last error: {last_error}"
            )
        raise RuntimeError(f"NVIDIA reranker endpoint not found. Tried: {', '.join(candidates)}")

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
        if not self.api_key:
            logger.warning("NVIDIA API key not configured. Skipping reranking.")
            # Return documents as-is with default scores
            return self._format_documents(documents, top_k)

        try:
            client = await self._get_client()

            # Prepare documents for API
            doc_texts = [
                d if isinstance(d, str) else d.get("text", str(d))
                for d in documents
            ]

            payload = {
                "model": self.model,
                "query": query,
                "documents": doc_texts,
                "top_k": top_k or len(documents),
            }

            result = await self._post_with_fallback(client, payload)

            # Parse reranked results
            reranked = []
            for item in result.get("results", []):
                idx = item.get("index", 0)
                score = item.get("score", 0.0)

                doc = documents[idx]
                if isinstance(doc, str):
                    reranked.append({
                        "text": doc,
                        "score": score,
                        "rank": len(reranked) + 1,
                    })
                else:
                    doc["score"] = score
                    doc["rank"] = len(reranked) + 1
                    reranked.append(doc)

            return reranked[:top_k] if top_k else reranked

        except Exception as e:
            logger.error(f"Error reranking documents: {e}")
            # Fallback: return documents as-is with default scores
            return self._format_documents(documents, top_k)

    def _format_documents(
        self,
        documents: list[str | dict[str, Any]],
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """Format documents with default scores for fallback."""
        formatted = []
        for idx, doc in enumerate(documents):
            if isinstance(doc, str):
                formatted.append({
                    "text": doc,
                    "score": 1.0 - (idx * 0.05),  # Descending scores
                    "rank": idx + 1,
                })
            else:
                doc["score"] = 1.0 - (idx * 0.05)
                doc["rank"] = idx + 1
                formatted.append(doc)

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
