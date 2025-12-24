from __future__ import annotations

from typing import Iterable, List

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    ExhaustiveKnnAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchSuggester,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery

from app.core.config import get_settings


class AzureAISearchService:
    def __init__(self) -> None:
        settings = get_settings()
        if settings.azure_search_api_key:
            credential = AzureKeyCredential(settings.azure_search_api_key)
        else:
            credential = DefaultAzureCredential(
                exclude_interactive_browser_credential=False
            )
        self._data_credential = credential
        self._index_credential = credential
        self.endpoint = settings.azure_search_endpoint
        self.index_name = settings.azure_search_index
        self._search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self._data_credential,
        )
        self._index_client = SearchIndexClient(
            endpoint=self.endpoint,
            credential=self._index_credential,
        )

    def ensure_index(self, vector_dimensions: int = 3072) -> None:
        if self._index_exists():
            return
        fields = [
            SimpleField(name="id", type="Edm.String", key=True),
            SimpleField(name="content", type="Edm.String", searchable=True),
            SimpleField(name="chunk_id", type="Edm.String", filterable=True),
            SimpleField(name="source_path", type="Edm.String", filterable=True),
            SimpleField(name="chunk_order", type="Edm.Int32", filterable=True),
            SimpleField(name="metadata", type="Edm.String", searchable=True),
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=vector_dimensions,
                vector_search_configuration="defaultProfile",
            ),
        ]
        vector_search = VectorSearch(
            algorithms=[
                VectorSearchAlgorithmConfiguration(
                    name="default",
                    kind="hnsw",
                ),
                ExhaustiveKnnAlgorithmConfiguration(name="exhaustive", kind="exhaustiveKnn"),
            ],
            profiles=[
                VectorSearchProfile(
                    name="defaultProfile",
                    algorithm_configuration_name="default",
                )
            ],
        )
        suggester = SearchSuggester(name="sg", source_fields=["content"])
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
            suggesters=[suggester],
        )
        self._index_client.create_index(index)

    def _index_exists(self) -> bool:
        for index in self._index_client.list_indexes():
            if index.name == self.index_name:
                return True
        return False

    def upload_documents(self, documents: Iterable[dict]) -> None:
        batch = list(documents)
        if not batch:
            return
        self._search_client.upload_documents(documents=batch)

    def semantic_hybrid_search(self, query: str, top_k: int, embedding: List[float]):
        vector_query = VectorizedQuery(
            vector=embedding,
            k_nearest_neighbors=top_k,
            fields="embedding",
        )
        results = self._search_client.search(
            search_text=query,
            semantic_configuration_name="semanticConfig",
            vector_queries=[vector_query],
            top=top_k,
        )
        return [r for r in results]


search_service = AzureAISearchService()
