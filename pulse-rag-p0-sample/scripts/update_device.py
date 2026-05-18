"""Update one device in Cosmos DB so you can demo incremental, merge-first reindexing.

Usage examples:
  python scripts/update_device.py --id device-003 --status offline
  python scripts/update_device.py --id device-005 --note "Replaced USB cable, ticket INC-44218 resolved."
  python scripts/update_device.py --id device-004 --poison    # writes a malformed document to trigger DLQ

Environment variables:
  COSMOS_ENDPOINT, COSMOS_DATABASE_NAME, COSMOS_CONTAINER_NAME, COSMOS_KEY (optional)
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential


def _client() -> CosmosClient:
    endpoint = os.environ["COSMOS_ENDPOINT"]
    key = os.getenv("COSMOS_KEY")
    if key:
        return CosmosClient(url=endpoint, credential=key)
    return CosmosClient(url=endpoint, credential=DefaultAzureCredential())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="Source document id to update.")
    parser.add_argument("--tenant", default="contoso", help="Partition key value (default: contoso).")
    parser.add_argument("--status", help="New status value (e.g. online, offline, degraded).")
    parser.add_argument("--note", help="Append this note to the document.")
    parser.add_argument("--name", help="Override the device name.")
    parser.add_argument(
        "--poison",
        action="store_true",
        help="Replace the document with an unparseable payload to demo the DLQ.",
    )
    args = parser.parse_args()

    database_name = os.getenv("COSMOS_DATABASE_NAME", "pulse-rag")
    container_name = os.getenv("COSMOS_CONTAINER_NAME", "devices")

    container = _client().get_database_client(database_name).get_container_client(container_name)

    if args.poison:
        poison_doc = {
            "id": args.id,
            "tenantId": args.tenant,
            "name": None,
            "description": None,
            "capabilities": None,
            "notes": None,
            "tags": None,
            "_poisoned_at": datetime.now(timezone.utc).isoformat(),
        }
        container.upsert_item(poison_doc)
        print(f"Wrote poison document for {args.id}. Watch the DLQ.")
        return 0

    item = container.read_item(item=args.id, partition_key=args.tenant)

    if args.status:
        item["status"] = args.status
    if args.name:
        item["name"] = args.name
    if args.note:
        existing = item.get("notes") or ""
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        item["notes"] = f"{existing}\n[{stamp}] {args.note}".strip()

    item["lastUpdatedAt"] = datetime.now(timezone.utc).isoformat()
    container.replace_item(item=args.id, body=item)

    print(f"Updated {args.id}. New _etag: {item.get('_etag', 'n/a')}")
    print("The Function App should re-index only this document's chunks and remove stale ones.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
