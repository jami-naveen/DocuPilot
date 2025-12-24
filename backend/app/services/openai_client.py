from __future__ import annotations

import time
from typing import List, Sequence

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

from app.core.config import get_settings


class OpenAIClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.chat = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=settings.azure_openai_gpt4o_deployment,
            api_key=settings.azure_openai_api_key,
            api_version="2024-08-01-preview",
            temperature=0.1,
        )
        self.embedding = AzureOpenAIEmbeddings(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=settings.azure_openai_embedding_deployment,
            api_key=settings.azure_openai_api_key,
            api_version="2024-08-01-preview",
        )

    def create_embedding(self, text: str) -> List[float]:
        vector = self.embedding.embed_query(text)
        return vector

    def batch_embeddings(self, texts: Sequence[str]) -> List[List[float]]:
        return self.embedding.embed_documents(list(texts))

    def chat_completion(self, prompt: str, context: str, citations: str) -> tuple[str, float]:
        system_prompt = (
            "You are an Azure RAG assistant. Answer only using the provided context."
        )
        start = time.perf_counter()
        response = self.chat.invoke(
            [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Context:\n{context}\nCitations:\n{citations}\nQuestion:{prompt}",
                },
            ]
        )
        latency = (time.perf_counter() - start) * 1000
        return response.content, latency


openai_client = OpenAIClient()
