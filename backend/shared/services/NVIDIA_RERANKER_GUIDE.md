# NVIDIA Nemotron Rerank VL Integration Guide

## Overview

This project now includes integration with **NVIDIA's Llama Nemotron Rerank VL 1B V2** model for intelligent document reranking. This free model significantly improves the relevance of search and matching results by reranking retrieved candidates based on semantic relevance.

## What is Reranking?

Reranking is a two-stage retrieval process:
1. **First stage**: Fast vector-based retrieval returns a larger set of candidates
2. **Second stage**: A reranker model re-orders these candidates by true semantic relevance

This approach combines the speed of vector search with the accuracy of a dedicated ranking model.

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
NVIDIA_API_KEY=sk-or-v1-<your-api-key>
NVIDIA_RERANKER_MODEL=nvidia/llama-nemotron-rerank-vl-1b-v2
NVIDIA_API_ENDPOINT=https://integrate.api.nvidia.com/v1
```

- Get your free API key at: https://build.nvidia.com/

### Configuration File

Settings are automatically loaded in `backend/shared/core/config.py`:

```python
nvidia_api_key: str | None = None
nvidia_reranker_model: str = "nvidia/llama-nemotron-rerank-vl-1b-v2"
nvidia_api_endpoint: str = "https://integrate.api.nvidia.com/v1"
```

## Usage

### In Matching Service

Rerank candidates after initial matching:

```python
from shared.services.matching import rerank_candidates_with_nvidia

# After initial candidate matching
reranked_candidates = await rerank_candidates_with_nvidia(
    job_description="Senior Python Developer with ML experience",
    candidates=initial_candidates,
    top_k=10  # Return top 10 reranked candidates
)
```

### In RAG Chatbot Service

Retrieve documents with reranking:

```python
from shared.services.rag_chatbot import retrieve_context_with_reranking

# Retrieve policy documents with reranking
docs = await retrieve_context_with_reranking(
    query="What is the vacation policy?",
    top_k=3,
    initial_k=10  # Retrieve 10 candidates, rerank to top 3
)

reply, sources = generate_reply(query, docs)
```

### Direct Reranking

For custom use cases:

```python
from shared.services.nvidia_reranker import rerank_documents

results = await rerank_documents(
    query="skill matching query",
    documents=["doc1", "doc2", "doc3"],
    top_k=5
)
```

## API Response Format

Reranked results include:

```python
[
    {
        "text": "document content",
        "score": 0.95,  # Relevance score (0-1)
        "rank": 1,
        "candidate_id": "cand_123",
        "name": "Candidate Name",
        # ... other fields from original document
    }
]
```

## Performance Characteristics

- **Model**: Llama Nemotron Rerank VL 1B V2 (free tier)
- **Latency**: ~100-300ms per request
- **Throughput**: Supports up to 1000 reranking operations/minute (free tier)
- **Accuracy**: State-of-the-art reranking performance

## Best Practices

1. **Two-stage retrieval**: Retrieve more candidates initially (10-50), rerank to final set (3-10)
2. **Timeout handling**: Reranking failures gracefully fallback to original ranking
3. **Batch operations**: Rerank multiple documents in a single API call for efficiency
4. **Top-K strategy**: Use `initial_k > top_k` to maximize relevance

Example two-stage pipeline:

```python
# Stage 1: Vector search retrieves 20 candidates
initial_results = vector_search(query, top_k=20)

# Stage 2: Rerank to top 5
final_results = await rerank_documents(
    query=query,
    documents=initial_results,
    top_k=5
)
```

## Error Handling

The reranker includes automatic fallback behavior:

- If API key is missing: Returns documents with default scores
- If API call fails: Logs error and returns original ranking
- If timeout occurs: Uses fallback scoring mechanism

## Monitoring

Monitor reranking performance:

```python
from shared.services.nvidia_reranker import get_reranker

reranker = await get_reranker()
# Check reranker.client connection status
# Monitor API response times in logs
```

## Use Cases in AI-HR Platform

### 1. **Candidate Matching** (Matching Engine)
```python
# Rerank candidates after resume parsing and skill matching
reranked = await rerank_candidates_with_nvidia(
    job_description=job_jd,
    candidates=matched_candidates,
    top_k=10
)
```

### 2. **Policy Search** (RAG Chatbot)
```python
# Rerank policy documents for employee queries
docs = await retrieve_context_with_reranking(
    query=employee_question,
    top_k=3
)
```

### 3. **Resume Ranking** (Resume Parser)
```python
# Rerank parsed resumes against JD
from shared.services.nvidia_reranker import rerank_documents

reranked_resumes = await rerank_documents(
    query=job_description,
    documents=parsed_resumes_text,
    top_k=10
)
```

## Deployment

When deploying:

1. Ensure `NVIDIA_API_KEY` is set in your environment
2. Add `httpx` to requirements.txt (already included)
3. Monitor API quota on NVIDIA developer console
4. Consider caching reranking results for repeated queries

## Requirements

```txt
httpx>=0.24.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
```

## Troubleshooting

### API key not configured
```
Warning: NVIDIA API key not configured. Skipping reranking.
```
Solution: Set `NVIDIA_API_KEY` in `.env`

### API connection errors
Check logs for detailed error messages. Ensure:
- Network connectivity to `integrate.api.nvidia.com`
- API key is valid (test at https://build.nvidia.com/)
- Rate limits not exceeded

### Slow reranking
- Reduce `initial_k` parameter
- Implement caching for common queries
- Consider async batching

## Additional Resources

- NVIDIA API Documentation: https://docs.nvidia.com/
- Model Card: https://huggingface.co/nvidia/Llama-3.1-Nemotron-70B-Reward-Hf
- Free Tier Info: https://build.nvidia.com/

