from __future__ import annotations

import json
from typing import List

from app.models.schemas import ChatHistoryItem, ChatResponse, Citation
from app.services.openai_client import openai_client
from app.services.search import search_service


def run_rag(question: str, history: List[ChatHistoryItem], top_k: int) -> ChatResponse:
    embedding = openai_client.create_embedding(question)
    search_results = search_service.semantic_hybrid_search(
        query=question,
        top_k=top_k,
        embedding=embedding,
    )
    context_chunks = []
    citations: List[Citation] = []
    ranked_hits: List[tuple[float, dict, dict]] = []
    for result in search_results:
        score = float(result.get("@search.score", 0.0) or 0.0)
        metadata = json.loads(result["metadata"])
        ranked_hits.append((score, result, metadata))

    if ranked_hits:
        ranked_hits.sort(key=lambda item: item[0], reverse=True)
        top_score, _, top_metadata = ranked_hits[0]
        primary_doc = top_metadata.get("source_path", "unknown")
        dynamic_threshold = max(0.2, top_score * 0.6)

        for score, result, metadata in ranked_hits:
            same_doc = metadata.get("source_path") == primary_doc
            if not same_doc and score < dynamic_threshold:
                continue
            context_chunks.append(result["content"])
            citations.append(
                Citation(
                    chunk_id=metadata.get("chunk_id", "unknown"),
                    source_document=metadata.get("source_path", "unknown"),
                    score=score,
                    snippet=result["content"][:400],
                )
            )
            if same_doc and len(citations) >= 4:
                break

        if not citations:
            score, result, metadata = ranked_hits[0]
            context_chunks.append(result["content"])
            citations.append(
                Citation(
                    chunk_id=metadata.get("chunk_id", "unknown"),
                    source_document=metadata.get("source_path", "unknown"),
                    score=score,
                    snippet=result["content"][:400],
                )
            )
    context = "\n---\n".join(context_chunks)
    citation_str = "\n".join(
        f"chunk: {c.chunk_id} source: {c.source_document} score:{c.score:.3f}"
        for c in citations
    )
    answer, latency = openai_client.chat_completion(question, context, citation_str)
    top_score = max((c.score for c in citations), default=0.0)
    confidence = min(1.0, top_score)
    return ChatResponse(
        answer=answer,
        citations=citations,
        latency_ms=latency,
        confidence=confidence,
    )
