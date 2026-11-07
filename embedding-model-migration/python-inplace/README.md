# Python in-place additive embedding migration sample

This sample keeps the same Azure AI Search index and performs an additive migration:

1. Adds a new vector field/profile/vectorizer (if missing).
2. Re-embeds documents from an existing text field.
3. Writes vectors into the new field with `mergeOrUpload`.
4. Prints before/after index calls and runs verification.

> [!IMPORTANT]
> This flow is additive. It does not toggle the old vector field to non-searchable in place. For strict schema cleanup/removal, use the new-index migration path (`python/migrate.py reembed`) and cut over to a new index.

For dual-write cutovers, use `--marker-field` (and optional `--marker-value`) so reruns process only stale/unmigrated documents.

## Run

```powershell
python .\embedding-model-migration\python-inplace\migrate_inplace.py `
  --search-endpoint "https://<search-service>.search.windows.net" `
  --index "<existing-index>" `
  --text-field "<text-field>" `
  --source-vector-field "<current-vector-field>" `
  --new-vector-field "<new-vector-field>" `
  --model fast `
  --dimensions 1024 `
  --function-base "https://<function-app>.azurewebsites.net" `
  --function-auth-resource-id "api://<function-entra-app-client-id>" `
  --marker-field "migrationVectorVersion"
```

Expected output includes:
- `Before: ...`
- `Backfill target set: ...`
- `Backfilled X/Y pending documents ...`
- `After: ...`
- `After query probe: ...`

## Offline test

```powershell
python .\embedding-model-migration\python-inplace\test_inplace.py
```
