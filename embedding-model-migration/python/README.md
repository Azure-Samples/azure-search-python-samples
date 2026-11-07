# python (backup/restore/migrate pipeline)

`python/` contains the primary migration scripts:

- `migrate.py`: baseline backup, restore, and vector re-embedding
- `configure_pipeline.py`: optional end-to-end Search indexer + skill + vectorizer setup
- `test_samples.py`: offline regression tests for script and Function contracts

For same-index additive migration (new vector field in the same index), use [`../python-inplace/README.md`](../python-inplace/README.md).

## What methods are used

- **Read path**: Search REST calls for schema, counts, and keyset-paged document reads.
- **Local artifact path**: writes `schema.json`, `documents.jsonl`, `keys.jsonl`, and `manifest.json`.
- **Write path**: pushes data to target index via Search indexing API in bounded batches.
- **Migration path**: calls Function document/query embedding routes and rewrites only the configured vector field.

## Install

```powershell
python -m pip install -r .\embedding-model-migration\python\requirements.txt
```

## Validate locally

```powershell
python .\embedding-model-migration\python\test_samples.py
```

## Main commands

### 1. Backup (frozen source required)

```powershell
python .\embedding-model-migration\python\migrate.py --search-endpoint "https://<source>.search.windows.net" backup --source "<index>" --backup-dir ".\backup" --source-frozen
```

### 2. Restore (identical data path)

```powershell
python .\embedding-model-migration\python\migrate.py --search-endpoint "https://<target>.search.windows.net" restore --target "<new-target-index>" --backup-dir ".\backup"
```

### 3. Re-embed (migration path)

```powershell
python .\embedding-model-migration\python\migrate.py --search-endpoint "https://<target>.search.windows.net" reembed --target "<new-migrated-index>" --backup-dir ".\backup" --migration-dir ".\migration-output" --text-field "<text-field>" --vector-field "<vector-field>" --model fast --dimensions <D> --function-base "https://<function-app>.azurewebsites.net" --function-auth-resource-id "api://<app-id>"
```

### 4. Optional full pipeline creation

```powershell
python .\embedding-model-migration\python\configure_pipeline.py --search-endpoint "https://<search>.search.windows.net" --function-base "https://<function-app>.azurewebsites.net" --function-auth-resource-id "api://<app-id>" --storage-resource-id "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<account>" --container "<container>" --index "<index>" --datasource "<datasource>" --skillset "<skillset>" --indexer "<indexer>" --model fast --dimensions <D>
```

## After migration: how indexing should work

- The migrated index should continue with a consistent embedding contract:
  - same vector field
  - same dimensions
  - same model variant expectation (`fast`/`pro`)
- Query-time vectorization should use the migrated `customWebApi` vectorizer route.
- For new/updated documents, either:
  1. run your normal ingestion pipeline configured to emit vectors with the migrated model settings, or
  2. use `configure_pipeline.py` to create a compatible indexer+skill+vectorizer path.
- Do not mix old/new embedding dimensions in the same target index.

## Human and agent guidance

- `--source-frozen` is mandatory for trustworthy backups.
- Backup and migration directories must be empty/new each run.
- Re-embed target index must be a new name.
- Keep Function auth audience consistent with EasyAuth config.
- Treat any nonzero exit as failure; do not continue into restore.
