from __future__ import annotations

from dataclasses import dataclass
import time
from typing import List

from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient, BlobServiceClient, ContentSettings

from app.core.config import get_settings


@dataclass
class StoredFile:
    name: str
    size_bytes: int
    uploaded_at: str
    container: str


class StorageService:
    def __init__(self) -> None:
        settings = get_settings()
        if settings.azure_storage_connection_string:
            self._client = BlobServiceClient.from_connection_string(
                settings.azure_storage_connection_string
            )
        else:
            credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
            self._client = BlobServiceClient(
                account_url=settings.azure_storage_account_url,
                credential=credential,
            )
        self.raw_container = settings.azure_storage_raw_container
        self.processed_container = settings.azure_storage_processed_container
        self.ensure_containers()

    def upload_file(self, file_bytes: bytes, blob_name: str, content_type: str) -> StoredFile:
        blob = self._client.get_blob_client(self.raw_container, blob_name)
        blob.upload_blob(
            file_bytes,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        props = blob.get_blob_properties()
        return StoredFile(
            name=blob_name,
            size_bytes=props.size,
            uploaded_at=props.last_modified.isoformat(),
            container=self.raw_container,
        )

    def list_recent(self, limit: int = 20) -> List[StoredFile]:
        container = self._client.get_container_client(self.raw_container)
        blobs = sorted(
            container.list_blobs(), key=lambda b: b.last_modified, reverse=True
        )[:limit]
        records = []
        for blob in blobs:
            records.append(
                StoredFile(
                    name=blob.name,
                    size_bytes=blob.size,
                    uploaded_at=blob.last_modified.isoformat(),
                    container=self.raw_container,
                )
            )
        return records

    def download_blob(self, container: str, blob_name: str) -> BlobClient:
        return self._client.get_blob_client(container, blob_name)

    def move_blob(self, source_container: str, target_container: str, blob_name: str) -> None:
        source_blob = self._client.get_blob_client(source_container, blob_name)
        target_blob = self._client.get_blob_client(target_container, blob_name)
        target_blob.start_copy_from_url(source_blob.url)
        props = target_blob.get_blob_properties()
        while props.copy.status == "pending":
            time.sleep(0.5)
            props = target_blob.get_blob_properties()
        if props.copy.status != "success":
            raise RuntimeError(
                f"Copy failed for {blob_name}: {props.copy.status_description}"
            )
        source_blob.delete_blob()

    def list_unprocessed_blob_names(self, limit: int | None = None) -> List[str]:
        container = self._client.get_container_client(self.raw_container)
        blobs = container.list_blobs()
        names: List[str] = []
        for blob in blobs:
            names.append(blob.name)
            if limit and len(names) >= limit:
                break
        return names

    def ensure_containers(self) -> None:
        for container_name in [self.raw_container, self.processed_container]:
            try:
                self._client.create_container(container_name)
            except ResourceExistsError:
                continue


storage_service = StorageService()
