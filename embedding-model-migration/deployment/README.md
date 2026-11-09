# deployment (auth/hosting/setup scripts)

`deployment/` includes PowerShell helpers to configure Entra auth, keyless hosting wiring, RBAC, and optional app deployment orchestration.

## Scripts

| Script | Purpose |
|---|---|
| `setup-e2e.ps1` | End-to-end setup wrapper for MI/RBAC/EasyAuth and optional deployment flow |
| `configure-keyless-hosting.ps1` | Configure keyless Function host/deployment storage and related settings |
| `..\function\configure-entra-auth.ps1` | Configure required EasyAuth policy and allowed principals |

## Usage pattern

1. Run in `-PrintConfiguration` mode first.
2. Review generated config for tenant/resource correctness.
3. Execute mutation mode only after review.
4. Validate auth path (anonymous returns 401, authorized calls succeed).

## Human and agent guidance

- Use only approved resource IDs and tenant scopes.
- Never embed secrets in command arguments or checked-in files.
- Do not run setup against shared production resources without explicit approval.
- Stop after any failed role assignment, auth config validation, or deployment check.
