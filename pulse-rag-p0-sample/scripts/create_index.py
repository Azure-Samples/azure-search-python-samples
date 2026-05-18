"""Create or update the Azure AI Search index from infra/index/pulse-device-chunks.json.

Reads:
  AZURE_SEARCH_ENDPOINT   Required. e.g. https://my-search.search.windows.net
  AZURE_SEARCH_API_KEY    Optional. If unset, DefaultAzureCredential is used (recommended).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "infra" / "index" / "pulse-device-chunks.json"


def main() -> int:
    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT") or os.environ.get("SearchServiceEndpoint")
    if not endpoint:
        print("AZURE_SEARCH_ENDPOINT is required.", file=sys.stderr)
        return 2

    api_key = os.environ.get("AZURE_SEARCH_API_KEY") or os.environ.get("SearchApiKey")
    credential = AzureKeyCredential(api_key) if api_key else DefaultAzureCredential()
    client = SearchIndexClient(endpoint=endpoint, credential=credential)

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    index = SearchIndex.deserialize(schema)
    result = client.create_or_update_index(index)
    print(f"Created or updated index: {result.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
