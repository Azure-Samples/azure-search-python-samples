"""Secretless credentials and the Entra audience shared by samples."""
import os
import threading
import time
from uuid import UUID


class CachedTokenCredential:
    """Process-memory tokens only; refresh five minutes before expiration."""
    def __init__(self, credential, clock=None):
        self.credential = credential
        self._clock = clock or time.time
        self._tokens = {}
        self._lock = threading.Lock()

    def get_token(self, *scopes, **kwargs):
        key = (scopes, tuple(sorted(kwargs.items())))
        try:
            hash(key)
        except TypeError:
            return self.credential.get_token(*scopes, **kwargs)
        with self._lock:
            token = self._tokens.get(key)
            if token is not None and token.expires_on > self._clock() + 300:
                return token
            token = self.credential.get_token(*scopes, **kwargs)
            self._tokens[key] = token
            return token

    def close(self):
        with self._lock:
            self._tokens.clear()
            self.credential.close()


def function_audience(value):
    if not isinstance(value, str) or not value.startswith("api://"):
        raise ValueError("Function audience must be api://<application-client-id>")
    try:
        UUID(value[6:])
    except (ValueError, AttributeError) as exc:
        raise ValueError("Function audience must be api://<application-client-id>") from exc
    return value


def credential(managed_identity=False, cli=False):
    from azure.identity import AzureCliCredential, DefaultAzureCredential, ManagedIdentityCredential
    client_id = os.environ.get("AZURE_CLIENT_ID")
    if managed_identity or client_id or os.environ.get("IDENTITY_ENDPOINT") or os.environ.get("MSI_ENDPOINT"):
        selected = ManagedIdentityCredential(client_id=client_id) if client_id else ManagedIdentityCredential()
        return CachedTokenCredential(selected)
    if cli:
        return CachedTokenCredential(AzureCliCredential())
    return CachedTokenCredential(DefaultAzureCredential(
        exclude_environment_credential=True, exclude_workload_identity_credential=True))
