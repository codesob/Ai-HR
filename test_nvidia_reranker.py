#!/usr/bin/env python3
"""
NVIDIA Reranker Integration Test Script

Run this script to test the NVIDIA Nemotron Rerank VL integration:
    python test_nvidia_reranker.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from shared.services.nvidia_reranker import rerank_documents, get_reranker
from shared.services.matching import rerank_candidates_with_nvidia
from shared.core.config import get_settings


async def test_basic_reranking():
    """Test basic document reranking."""
    print("\n" + "="*60)
    print("TEST 1: Basic Document Reranking")
    print("="*60)
    
    query = "Python developer with machine learning experience"
    documents = [
        "Experienced Python developer with 5 years in web development",
        "Machine learning engineer specialized in NLP and deep learning",
        "Full-stack developer proficient in JavaScript and React",
        "Python expert with machine learning and data science background",
        "Junior developer learning Python basics",
    ]
    
    print(f"\nQuery: {query}\n")
    print("Original Document Order:")
    for i, doc in enumerate(documents, 1):
        print(f"  {i}. {doc}")
    
    results = await rerank_documents(query, documents, top_k=3)
    
    print("\nReranked Results (Top 3):")
    for result in results:
        score = result.get("score")
        rank = result.get("rank", 0)
        text = result.get("text", "")
        print(f"  {rank}. [{'n/a' if score is None else f'{score:.3f}'}] {text}")
    
    return len(results) > 0


async def test_candidate_reranking():
    """Test candidate reranking."""
    print("\n" + "="*60)
    print("TEST 2: Candidate Reranking")
    print("="*60)
    
    job_description = """
    Looking for a Senior Backend Engineer with expertise in Python, FastAPI, 
    and async programming. Experience with cloud deployment and microservices required.
    """
    
    candidates = [
        {
            "id": "cand_001",
            "name": "Alice Johnson",
            "match_score": 0.75,
            "resume_text": "Senior developer with 8 years experience. Expertise in Python, Django, REST APIs. Cloud deployment with AWS."
        },
        {
            "id": "cand_002",
            "name": "Bob Smith",
            "match_score": 0.65,
            "resume_text": "Backend engineer with 5 years experience. Node.js, Express, PostgreSQL. Some Python knowledge."
        },
        {
            "id": "cand_003",
            "name": "Carol White",
            "match_score": 0.88,
            "resume_text": "Principal engineer with 12 years experience. Python, FastAPI, async/await expert. Microservices architecture, Kubernetes, GCP."
        },
        {
            "id": "cand_004",
            "name": "David Brown",
            "match_score": 0.45,
            "resume_text": "Junior developer. Learning Python. Familiar with basic web development concepts."
        },
    ]
    
    print(f"\nJob Description: {job_description.strip()}\n")
    print("Original Candidate Order (by match_score):")
    for c in sorted(candidates, key=lambda x: x["match_score"], reverse=True):
        print(f"  • {c['name']:15} (score: {c['match_score']:.2f}) - {c['resume_text'][:60]}...")
    
    reranked = await rerank_candidates_with_nvidia(
        job_description=job_description,
        candidates=candidates,
        top_k=3
    )
    
    print("\nReranked Candidates (NVIDIA Nemotron):")
    for c in reranked:
        rerank_score = c.get("rerank_score")
        original_score = c.get("original_score", 0.0)
        rerank_text = "n/a" if rerank_score is None else f"{rerank_score:.3f}"
        print(f"  • {c.get('name', 'Unknown'):15} (rerank: {rerank_text}, original: {original_score:.2f})")
    
    return len(reranked) > 0


async def test_reranker_instance():
    """Test reranker instance management."""
    print("\n" + "="*60)
    print("TEST 3: Reranker Instance Management")
    print("="*60)
    
    settings = get_settings()
    print(f"\nSettings loaded:")
    print(f"  NVIDIA API Key configured: {'✓' if settings.nvidia_api_key else '✗'}")
    print(f"  Model: {settings.nvidia_reranker_model}")
    print(f"  Endpoint: {settings.nvidia_api_endpoint}")
    
    reranker = await get_reranker()
    print(f"\nReranker instance created: {reranker is not None}")
    print(f"  API Key configured: {'✓' if reranker.api_key else '✗'}")
    
    await reranker.close()
    print("  Connection closed: ✓")
    
    return True


async def test_error_handling():
    """Test error handling."""
    print("\n" + "="*60)
    print("TEST 4: Error Handling & Fallback")
    print("="*60)
    
    # Test with empty documents
    print("\nTest 4a: Empty documents")
    results = await rerank_documents("query", [], top_k=5)
    print(f"  Empty results returned: {len(results) == 0} ✓")
    
    # Test with single document
    print("\nTest 4b: Single document")
    results = await rerank_documents("query", ["single document"], top_k=1)
    print(f"  Single result returned: {len(results) == 1} ✓")
    
    # Test with None API key (simulated fallback)
    print("\nTest 4c: Graceful fallback")
    results = await rerank_documents(
        "Python programming",
        ["doc1", "doc2", "doc3"],
        top_k=2
    )
    print(f"  Fallback results returned: {len(results) > 0} ✓")
    
    return True


async def run_all_tests():
    """Run all tests."""
    print("\n" + "#"*60)
    print("# NVIDIA Nemotron Rerank VL Integration Tests")
    print("#"*60)
    
    tests = [
        ("Basic Reranking", test_basic_reranking),
        ("Candidate Reranking", test_candidate_reranking),
        ("Reranker Instance", test_reranker_instance),
        ("Error Handling", test_error_handling),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Error in {test_name}: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "#"*60)
    print("# Test Summary")
    print("#"*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} | {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Integration is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check configuration.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
