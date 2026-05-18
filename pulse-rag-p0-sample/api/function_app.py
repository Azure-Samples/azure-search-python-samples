"""Azure Functions Python v2 entry point for the Pulse RAG ingestion API.

This module wires two blueprints into a single Function App:

* ``query`` -- HTTP endpoints (`/api/health`, `/api/p0/summary`,
  `/api/search/preview`) used by demos and probes.
* ``ingest`` -- the Cosmos DB change-feed trigger that drives incremental,
  merge-first indexing into Azure AI Search.

The Function App relies on the v2 worker-indexing model
(``AzureWebJobsFeatureFlags=EnableWorkerIndexing``) and identity-based
storage; secrets and connection strings are never required at runtime.
"""

import azure.functions as func

from ingest import bp as ingest_bp
from query import bp as query_bp


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

app.register_functions(query_bp)
app.register_functions(ingest_bp)
