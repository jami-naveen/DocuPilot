from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Azure RAG MVP"
    environment: str = "development"

    azure_storage_account_url: str
    azure_storage_connection_string: str | None = None
    azure_storage_raw_container: str = "raw-documents"
    azure_storage_processed_container: str = "processed-documents"

    azure_search_endpoint: str
    azure_search_index: str
    azure_search_api_key: str | None = None

    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_gpt4o_deployment: str
    azure_openai_embedding_deployment: str

    processing_chunk_size: int = 1500
    processing_chunk_overlap: int = 200
    processing_batch_size: int = 10
    max_documents_per_run: int = 25

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
