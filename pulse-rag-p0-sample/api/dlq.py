"""Dead-letter queue helpers for the per-document failure-isolation P0 control.

When ``api/ingest.py`` fails to index a single source document it constructs a
``DeadLetterRecord`` (source id, failure timestamp, error message, original
payload) and enqueues it onto the ``pulse-rag-indexing-dlq`` Azure Storage
queue. The queue is created by ``infra/resources.bicep`` and the Function
App authenticates with its managed identity (Storage Queue Data Contributor),
so no connection strings or SAS tokens are required.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from azure.storage.queue import QueueClient

from shared_code.config import AppSettings


@dataclass(frozen=True)
class DeadLetterRecord:
    id: str
    source_id: str
    failed_at: str
    error_message: str
    retry_count: int
    payload: dict[str, Any]


def build_dead_letter_record(
    source_document: dict[str, Any], error: Exception, retry_count: int = 0
) -> DeadLetterRecord:
    source_id = str(source_document.get("id", "unknown"))
    return DeadLetterRecord(
        id=f"{source_id}:{int(datetime.now(timezone.utc).timestamp())}",
        source_id=source_id,
        failed_at=datetime.now(timezone.utc).isoformat(),
        error_message=str(error),
        retry_count=retry_count,
        payload=source_document,
    )


def create_dead_letter_client(settings: AppSettings) -> Optional[QueueClient]:
    storage_connection_string = os.getenv("AzureWebJobsStorage")
    if not storage_connection_string:
        return None

    client = QueueClient.from_connection_string(
        conn_str=storage_connection_string,
        queue_name=settings.dlq_queue_name,
    )
    client.create_queue()
    return client


def send_dead_letter_record(
    dead_letter_client: Optional[QueueClient], record: DeadLetterRecord
) -> None:
    payload = json.dumps(asdict(record), default=str)

    if dead_letter_client is None:
        logging.error("DLQ client not configured. Failed payload: %s", payload)
        return

    dead_letter_client.send_message(payload)
