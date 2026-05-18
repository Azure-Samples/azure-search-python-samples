"""Embedding helpers backed by Azure OpenAI.

This module is intentionally optional: if `AzureOpenAIEndpoint` and
`AzureOpenAIEmbeddingDeployment` are not configured, `embed_texts` returns
`None` and the indexing pipeline simply skips the `contentVector` field. This
lets unit tests and local development work without an Azure OpenAI account, and
makes the embedding dimension change isolated to a single place.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Optional

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


_LOGGER = logging.getLogger(__name__)


def _endpoint() -> Optional[str]:
    return os.getenv("AzureOpenAIEndpoint") or None


def _deployment() -> Optional[str]:
    return os.getenv("AzureOpenAIEmbeddingDeployment") or None


def is_configured() -> bool:
    return bool(_endpoint() and _deployment())


@lru_cache(maxsize=1)
def _client():
    try:
        from openai import AzureOpenAI
    except ImportError:  # pragma: no cover - import-time guard
        _LOGGER.warning("openai package is not installed; embeddings disabled.")
        return None

    endpoint = _endpoint()
    if not endpoint:
        return None

    api_key = os.getenv("AzureOpenAIApiKey")
    api_version = os.getenv("AzureOpenAIApiVersion", "2024-10-21")

    if api_key:
        return AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint,
        )

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    return AzureOpenAI(
        api_version=api_version,
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
    )


def embed_texts(texts: list[str]) -> Optional[list[list[float]]]:
    """Return embeddings for `texts`, or None if embeddings aren't configured."""

    if not is_configured() or not texts:
        return None

    client = _client()
    deployment = _deployment()
    if client is None or deployment is None:
        return None

    response = client.embeddings.create(model=deployment, input=texts)
    return [item.embedding for item in response.data]


def embed_query(text: str) -> Optional[list[float]]:
    embeddings = embed_texts([text])
    return embeddings[0] if embeddings else None


__all__ = ["is_configured", "embed_texts", "embed_query"]
# AzureKeyCredential is re-exported only to keep linters quiet about the unused import
# when downstream tooling inspects the module surface.
_ = AzureKeyCredential
