"""HTTP endpoints exposed by the Function App for demos, probes, and ad-hoc search.

* ``GET  /api/health`` -- liveness probe returning ``"OK"``.
* ``GET  /api/p0/summary`` -- machine-readable summary of which P0 controls
  are implemented and where, for use in demos and reviews.
* ``POST /api/search/preview`` -- thin wrapper over the AI Search index
  (keyword search only) so reviewers can confirm that the change-feed-driven
  ingestion path is actually writing documents.
"""

import json

import azure.functions as func

from shared_code.config import create_search_client, get_settings


bp = func.Blueprint()


@bp.function_name(name="health")
@bp.route(route="health", methods=[func.HttpMethod.GET])
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("OK", status_code=200)


@bp.function_name(name="p0Summary")
@bp.route(route="p0/summary", methods=[func.HttpMethod.GET])
def p0_summary(req: func.HttpRequest) -> func.HttpResponse:
    settings = get_settings()
    payload = {
        "sample": "pulse-rag-p0-sample",
        "searchIndexName": settings.search_index_name,
        "chunking": {
            "chunkSize": settings.chunk_size,
            "chunkOverlap": settings.chunk_overlap,
        },
        "p0Controls": [
            {
                "name": "merge-first indexing",
                "status": "implemented",
                "implementation": "api/indexing.py :: SearchIngestionService.sync_source_document",
            },
            {
                "name": "idempotent chunk keys",
                "status": "implemented",
                "implementation": "api/indexing.py :: build_chunk_id",
            },
            {
                "name": "per-document failure isolation",
                "status": "implemented",
                "implementation": "api/ingest.py :: cosmos_search_sync + api/dlq.py",
            },
        ],
    }
    return func.HttpResponse(
        body=json.dumps(payload),
        mimetype="application/json",
        status_code=200,
    )


@bp.function_name(name="previewSearch")
@bp.route(route="search/preview", methods=[func.HttpMethod.POST])
def preview_search(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
    except ValueError:
        req_body = {}

    search_text = req_body.get("q") or "*"
    top = int(req_body.get("top", 5))

    settings = get_settings()
    search_client = create_search_client(settings)
    results = search_client.search(
        search_text=search_text,
        top=top,
        select=[
            "id",
            "sourceId",
            "title",
            "content",
            "deviceVersion",
            "ingestionTimestamp",
        ],
    )

    response_payload = {
        "results": [
            {
                "id": result.get("id"),
                "sourceId": result.get("sourceId"),
                "title": result.get("title"),
                "content": result.get("content"),
                "deviceVersion": result.get("deviceVersion"),
                "ingestionTimestamp": result.get("ingestionTimestamp"),
            }
            for result in results
        ]
    }

    return func.HttpResponse(
        body=json.dumps(response_payload),
        mimetype="application/json",
        status_code=200,
    )
