# function (embedding endpoint)

`function/` hosts the embedding API used by both indexing-time and query-time vector generation.

## What it exposes

Route:

- `POST /api/embed/{model}/{role}`

Allowed values:

- `model`: `baseline`, `fast`, `pro`
- `role`: `document`, `query`

## Security model

- Function runtime is `ANONYMOUS` trigger mode, but access is enforced by Entra EasyAuth.
- `REQUIRE_ENTRA_AUTH=true` must be set.
- Requests must include a valid Entra principal (`X-MS-CLIENT-PRINCIPAL-ID` present).
- Unauthenticated calls return 401.

## Install

```powershell
python -m pip install -r .\embedding-model-migration\function\requirements.txt
```

## Local contract tests

`python\test_samples.py` exercises function contract behavior via mocks and in-memory adapters.

```powershell
python .\embedding-model-migration\python\test_samples.py
```

## Required runtime settings (summary)

- `BASELINE_ENDPOINT`, `BASELINE_DEPLOYMENT`
- `COHERE_ENDPOINT`
- `FAST_DEPLOYMENT`, `PRO_DEPLOYMENT`
- `FAST_DIMENSIONS`, `PRO_DIMENSIONS`
- `REQUIRE_ENTRA_AUTH=true`

## Human and agent guidance

- Do not use API keys, function keys, or client secrets in this sample path.
- Validate both `/document` and `/query` routes for each model before indexing.
- Treat 429/5xx as retriable and 401/403 as hard auth failures requiring configuration fix.
