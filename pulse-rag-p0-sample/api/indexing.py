from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Iterable
from uuid import uuid4

if TYPE_CHECKING:
    from azure.search.documents import SearchClient


DEFAULT_CHUNK_WORDS = 220
DEFAULT_CHUNK_OVERLAP_WORDS = 40
CONTENT_FIELDS = (
    "name",
    "model",
    "room",
    "building",
    "status",
    "description",
    "capabilities",
    "notes",
    "tags",
)


class SearchIndexingError(Exception):
    pass


@dataclass(frozen=True)
class PreparedIndexBatch:
    source_id: str
    device_version: str
    ingestion_run_id: str
    ingestion_timestamp: str
    search_documents: list[dict[str, Any]]


def _coerce_text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(_coerce_text(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _normalize_source_document(source_document: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in source_document.items() if value is not None}


def _source_partition_key(source_document: dict[str, Any]) -> str:
    candidate = (
        source_document.get("tenantId")
        or source_document.get("deviceId")
        or source_document.get("partitionKey")
        or source_document.get("id")
    )
    return str(candidate)


def _device_version(source_document: dict[str, Any]) -> str:
    return str(
        source_document.get("_etag")
        or source_document.get("version")
        or source_document.get("_ts")
        or "v0"
    )


def _compose_source_text(source_document: dict[str, Any]) -> str:
    sections: list[str] = []

    for field in CONTENT_FIELDS:
        value = source_document.get(field)
        if value in (None, "", []):
            continue
        sections.append(f"{field}: {_coerce_text(value)}")

    if not sections:
        fallback_body = {
            key: value
            for key, value in source_document.items()
            if not key.startswith("_") and key != "id"
        }
        sections.append(json.dumps(fallback_body, sort_keys=True))

    return "\n".join(sections)


def _split_text(text: str) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + DEFAULT_CHUNK_WORDS, len(words))
        chunks.append(" ".join(words[start:end]))

        if end == len(words):
            break

        next_start = max(end - DEFAULT_CHUNK_OVERLAP_WORDS, start + 1)
        start = next_start

    return chunks


def _version_token(version_value: str) -> str:
    return hashlib.sha256(version_value.encode("utf-8")).hexdigest()[:16]


def _chunk_content_hash(chunk_text: str) -> str:
    return hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()[:16]


def build_chunk_id(source_id: str, version_value: str, chunk_index: int) -> str:
    return f"{source_id}_{_version_token(version_value)}_{chunk_index:04d}"


def prepare_index_batch(
    source_document: dict[str, Any],
    ingestion_run_id: str | None = None,
    now: datetime | None = None,
) -> PreparedIndexBatch:
    normalized = _normalize_source_document(source_document)
    source_id = str(normalized["id"])
    partition_key = _source_partition_key(normalized)
    device_version = _device_version(normalized)
    search_text = _compose_source_text(normalized)
    chunks = _split_text(search_text)

    now = now or datetime.now(timezone.utc)
    ingestion_run_id = ingestion_run_id or str(uuid4())
    ingestion_timestamp = now.isoformat()

    search_documents: list[dict[str, Any]] = []
    for chunk_index, chunk_text in enumerate(chunks):
        content_hash = _chunk_content_hash(chunk_text)
        search_documents.append(
            {
                "id": build_chunk_id(source_id, device_version, chunk_index),
                "sourceId": source_id,
                "sourcePartitionKey": partition_key,
                "sourceETag": normalized.get("_etag"),
                "chunkIndex": chunk_index,
                "contentHash": content_hash,
                "ingestionRunId": ingestion_run_id,
                "ingestionTimestamp": ingestion_timestamp,
                "deviceVersion": device_version,
                "title": normalized.get("name") or source_id,
                "room": normalized.get("room"),
                "building": normalized.get("building"),
                "status": normalized.get("status"),
                "tags": normalized.get("tags"),
                "content": chunk_text,
            }
        )

    return PreparedIndexBatch(
        source_id=source_id,
        device_version=device_version,
        ingestion_run_id=ingestion_run_id,
        ingestion_timestamp=ingestion_timestamp,
        search_documents=search_documents,
    )


def _failed_results(results: Iterable[Any]) -> list[Any]:
    failures = []
    for result in results:
        if not getattr(result, "succeeded", False):
            failures.append(result)
    return failures


def _escape_filter_value(value: str) -> str:
    return value.replace("'", "''")


def _delete_stale_chunks(
    search_client: "SearchClient",
    source_id: str,
    device_version: str,
    current_ids: set[str],
) -> int:
    filter_expression = (
        f"sourceId eq '{_escape_filter_value(source_id)}' "
        f"and deviceVersion ne '{_escape_filter_value(device_version)}'"
    )
    stale_results = search_client.search(
        search_text="*",
        filter=filter_expression,
        select=["id"],
        top=1000,
    )

    stale_documents = [
        {"id": result["id"]}
        for result in stale_results
        if result.get("id") not in current_ids
    ]

    if not stale_documents:
        return 0

    search_client.delete_documents(documents=stale_documents)
    return len(stale_documents)


class SearchIngestionService:
    def __init__(self, search_client: "SearchClient"):
        self.search_client = search_client

    def sync_source_document(self, source_document: dict[str, Any]) -> dict[str, Any]:
        batch = prepare_index_batch(source_document)
        current_ids = {document["id"] for document in batch.search_documents}

        # P0-1: upsert replacement chunks first. Old chunks are only considered
        # for deletion after the upsert call returns without per-document failures.
        results = self.search_client.merge_or_upload_documents(
            documents=batch.search_documents
        )
        failed_results = _failed_results(results)
        if failed_results:
            first_failure = failed_results[0]
            raise SearchIndexingError(
                "Search upsert failed for source document "
                f"{batch.source_id}: {getattr(first_failure, 'error_message', 'unknown error')}"
            )

        stale_deleted = _delete_stale_chunks(
            search_client=self.search_client,
            source_id=batch.source_id,
            device_version=batch.device_version,
            current_ids=current_ids,
        )

        logging.info(
            "Indexed source document %s with %s chunks and removed %s stale chunks.",
            batch.source_id,
            len(batch.search_documents),
            stale_deleted,
        )
        return {
            "sourceId": batch.source_id,
            "deviceVersion": batch.device_version,
            "chunkCount": len(batch.search_documents),
            "staleDeleted": stale_deleted,
            "ingestionRunId": batch.ingestion_run_id,
        }
