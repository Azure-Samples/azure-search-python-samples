---
page_type: sample
languages:
  - python
name: "Tutorial: Embedding model migration in Azure AI Search using Python"
description: |
  Back up an index, regenerate vectors with a new embedding model, and restore to a new target using keyless Python workflows.
products:
  - azure
  - azure-cognitive-search
urlFragment: python-embedding-model-migration
---

# Tutorial: Embedding model migration in Azure AI Search using Python

![Flask sample MIT license badge](https://img.shields.io/badge/license-MIT-green.svg)

This sample provides a keyless migration path for vector indexes:

1. **Baseline pipeline (`python/`)** for backup, restore, and re-embedding.
2. **Embedding Function (`function/`)** with Entra-gated document/query routes.
3. **Deployment helpers (`deployment/`)** to configure keyless hosting and end-to-end setup.

> [!IMPORTANT]
> This is a reference sample, not a production-ready drop-in. Validate E2E behavior in a representative test environment that mirrors your tenant auth, network, model deployments, quotas, and index schema before rollout.

## Problem this sample solves

When customers need to move from one embedding model/dimension setup to another, a direct in-place change can break query compatibility and make rollback hard. They need a safe way to:

1. create a verified baseline copy,
2. regenerate vectors with the new model path, and
3. publish to a new target index with controlled cutover.

## Architecture (what connects to what)

```text
Source Search Index
  -> python/migrate.py backup (schema + docs + manifest)
  -> python/migrate.py reembed (calls Function /document route)
  -> migrated backup artifacts
  -> python/migrate.py restore/reembed
  -> New Target Search Index (new vectorizer/query route)

Query-time path after migration:
Search vectorizer (customWebApi /query route) -> Function -> embedding model
```

## Example customer migration flow

Example: customer has `products-v1` with old vectors and wants `fast` model vectors.

1. Run `migrate.py backup` against `products-v1` (source frozen).
2. Run `migrate.py restore` to validate baseline reproducibility on a new test index.
3. Run `migrate.py reembed` with:
   - `--model fast`
   - `--dimensions <measured fast dimension>`
   - Function auth/resource settings
4. Create `products-v2-fast` as a new target index.
5. Validate retrieval quality and operational behavior, then cut traffic to `products-v2-fast`.

## What happens after migration

- The migrated index is expected to become the active index for reads.
- Ongoing ingestion must produce vectors compatible with the migrated vector field and dimensions.
- Query vectorization must keep using the migrated customWebApi query route and same model family.
- Keep the old index only for rollback window; retire it after acceptance.

## Choose your path

| If you need to... | Use |
|---|---|
| Back up, restore, and migrate vectors | [`python/README.md`](python/README.md) |
| Run the embedding Function app | [`function/README.md`](function/README.md) |
| Configure auth/hosting and optional deployment wiring | [`deployment/README.md`](deployment/README.md) |
| Start from one environment template | [`sample.env`](sample.env) |

## How this Python sample works (high level)

- **Backup path**: reads schema + documents from Search and writes local backup artifacts.
- **Restore path**: reads local backup artifacts and pushes documents into a new target index.
- **Migration path**: reads backup artifacts, regenerates vectors through the Function endpoints, writes a new migration artifact, then restores to a new target.
- **Pipeline helper**: can create an index + datasource + skillset + indexer + query vectorizer aligned to the Function routes.

## Folder structure

- `python/`: migration scripts, fixtures, and tests
- `function/`: Function implementation and auth/runtime helpers
- `deployment/`: PowerShell setup/config scripts
- `sample.env`: consolidated non-secret environment template

## Quickstart (humans)

1. Install Python dependencies:

```powershell
python -m pip install -r .\embedding-model-migration\python\requirements.txt
python -m pip install -r .\embedding-model-migration\function\requirements.txt
```

2. Validate scripts locally:

```powershell
python .\embedding-model-migration\python\test_samples.py
```

3. Run backup and restore:

```powershell
python .\embedding-model-migration\python\migrate.py --search-endpoint "https://<source>.search.windows.net" backup --source "<index>" --backup-dir ".\backup" --source-frozen
python .\embedding-model-migration\python\migrate.py --search-endpoint "https://<target>.search.windows.net" restore --target "<new-target-index>" --backup-dir ".\backup"
```

4. Run migration:

```powershell
python .\embedding-model-migration\python\migrate.py --search-endpoint "https://<target>.search.windows.net" reembed --target "<new-migrated-index>" --backup-dir ".\backup" --migration-dir ".\migration-output" --text-field "<text-field>" --vector-field "<vector-field>" --model fast --dimensions <D> --function-base "https://<function-app>.azurewebsites.net" --function-auth-resource-id "api://<app-id>"
```

## Quickstart (agents/automation)

Execution contract:

1. Stop on first nonzero exit.
2. Require `--source-frozen` for backup.
3. Never reuse backup or migration output directories.
4. Never reuse target index names.
5. Use Entra bearer tokens only; no API keys or client secrets.

## Safety boundaries

- This sample verifies index content and schema compatibility, but does not back up indexers, data sources, aliases, or external model resources.
- Non-retrievable/unstored fields are treated as non-recoverable and fail backup.
- Function query route and dimensions are validated before migration mutations.
- Review and adjust settings, retry policies, naming, and operational controls to your environment and requirements.
- After migration, keep indexing and query vectorization on the same model/dimensions path to avoid drift.
