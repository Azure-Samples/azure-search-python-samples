---
page_type: sample
languages:
  - python
name: "Pulse RAG P0 sample with Cosmos DB incremental indexing"
description: |
  Demonstrates a Foundry-backed chat application architecture where Azure Cosmos DB updates incrementally flow into Azure AI Search using a push-based Azure Functions pipeline that explicitly addresses three P0 reliability issues: merge-first indexing, idempotent chunk keys, and per-document failure isolation.
---
page_type: sample
languages:
  - python
name: "Pulse RAG P0 sample with Cosmos DB incremental sync and Azure AI Search"
description: |
  Demonstrates a push-based Azure Cosmos DB to Azure AI Search ingestion pipeline with explicit protections against delete-before-upload data loss, duplicate processing, and poison document stalls.
products:
  - azure
  - azure-cosmos-db
  - azure-cognitive-search
  - azure-functions
  - azure-ai-foundry
urlFragment: pulse-rag-p0-sample
---

# Pulse RAG P0 sample with Cosmos DB incremental sync and Azure AI Search

This sample is a customer-demo-focused reference for a simple RAG application where Azure Cosmos DB is the system of record and Azure AI Search is updated incrementally from the Cosmos DB change feed.

The implementation is intentionally shaped around Claude's P0 recommendations in [claude-recs.md](../claude-recs.md):

- `mergeOrUpload` is the default indexing action, so the sample never deletes existing search chunks before replacement chunks are accepted.
- Search document keys are deterministic and version-aware, which makes retries idempotent.
- Change feed processing isolates failures per source document and routes failed work to a dead-letter queue.

## Current implementation slice

This initial slice scaffolds the backend ingestion and query layers:

| File | Description |
|------|-------------|
| `api/function_app.py` | Azure Functions entry point that registers HTTP and Cosmos-triggered blueprints |
| `api/query.py` | Health, P0 status, and search preview endpoints |
| `api/ingest.py` | Cosmos DB trigger that processes changes one source document at a time |
| `api/indexing.py` | Stable ID generation, chunk preparation, merge-first upload, and stale chunk cleanup helpers |
| `api/dlq.py` | Dead-letter queue helpers for failed source documents |
| `api/shared_code/config.py` | Shared configuration and authenticated client creation |
| `api/shared_code/p0_pipeline.py` | Pure helper functions with unit tests for stable IDs, chunking, and stale cleanup filters |
| `app/server.py` | Flask chat app that persists the Foundry conversation ID in the user session |
| `app/foundry_chat.py` | Foundry project client wrapper that sends messages to a named agent |
| `app/templates/index.html` | Browser chat interface for demoing the persistent agent experience |
| `tests/test_p0_pipeline.py` | Focused tests for the P0 planning helpers |

## P0 behaviors called out in code

### P0-1: Merge-first indexing

The ingestion path prepares replacement chunks, upserts them with `mergeOrUpload`, and only then looks for stale chunks to delete. This keeps previous content available if an upload fails halfway through.

### P0-2: Idempotent retries

Each search chunk key is derived from the Cosmos source ID, a version token, and the chunk index. Replaying the same change produces the same search document keys instead of duplicates.

### P0-3: Per-document failure isolation

The Cosmos DB trigger processes one changed source document at a time. A single bad document is logged and sent to the DLQ while the remaining documents continue through the pipeline.

## File-to-behavior map

| Customer pain point | Implementation file | Behavior to demo |
|------|-------------|-------------|
| Delete-before-upload causes data loss | `api/indexing.py` | `SearchIngestionService.sync_source_document` upserts replacement chunks first and deletes stale chunks only after the upsert succeeds |
| Retries create duplicate search chunks | `api/shared_code/p0_pipeline.py` | `stable_chunk_id` and the version-aware chunk metadata keep repeated processing idempotent |
| One poison document stalls the batch | `api/ingest.py` and `api/dlq.py` | The change feed handler catches per-document failures and routes them to the DLQ path |
| Need a simple persistent agent demo | `app/server.py` and `app/foundry_chat.py` | The browser session stores a Foundry conversation ID so the chat continues across page refreshes |

## Validation target for this slice

The sample is considered valid for this slice when:

1. The helper tests pass locally.
2. The new Function App modules parse cleanly.
3. The sample documentation makes the P0 intent explicit.

## Local development

### Function App

1. Copy `api/local.settings.json.rename` to `api/local.settings.json` and fill in the Cosmos DB and Azure AI Search values.
2. Install the backend dependencies from `api/requirements.txt`.
3. Start the Function App from the `api/` folder.

### Chat app

1. Copy `app/sample.env` to `app/.env` and fill in `PROJECT_ENDPOINT` and `AGENT_NAME`.
2. Install the chat dependencies from `app/requirements.txt`.
3. Start the app with `python server.py` from the `app/` folder.

If the Foundry settings are missing, the app still starts and the chat API returns a clear configuration error instead of failing at import time.

## Next slices

- Add the chat application surface and persistent session model
- Add infrastructure as code for Cosmos DB, Azure AI Search, Function App hosting, and the Foundry-backed app surface
- Add seed and update scripts that prove incremental refresh without a full rebuild
This sample is a customer-demo-focused reference for a simple RAG application where Azure Cosmos DB is the system of record and Azure AI Search is updated incrementally from the Cosmos DB change feed.
