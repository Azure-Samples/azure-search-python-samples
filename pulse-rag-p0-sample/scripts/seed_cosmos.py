"""Seed Cosmos DB with sample device documents to drive the change feed.

Usage:
  python scripts/seed_cosmos.py [--reset]

Environment variables:
  COSMOS_ENDPOINT          Cosmos DB account endpoint (e.g. https://acct.documents.azure.com:443/)
  COSMOS_DATABASE_NAME     Database name (default: pulse-rag)
  COSMOS_CONTAINER_NAME    Container name (default: devices)
  COSMOS_KEY               Optional. If unset, DefaultAzureCredential is used.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential


SAMPLE_PATH = Path(__file__).resolve().parent / "sample_devices.json"


def _client() -> CosmosClient:
    endpoint = os.environ["COSMOS_ENDPOINT"]
    key = os.getenv("COSMOS_KEY")
    if key:
        return CosmosClient(url=endpoint, credential=key)
    return CosmosClient(url=endpoint, credential=DefaultAzureCredential())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete each sample document before upserting it (forces a fresh change feed event).",
    )
    args = parser.parse_args()

    database_name = os.getenv("COSMOS_DATABASE_NAME", "pulse-rag")
    container_name = os.getenv("COSMOS_CONTAINER_NAME", "devices")

    client = _client()
    database = client.create_database_if_not_exists(id=database_name)
    container = database.create_container_if_not_exists(
        id=container_name,
        partition_key=PartitionKey(path="/tenantId"),
    )

    documents = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    for doc in documents:
        if args.reset:
            try:
                container.delete_item(item=doc["id"], partition_key=doc["tenantId"])
                print(f"deleted {doc['id']}")
            except Exception:  # noqa: BLE001
                pass
        container.upsert_item(doc)
        print(f"upserted {doc['id']} ({doc['name']})")

    print(f"\nSeeded {len(documents)} devices into {database_name}/{container_name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
