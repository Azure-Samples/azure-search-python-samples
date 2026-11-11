from azure.search.documents.knowledgebases.models import (
    McpServerKnowledgeSourceParams,
    SearchIndexKnowledgeSourceParams,
)

from foundry_iq_multi_source.config import Settings
from foundry_iq_multi_source.sample import (
    build_knowledge_base,
    build_mcp_knowledge_source,
    build_retrieval_request,
    build_search_knowledge_source,
)


def settings() -> Settings:
    return Settings(
        search_endpoint="https://example.search.windows.net",
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_deployment="gpt-5-mini",
        azure_openai_model="gpt-5-mini",
    )


def test_knowledge_base_references_both_sources() -> None:
    config = settings()
    payload = build_knowledge_base(config).as_dict()

    assert payload["knowledgeSources"] == [
        {"name": config.search_knowledge_source_name},
        {"name": config.mcp_knowledge_source_name},
    ]
    assert payload["outputMode"] == "answerSynthesis"
    assert "apiKey" not in payload["models"][0]["azureOpenAIParameters"]


def test_search_index_knowledge_source_uses_semantic_config() -> None:
    payload = build_search_knowledge_source(settings()).as_dict()

    assert payload["kind"] == "searchIndex"
    assert payload["searchIndexParameters"]["semanticConfigurationName"]


def test_mcp_knowledge_source_forces_tool_output_inclusion() -> None:
    payload = build_mcp_knowledge_source(settings()).as_dict()
    tool = payload["mcpServerParameters"]["tools"][0]

    assert payload["kind"] == "mcpServer"
    assert payload["mcpServerParameters"]["serverURL"].startswith("https://")
    assert tool["name"] == "microsoft_docs_search"
    assert tool["inclusionMode"] == "always"
    assert tool["outputParsing"] == {"kind": "auto"}


def test_retrieval_request_forces_only_the_search_source() -> None:
    request = build_retrieval_request(settings()).as_dict()
    source_params = request["knowledgeSourceParams"]
    search = next(
        item for item in source_params if item["kind"] == "searchIndex"
    )
    mcp = next(item for item in source_params if item["kind"] == "mcpServer")

    assert request["includeActivity"] is True
    assert request["maxRuntimeInSeconds"] == 120
    assert "maxRuntimeInSeconds" in request["messages"][0]["content"][0]["text"]
    assert search["alwaysQuerySource"] is True
    assert search["rerankerThreshold"] == 0.0
    assert search["maxOutputDocuments"] == 50
    assert "alwaysQuerySource" not in mcp
    assert mcp["rerankerThreshold"] == 0.0
    assert mcp["maxOutputDocuments"] == 50
    assert all(item["includeReferences"] for item in source_params)
    assert all(item["includeReferenceSourceData"] for item in source_params)
    assert isinstance(
        build_retrieval_request(settings()).knowledge_source_params[0],
        SearchIndexKnowledgeSourceParams,
    )
    assert isinstance(
        build_retrieval_request(settings()).knowledge_source_params[1],
        McpServerKnowledgeSourceParams,
    )
