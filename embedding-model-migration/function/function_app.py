"""Custom skill/vectorizer; never deploy without required Entra EasyAuth.

authsettingsV2 must enable the platform, requireAuthentication, return HTTP 401
for unauthenticated clients, and allow only this app's api://<client-id> audience.
No excluded paths. REQUIRE_ENTRA_AUTH must be true. The platform validates
tokens and supplies the client principal header; a header alone is not JWT
validation and must never replace the required platform configuration.
"""
import json
import os

import azure.functions as func
from embedding_engine import EmbeddingEngine, InputError, TransientProviderError
from embedding_contract import process_values
from retrying_engine import RetryingEmbeddingEngine

# EasyAuth must require Entra authentication (401, no excluded paths) before
# deployment. Function-host anonymous mode delegates JWT validation to EasyAuth.
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
engine = EmbeddingEngine()


@app.route(route="embed/{model}/{role}", methods=["POST"])
def embed(req: func.HttpRequest) -> func.HttpResponse:
    if os.environ.get("REQUIRE_ENTRA_AUTH", "").lower() != "true":
        return func.HttpResponse("Required Entra deployment configuration is missing", status_code=503)
    if not req.headers.get("X-MS-CLIENT-PRINCIPAL-ID"):
        return func.HttpResponse("Entra authentication required", status_code=401)
    model, role = req.route_params.get("model"), req.route_params.get("role")
    if model not in ("baseline", "fast", "pro") or role not in ("document", "query"):
        return func.HttpResponse("Unknown embedding route", status_code=404)
    try:
        body = process_values(req.get_json(), model, role, RetryingEmbeddingEngine(engine, role))
        return func.HttpResponse(json.dumps(body, allow_nan=False),
                                 mimetype="application/json", status_code=200)
    except (ValueError, InputError) as exc:
        return func.HttpResponse(str(exc), status_code=400)
    except TransientProviderError as exc:
        headers = {"Retry-After": exc.retry_after} if exc.retry_after else {}
        return func.HttpResponse(str(exc), status_code=429 if exc.status == 429 else 502,
                                 headers=headers)
