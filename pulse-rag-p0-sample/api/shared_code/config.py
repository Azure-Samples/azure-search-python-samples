from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient


COSMOS_CONNECTION_NAME = "COSMOS_CONNECTION"


@dataclass(frozen=True, slots=True)
class AppSettings:
    search_endpoint: str
    search_index_name: str
    search_api_key: str | None
    cosmos_database_name: str
    cosmos_container_name: str
    lease_container_name: str
    dlq_queue_name: str
    chunk_size: int
    chunk_overlap: int

    @property
    def search_service_name(self) -> str:
        return self.search_endpoint.removeprefix("https://").split(".", maxsplit=1)[0]


Settings = AppSettings


def _read_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    return int(raw_value)


@lru_cache(maxsize=1)
def load_settings() -> AppSettings:
    search_endpoint = os.getenv("SearchServiceEndpoint")
    search_service_name = os.getenv("SearchServiceName", "pulse-search")

    if not search_endpoint:
        search_endpoint = f"https://{search_service_name}.search.windows.net"

    return AppSettings(
        search_endpoint=search_endpoint,
        search_index_name=os.getenv("SearchIndexName", "pulse-device-chunks"),
        search_api_key=os.getenv("SearchApiKey") or None,
        cosmos_database_name=os.getenv("COSMOS_DATABASE_NAME", "pulse-rag"),
        cosmos_container_name=os.getenv("COSMOS_CONTAINER_NAME", "devices"),
        lease_container_name=os.getenv("COSMOS_LEASE_CONTAINER_NAME", "leases"),
        dlq_queue_name=os.getenv("DLQ_QUEUE_NAME", "pulse-rag-indexing-dlq"),
        chunk_size=_read_int("ChunkSize", 1000),
        chunk_overlap=_read_int("ChunkOverlap", 150),
    )


def get_settings() -> AppSettings:
    return load_settings()


def create_search_client(settings: AppSettings) -> SearchClient:
    if settings.search_api_key:
        credential = AzureKeyCredential(settings.search_api_key)
    else:
        credential = DefaultAzureCredential()

    return SearchClient(
        endpoint=settings.search_endpoint,
        index_name=settings.search_index_name,
        credential=credential,
    )
