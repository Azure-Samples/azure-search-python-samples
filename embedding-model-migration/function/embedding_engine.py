"""Shared REST embedding engine; never substitutes another model or dimension."""
import math
import os
from urllib.parse import urlencode, urlparse
from identity_auth import credential as identity_credential


class InputError(ValueError):
    pass


class ProviderError(RuntimeError):
    pass


class TransientProviderError(ProviderError):
    def __init__(self, status, retry_after=None):
        super().__init__("Embedding provider temporarily unavailable")
        self.status = status
        self.retry_after = retry_after


def validate_vector(vector, dimensions=None):
    if not isinstance(vector, list) or not vector:
        raise ProviderError("Provider returned an empty or non-array vector")
    if any(isinstance(v, bool) or not isinstance(v, (int, float))
           or not math.isfinite(v) for v in vector):
        raise ProviderError("Provider returned a nonfinite or nonnumeric vector")
    if dimensions is not None and len(vector) != dimensions:
        raise ProviderError(f"Expected {dimensions} dimensions; provider returned {len(vector)}")
    return vector


def _endpoint(name, suffix=None):
    value = os.environ.get(name, "").rstrip("/")
    parsed = urlparse(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise InputError(f"{name} must be a configured HTTPS endpoint without credentials/query")
    if suffix and not parsed.path.rstrip("/").endswith(suffix):
        raise InputError(f"{name} must end with {suffix}")
    return value


class EmbeddingEngine:
    def __init__(self, credential=None, session=None):
        if session is None:
            import requests
            session = requests.Session()
        self.session = session
        self.credential = credential

    def embed(self, model, role, text, dimensions=None, *, timeout=None):
        if model not in ("baseline", "fast", "pro") or role not in ("document", "query"):
            raise InputError("Unsupported model or role")
        if not isinstance(text, str) or not text.strip():
            raise InputError("data.text must be a nonempty string")
        if dimensions is not None and (isinstance(dimensions, bool)
                                       or not isinstance(dimensions, int) or dimensions < 1):
            raise InputError("Dimensions must be a positive integer")
        headers = {"Content-Type": "application/json"}
        if self.credential is None:
            self.credential = identity_credential()
        headers["Authorization"] = "Bearer " + self.credential.get_token(
            "https://cognitiveservices.azure.com/.default").token
        if model == "baseline":
            from urllib.parse import quote
            endpoint = _endpoint("BASELINE_ENDPOINT")
            deployment = os.environ.get("BASELINE_DEPLOYMENT", "text-embedding-3-small")
            url = (f"{endpoint}/openai/deployments/{quote(deployment, safe='')}"
                   "/embeddings?api-version=2024-02-01")
            if dimensions not in (None, 1536):
                raise InputError("The baseline sample uses exactly 1536 dimensions")
            expected = 1536
            payload = {"input": [text], "dimensions": expected}
        else:
            url = _endpoint("COHERE_ENDPOINT", "/providers/cohere/v2/embed")
            api_version = os.environ.get("COHERE_API_VERSION", "2024-05-01-preview")
            if not api_version.strip():
                raise InputError("COHERE_API_VERSION must be nonempty")
            url += "?" + urlencode({"api-version": api_version})
            deployment = os.environ.get(model.upper() + "_DEPLOYMENT")
            if not deployment:
                raise InputError(f"{model.upper()}_DEPLOYMENT is required")
            configured = os.environ.get(model.upper() + "_DIMENSIONS")
            try:
                expected = dimensions if dimensions is not None else (
                    int(configured) if configured else None)
            except ValueError as exc:
                raise InputError("Configured dimensions must be a positive integer") from exc
            if expected is not None and expected < 1:
                raise InputError("Configured dimensions must be positive")
            payload = {"model": deployment, "texts": [text],
                       "input_type": "search_" + role, "embedding_types": ["float"],
                       "truncate": "NONE"}
            if expected is not None:
                payload["output_dimension"] = expected
        # Retry policy belongs to the Function adapter or direct migration caller.
        import requests
        try:
            response = self.session.post(url, headers=headers, json=payload,
                                         timeout=timeout if timeout is not None else (10, 90))
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise TransientProviderError(502) from exc
        except requests.RequestException as exc:
            raise ProviderError("Embedding provider transport failure") from exc
        if response.status_code == 429 or 500 <= response.status_code <= 599:
            raise TransientProviderError(response.status_code, response.headers.get("Retry-After"))
        if not 200 <= response.status_code < 300:
            raise ProviderError(f"Embedding provider rejected request (HTTP {response.status_code})")
        try:
            data = response.json()
            embeddings = ([item["embedding"] for item in data["data"]] if model == "baseline"
                          else data["embeddings"]["float"])
            if len(embeddings) != 1:
                raise ProviderError("Provider did not return exactly one embedding")
            vector = embeddings[0]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Unexpected embedding provider response shape") from exc
        return validate_vector(vector, expected)
