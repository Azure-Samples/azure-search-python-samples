from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from typing import Any, Mapping


DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150


@dataclass(frozen=True, slots=True)
class SearchChunkDocument:
    id: str
    source_id: str
    source_partition_key: str
    source_etag: str
    chunk_index: int
    content_hash: str
    ingestion_run_id: str
    ingestion_timestamp: str
    device_version: str
    title: str
    content: str

    def as_search_document(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "sourceId": self.source_id,
            "sourcePartitionKey": self.source_partition_key,
            "sourceETag": self.source_etag,
            "chunkIndex": self.chunk_index,
            "contentHash": self.content_hash,
            "ingestionRunId": self.ingestion_run_id,
            "ingestionTimestamp": self.ingestion_timestamp,
            "deviceVersion": self.device_version,
            "title": self.title,
            "content": self.content,
        }


def stable_chunk_id(source_id: str, source_etag: str, chunk_index: int) -> str:
    normalized_etag = source_etag.strip().strip('"').replace(" ", "-") or "missing-etag"
    return f"{source_id}_{normalized_etag}_{chunk_index:04d}"


def build_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def split_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be zero or greater")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    normalized_text = text.strip()
    if not normalized_text:
        return []

    step = chunk_size - chunk_overlap
    chunks: list[str] = []
    start = 0
    while start < len(normalized_text):
        end = min(start + chunk_size, len(normalized_text))
        chunk = normalized_text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized_text):
            break
        start += step

    return chunks


def build_searchable_content(source_document: Mapping[str, Any]) -> str:
    field_order = [
        "deviceName",
        "location",
        "status",
        "description",
        "capabilities",
        "notes",
        "content",
    ]
    lines: list[str] = []
    for field_name in field_order:
        value = source_document.get(field_name)
        if value in (None, "", []):
            continue
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value)
        else:
            rendered = str(value)
        lines.append(f"{field_name}: {rendered}")

    if not lines:
        raise ValueError("source document does not contain any searchable content")

    return "\n".join(lines)


def build_search_documents(
    source_document: Mapping[str, Any],
    *,
    ingestion_run_id: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ingestion_time: datetime | None = None,
) -> list[SearchChunkDocument]:
    source_id = str(source_document.get("id") or "").strip()
    if not source_id:
        raise ValueError("source document must contain an id")

    source_etag = str(source_document.get("_etag") or source_document.get("etag") or "missing-etag")
    source_partition_key = str(
        source_document.get("partitionKey")
        or source_document.get("deviceId")
        or source_document.get("tenantId")
        or source_id
    )
    title = str(source_document.get("deviceName") or source_document.get("title") or source_id)
    device_version = str(
        source_document.get("deviceVersion")
        or source_document.get("_ts")
        or source_etag.strip().strip('"')
    )

    content = build_searchable_content(source_document)
    chunks = split_text(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if not chunks:
        raise ValueError("source document did not produce any chunks")

    normalized_time = (ingestion_time or datetime.now(UTC)).astimezone(UTC).isoformat()
    return [
        SearchChunkDocument(
            id=stable_chunk_id(source_id, source_etag, chunk_index),
            source_id=source_id,
            source_partition_key=source_partition_key,
            source_etag=source_etag,
            chunk_index=chunk_index,
            content_hash=build_content_hash(chunk),
            ingestion_run_id=ingestion_run_id,
            ingestion_timestamp=normalized_time,
            device_version=device_version,
            title=title,
            content=chunk,
        )
        for chunk_index, chunk in enumerate(chunks)
    ]


def build_merge_or_upload_actions(documents: list[SearchChunkDocument]) -> list[dict[str, Any]]:
    return [
        {
            "@search.action": "mergeOrUpload",
            **document.as_search_document(),
        }
        for document in documents
    ]


def build_stale_chunk_filter(source_id: str, current_ingestion_run_id: str) -> str:
    escaped_source_id = source_id.replace("'", "''")
    escaped_run_id = current_ingestion_run_id.replace("'", "''")
    return (
        f"sourceId eq '{escaped_source_id}' and ingestionRunId ne '{escaped_run_id}'"
    )