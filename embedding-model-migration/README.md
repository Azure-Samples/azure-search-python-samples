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

## Choose your path

| If you need to... | Use |
|---|---|
| Back up, restore, and migrate vectors | [`python/README.md`](python/README.md) |
| Run the embedding Function app | [`function/README.md`](function/README.md) |
| Configure auth/hosting and optional deployment wiring | [`deployment/README.md`](deployment/README.md) |
| Start from one environment template | [`sample.env`](sample.env) |

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
