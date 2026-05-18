"""Retrieve grounding context from Azure AI Search for the chat surface."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    id: str
    source_id: str
    title: str
    content: str
    score: float | None


def _search_client() -> SearchClient | None:
    endpoint = os.getenv("SearchServiceEndpoint")
    index_name = os.getenv("SearchIndexName", "pulse-device-chunks")
    if not endpoint:
        return None

    api_key = os.getenv("SearchApiKey")
    credential = AzureKeyCredential(api_key) if api_key else DefaultAzureCredential()
    return SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)


def _format_results(results: Iterable[dict]) -> list[RetrievedChunk]:
    formatted: list[RetrievedChunk] = []
    for item in results:
        formatted.append(
            RetrievedChunk(
                id=item.get("id", ""),
                source_id=item.get("sourceId", ""),
                title=item.get("title", ""),
                content=item.get("content", ""),
                score=item.get("@search.score"),
            )
        )
    return formatted


def retrieve_context(query: str, top: int = 5, query_vector: list[float] | None = None) -> list[RetrievedChunk]:
    client = _search_client()
    if client is None:
        return []

    select_fields = ["id", "sourceId", "title", "content"]

    if query_vector is not None:
        vector_query = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=top,
            fields="contentVector",
        )
        results = client.search(
            search_text=query,
            top=top,
            select=select_fields,
            vector_queries=[vector_query],
            query_type="semantic",
            semantic_configuration_name="pulse-semantic",
        ) if os.getenv("EnableSemanticRanking", "false").lower() == "true" else client.search(
            search_text=query,
            top=top,
            select=select_fields,
            vector_queries=[vector_query],
        )
    else:
        results = client.search(search_text=query, top=top, select=select_fields)

    return _format_results(results)
