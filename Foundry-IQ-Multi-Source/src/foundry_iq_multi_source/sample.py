from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from azure.core import MatchConditions
from azure.core.credentials import AzureKeyCredential, TokenCredential
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizerParameters,
    KnowledgeBase,
    KnowledgeBaseAzureOpenAIModel,
    KnowledgeSourceReference,
    McpServerAutoOutputParsing,
    McpServerKnowledgeSource,
    McpServerKnowledgeSourceParameters,
    McpServerTool,
    SearchableField,
    SearchFieldDataType,
    SearchIndex,
    SearchIndexFieldReference,
    SearchIndexKnowledgeSource,
    SearchIndexKnowledgeSourceParameters,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
)
from azure.search.documents.knowledgebases import KnowledgeBaseRetrievalClient
from azure.search.documents.knowledgebases.models import (
    KnowledgeBaseMessage,
    KnowledgeBaseMessageTextContent,
    KnowledgeBaseRetrievalRequest,
    KnowledgeRetrievalLowReasoningEffort,
    KnowledgeRetrievalOutputMode,
    McpServerKnowledgeSourceParams,
    SearchIndexKnowledgeSourceParams,
)

from .config import DEFAULT_QUERY, Settings
from .trace import DualSourceEvidence, verify_dual_source_evidence


SEMANTIC_CONFIGURATION_NAME = "multi-source-semantic-config"


def build_index(index_name: str) -> SearchIndex:
    return SearchIndex(
        name=index_name,
        fields=[
            SimpleField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                filterable=True,
            ),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SimpleField(
                name="source_url",
                type=SearchFieldDataType.String,
                retrievable=True,
            ),
        ],
        semantic_search=SemanticSearch(
            default_configuration_name=SEMANTIC_CONFIGURATION_NAME,
            configurations=[
                SemanticConfiguration(
                    name=SEMANTIC_CONFIGURATION_NAME,
                    prioritized_fields=SemanticPrioritizedFields(
                        title_field=SemanticField(field_name="title"),
                        content_fields=[SemanticField(field_name="content")],
                    ),
                )
            ],
        ),
    )


def build_search_knowledge_source(settings: Settings) -> SearchIndexKnowledgeSource:
    return SearchIndexKnowledgeSource(
        name=settings.search_knowledge_source_name,
        description="Indexed fictional Contoso Trail Guide release facts.",
        search_index_parameters=SearchIndexKnowledgeSourceParameters(
            search_index_name=settings.index_name,
            semantic_configuration_name=SEMANTIC_CONFIGURATION_NAME,
            source_data_fields=[
                SearchIndexFieldReference(name="id"),
                SearchIndexFieldReference(name="title"),
                SearchIndexFieldReference(name="content"),
                SearchIndexFieldReference(name="source_url"),
            ],
        ),
    )


def build_mcp_knowledge_source(settings: Settings) -> McpServerKnowledgeSource:
    return McpServerKnowledgeSource(
        name=settings.mcp_knowledge_source_name,
        description="Live public Microsoft Learn documentation through MCP.",
        mcp_server_parameters=McpServerKnowledgeSourceParameters(
            server_url=settings.mcp_server_url,
            tools=[
                McpServerTool(
                    name=settings.mcp_tool_name,
                    output_parsing=McpServerAutoOutputParsing(),
                    inclusion_mode="always",
                    max_output_tokens=3000,
                )
            ],
        ),
    )


def build_knowledge_base(settings: Settings) -> KnowledgeBase:
    model_parameters: dict[str, Any] = {
        "resource_url": settings.azure_openai_endpoint,
        "deployment_name": settings.azure_openai_deployment,
        "model_name": settings.azure_openai_model,
    }
    if settings.azure_openai_api_key:
        model_parameters["api_key"] = settings.azure_openai_api_key

    return KnowledgeBase(
        name=settings.knowledge_base_name,
        description=(
            "Combines indexed Contoso Trail release facts with live Microsoft "
            "Learn guidance."
        ),
        models=[
            KnowledgeBaseAzureOpenAIModel(
                azure_open_ai_parameters=AzureOpenAIVectorizerParameters(
                    **model_parameters
                )
            )
        ],
        knowledge_sources=[
            KnowledgeSourceReference(
                name=settings.search_knowledge_source_name
            ),
            KnowledgeSourceReference(
                name=settings.mcp_knowledge_source_name
            ),
        ],
        retrieval_instructions=(
            "For every request, retrieve the named Contoso release facts from "
            "the Search index and current product guidance from the Microsoft "
            "Learn MCP tool. For runtime questions, retrieve the MCP Server "
            "knowledge source guide that documents maxRuntimeInSeconds, "
            "activity, and references. Do not infer one source's facts from "
            "the other."
        ),
        answer_instructions=(
            "Answer concisely. Cite the indexed release brief for Contoso facts "
            "and Microsoft Learn MCP references for product guidance."
        ),
        retrieval_reasoning_effort=KnowledgeRetrievalLowReasoningEffort(),
        output_mode=KnowledgeRetrievalOutputMode.ANSWER_SYNTHESIS,
    )


def build_retrieval_request(
    settings: Settings,
    query: str = DEFAULT_QUERY,
) -> KnowledgeBaseRetrievalRequest:
    return KnowledgeBaseRetrievalRequest(
        messages=[
            KnowledgeBaseMessage(
                role="user",
                content=[KnowledgeBaseMessageTextContent(text=query)],
            )
        ],
        knowledge_source_params=[
            SearchIndexKnowledgeSourceParams(
                knowledge_source_name=settings.search_knowledge_source_name,
                include_references=True,
                include_reference_source_data=True,
                always_query_source=True,
                fail_on_error=True,
                reranker_threshold=0.0,
                max_output_documents=50,
            ),
            McpServerKnowledgeSourceParams(
                knowledge_source_name=settings.mcp_knowledge_source_name,
                include_references=True,
                include_reference_source_data=True,
                fail_on_error=True,
                reranker_threshold=0.0,
                max_output_documents=50,
            ),
        ],
        include_activity=True,
        max_runtime_in_seconds=120,
        retrieval_reasoning_effort=KnowledgeRetrievalLowReasoningEffort(),
        output_mode=KnowledgeRetrievalOutputMode.ANSWER_SYNTHESIS,
    )


class MultiSourceSample:
    def __init__(
        self,
        settings: Settings,
        credential: AzureKeyCredential | TokenCredential,
    ) -> None:
        self.settings = settings
        self.credential = credential
        self._created_resources: list[dict[str, str]] = []
        self.index_client = SearchIndexClient(
            endpoint=settings.search_endpoint,
            credential=credential,
        )

    def setup(self) -> None:
        self._ensure_names_available()
        created_index = self.index_client.create_index(
            build_index(self.settings.index_name)
        )
        self._record_created(
            "index",
            self.settings.index_name,
            created_index.e_tag,
        )
        documents = _load_documents(self.settings.data_path)
        with SearchClient(
            endpoint=self.settings.search_endpoint,
            index_name=self.settings.index_name,
            credential=self.credential,
        ) as search_client:
            results = search_client.upload_documents(documents)
            failed = [result for result in results if not result.succeeded]
            if failed:
                raise RuntimeError(f"Failed to index documents: {failed}")
            _wait_for_documents(search_client, len(documents))

        created_search_source = self.index_client.create_knowledge_source(
            build_search_knowledge_source(self.settings)
        )
        self._record_created(
            "knowledge_source",
            self.settings.search_knowledge_source_name,
            created_search_source.e_tag,
        )
        created_mcp_source = self.index_client.create_knowledge_source(
            build_mcp_knowledge_source(self.settings)
        )
        self._record_created(
            "knowledge_source",
            self.settings.mcp_knowledge_source_name,
            created_mcp_source.e_tag,
        )
        created_knowledge_base = self.index_client.create_knowledge_base(
            build_knowledge_base(self.settings)
        )
        self._record_created(
            "knowledge_base",
            self.settings.knowledge_base_name,
            created_knowledge_base.e_tag,
        )

    def query(self, query: str = DEFAULT_QUERY) -> tuple[str, DualSourceEvidence]:
        with KnowledgeBaseRetrievalClient(
            endpoint=self.settings.search_endpoint,
            knowledge_base_name=self.settings.knowledge_base_name,
            credential=self.credential,
        ) as client:
            result = client.retrieve(
                retrieval_request=build_retrieval_request(self.settings, query)
            )

        payload = result.as_dict()
        evidence = verify_dual_source_evidence(
            payload,
            search_knowledge_source_name=(
                self.settings.search_knowledge_source_name
            ),
            mcp_knowledge_source_name=self.settings.mcp_knowledge_source_name,
        )
        answer = _extract_answer(payload)
        if not answer:
            raise RuntimeError("The knowledge base returned no synthesized answer.")

        output = {
            "answer": answer,
            "evidence": evidence.as_dict(),
            "response": payload,
        }
        self.settings.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings.output_path.write_text(
            json.dumps(output, indent=2),
            encoding="utf-8",
        )
        return answer, evidence

    def cleanup(self) -> None:
        failures: list[str] = []
        resources = self._created_resources or self._load_manifest()
        operations_by_kind = {
            "knowledge_base": (
                self.index_client.get_knowledge_base,
                self.index_client.delete_knowledge_base,
            ),
            "knowledge_source": (
                self.index_client.get_knowledge_source,
                self.index_client.delete_knowledge_source,
            ),
            "index": (
                self.index_client.get_index,
                self.index_client.delete_index,
            ),
        }
        for resource in reversed(resources):
            kind = resource["kind"]
            name = resource["name"]
            operations = operations_by_kind.get(kind)
            if operations is None:
                failures.append(f"unknown resource kind '{kind}' for '{name}'")
                continue
            get_resource, delete = operations
            try:
                current = get_resource(name)
                if current.e_tag != resource.get("e_tag"):
                    failures.append(
                        f"{kind} '{name}' changed ownership or was modified; "
                        "cleanup refused to delete it"
                    )
                    continue
                delete(
                    current,
                    match_condition=MatchConditions.IfNotModified,
                )
            except ResourceNotFoundError:
                continue
            except HttpResponseError as exc:
                failures.append(f"{kind} '{name}': {exc.message}")
        if failures:
            raise RuntimeError("Cleanup failed:\n- " + "\n- ".join(failures))
        self._created_resources.clear()
        self.settings.manifest_path.unlink(missing_ok=True)

    def _ensure_names_available(self) -> None:
        if self.settings.manifest_path.exists():
            raise RuntimeError(
                f"Resource ownership manifest already exists at "
                f"{self.settings.manifest_path}. Run cleanup before setup."
            )

        checks = [
            ("index", self.settings.index_name, self.index_client.get_index),
            (
                "Search knowledge source",
                self.settings.search_knowledge_source_name,
                self.index_client.get_knowledge_source,
            ),
            (
                "MCP knowledge source",
                self.settings.mcp_knowledge_source_name,
                self.index_client.get_knowledge_source,
            ),
            (
                "knowledge base",
                self.settings.knowledge_base_name,
                self.index_client.get_knowledge_base,
            ),
        ]
        collisions: list[str] = []
        for kind, name, get_resource in checks:
            try:
                get_resource(name)
            except ResourceNotFoundError:
                continue
            collisions.append(f"{kind} '{name}'")
        if collisions:
            raise RuntimeError(
                "Setup stopped because these names already exist and aren't "
                "owned by this run:\n- " + "\n- ".join(collisions)
            )

    def _record_created(self, kind: str, name: str, e_tag: str | None) -> None:
        if not e_tag:
            raise RuntimeError(
                f"Created {kind} '{name}' without an ETag; refusing unsafe "
                "name-only ownership tracking."
            )
        self._created_resources.append(
            {"kind": kind, "name": name, "e_tag": e_tag}
        )
        self.settings.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings.manifest_path.write_text(
            json.dumps(
                {
                    "search_endpoint": self.settings.search_endpoint,
                    "resources": self._created_resources,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _load_manifest(self) -> list[dict[str, str]]:
        path = self.settings.manifest_path
        if not path.exists():
            return []
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("search_endpoint") != self.settings.search_endpoint:
            raise RuntimeError(
                f"Ownership manifest endpoint doesn't match SEARCH_ENDPOINT: "
                f"{path}"
            )
        resources = manifest.get("resources")
        if not isinstance(resources, list):
            raise RuntimeError(f"Invalid resource ownership manifest: {path}")
        if any(
            not isinstance(resource, dict)
            or not all(resource.get(key) for key in ("kind", "name", "e_tag"))
            for resource in resources
        ):
            raise RuntimeError(f"Invalid resource ownership manifest: {path}")
        return resources

    def close(self) -> None:
        self.index_client.close()
        close = getattr(self.credential, "close", None)
        if close:
            close()


def _load_documents(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise RuntimeError(f"Expected a non-empty JSON array in {path}")
    return payload


def _wait_for_documents(
    search_client: SearchClient,
    expected_count: int,
    timeout_seconds: int = 60,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if search_client.get_document_count() >= expected_count:
            return
        time.sleep(2)
    raise TimeoutError(
        f"Index did not report {expected_count} documents within "
        f"{timeout_seconds} seconds."
    )


def _extract_answer(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for message in payload.get("response", []):
        if not isinstance(message, dict):
            continue
        for content in message.get("content", []):
            if isinstance(content, dict) and content.get("text"):
                parts.append(str(content["text"]))
    return "\n\n".join(parts)
