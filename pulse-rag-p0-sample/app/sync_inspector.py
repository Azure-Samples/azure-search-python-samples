"""Sync Inspector: the demo-side view of merge-first indexing.

This module exposes three Flask endpoints used by the "Sync Inspector" panel
in the chat UI. Together they let a viewer trigger a write to Cosmos DB and
watch the change propagate into Azure AI Search through three phases that
make the P0-1 invariant visible:

* ``pending`` - the change feed has not yet upserted any chunk at the new
  ``deviceVersion``. The previous version of the content is still fully
  searchable.
* ``upserting`` - chunks at the new ``deviceVersion`` are present **and** the
  stale chunks from the previous version are also still present. This is the
  intentional "merge-first" window: even if the pipeline crashed right now,
  retrieval would still return content.
* ``consistent`` - only chunks at the new ``deviceVersion`` remain for this
  source id; the post-upsert stale-chunk cleanup has run.

The endpoints use ``DefaultAzureCredential`` and rely on the managed identity
already wired to the web container (Cosmos DB Built-in Data Contributor +
Search Index Data Contributor).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Optional

from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from flask import Blueprint, jsonify, request


bp = Blueprint("sync_inspector", __name__)


# A small, curated set of editable fields. Keeping this allow-list makes the
# demo predictable and prevents accidental writes to system fields like ``id``
# or ``_etag``.
_EDITABLE_FIELDS = {"status", "notes", "room", "building", "name"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@lru_cache(maxsize=1)
def _credential() -> DefaultAzureCredential:
    return DefaultAzureCredential()


@lru_cache(maxsize=1)
def _cosmos_container():
    endpoint = os.environ.get("COSMOS_ENDPOINT")
    if not endpoint:
        raise RuntimeError("COSMOS_ENDPOINT is not configured.")
    database_name = os.getenv("COSMOS_DATABASE_NAME", "pulse-rag")
    container_name = os.getenv("COSMOS_CONTAINER_NAME", "devices")
    client = CosmosClient(url=endpoint, credential=_credential())
    return client.get_database_client(database_name).get_container_client(container_name)


@lru_cache(maxsize=1)
def _search_client() -> SearchClient:
    endpoint = os.environ.get("SearchServiceEndpoint")
    if not endpoint:
        raise RuntimeError("SearchServiceEndpoint is not configured.")
    index_name = os.getenv("SearchIndexName", "pulse-device-chunks")
    return SearchClient(endpoint=endpoint, index_name=index_name, credential=_credential())


def _default_tenant() -> str:
    return os.getenv("DEMO_DEFAULT_TENANT_ID", "contoso")


def _escape_filter(value: str) -> str:
    return value.replace("'", "''")


def _summarize_device(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "tenantId": item.get("tenantId") or _default_tenant(),
        "name": item.get("name"),
        "room": item.get("room"),
        "building": item.get("building"),
        "status": item.get("status"),
        "notes": item.get("notes"),
        "etag": item.get("_etag"),
    }


@bp.get("/api/demo/devices")
def list_devices():
    """Return a compact list of devices the Sync Inspector panel can edit."""

    try:
        container = _cosmos_container()
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503

    query = "SELECT c.id, c.tenantId, c.name, c.room, c.building, c.status, c.notes, c._etag FROM c"
    items = list(
        container.query_items(query=query, enable_cross_partition_query=True, max_item_count=200)
    )
    items.sort(key=lambda doc: str(doc.get("id")))
    return jsonify({"devices": [_summarize_device(doc) for doc in items]})


@bp.post("/api/demo/update")
def update_device():
    """Patch one allow-listed field on a device and return the new device version.

    The returned ``expectedVersion`` is the Cosmos ``_etag`` of the just-written
    document. That same value will land on the indexed chunks once the
    change-feed trigger has fully synced this source.
    """

    payload = request.get_json(silent=True) or {}
    device_id = str(payload.get("deviceId") or "").strip()
    tenant_id = str(payload.get("tenantId") or _default_tenant()).strip()
    field = str(payload.get("field") or "").strip()
    value = payload.get("value")

    if not device_id:
        return jsonify({"error": "deviceId is required"}), 400
    if field not in _EDITABLE_FIELDS:
        return jsonify(
            {
                "error": f"field must be one of: {sorted(_EDITABLE_FIELDS)}",
            }
        ), 400
    if value is None:
        return jsonify({"error": "value is required"}), 400

    try:
        container = _cosmos_container()
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503

    try:
        item = container.read_item(item=device_id, partition_key=tenant_id)
    except CosmosResourceNotFoundError:
        return jsonify({"error": f"device {device_id} not found in tenant {tenant_id}"}), 404

    previous_etag = item.get("_etag")
    item[field] = value
    item["lastUpdatedAt"] = _now_iso()

    written = container.replace_item(item=device_id, body=item)
    new_etag = written.get("_etag")

    return jsonify(
        {
            "deviceId": device_id,
            "tenantId": tenant_id,
            "field": field,
            "value": value,
            "previousVersion": previous_etag,
            "expectedVersion": new_etag,
            "writtenAt": item["lastUpdatedAt"],
        }
    )


def _classify(new_count: int, stale_count: int) -> str:
    if new_count == 0 and stale_count == 0:
        return "missing"
    if new_count == 0:
        return "pending"
    if stale_count > 0:
        return "upserting"
    return "consistent"


@bp.get("/api/demo/ingestion-status")
def ingestion_status():
    """Bucket the chunks for a sourceId by ``deviceVersion`` to expose phase.

    A single search call retrieves all chunks for the given ``deviceId``; we
    then count how many are at ``expectedVersion`` (the new version) versus
    any other (stale) version. The combination drives the phase indicator in
    the UI.
    """

    device_id = (request.args.get("deviceId") or "").strip()
    expected_version = (request.args.get("expectedVersion") or "").strip()
    if not device_id or not expected_version:
        return jsonify({"error": "deviceId and expectedVersion are required"}), 400

    try:
        client = _search_client()
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503

    filter_expression = f"sourceId eq '{_escape_filter(device_id)}'"
    results = client.search(
        search_text="*",
        filter=filter_expression,
        select=["id", "deviceVersion", "ingestionTimestamp"],
        top=200,
    )

    new_count = 0
    stale_count = 0
    stale_versions: set[str] = set()
    latest_new_ts: Optional[str] = None
    latest_stale_ts: Optional[str] = None
    for chunk in results:
        version = chunk.get("deviceVersion")
        ts = chunk.get("ingestionTimestamp")
        if version == expected_version:
            new_count += 1
            if ts and (latest_new_ts is None or ts > latest_new_ts):
                latest_new_ts = ts
        else:
            stale_count += 1
            if version:
                stale_versions.add(version)
            if ts and (latest_stale_ts is None or ts > latest_stale_ts):
                latest_stale_ts = ts

    status = _classify(new_count, stale_count)
    return jsonify(
        {
            "deviceId": device_id,
            "expectedVersion": expected_version,
            "status": status,
            "newChunkCount": new_count,
            "staleChunkCount": stale_count,
            "staleVersions": sorted(stale_versions),
            "latestNewIngestionTimestamp": latest_new_ts,
            "latestStaleIngestionTimestamp": latest_stale_ts,
            "checkedAt": _now_iso(),
        }
    )
