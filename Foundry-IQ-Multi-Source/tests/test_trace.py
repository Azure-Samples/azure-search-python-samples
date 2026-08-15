import pytest

from foundry_iq_multi_source.trace import verify_dual_source_evidence


SEARCH_SOURCE = "foundry-iq-search-source"
MCP_SOURCE = "foundry-iq-learn-mcp-source"


def response_with_both_sources() -> dict:
    return {
        "activity": [
            {
                "id": 1,
                "type": "searchIndex",
                "knowledgeSourceName": SEARCH_SOURCE,
            },
            {
                "id": 2,
                "type": "mcpServer",
                "knowledgeSourceName": MCP_SOURCE,
                "mcpServerArguments": {"toolName": "microsoft_docs_search"},
            },
        ],
        "references": [
            {
                "id": "0",
                "type": "searchIndex",
                "activitySource": 1,
                "sourceData": {"id": "trail-release-wave-b"},
            },
            {
                "id": "1",
                "type": "mcpServer",
                "activitySource": 2,
                "sourceData": {"title": "MCP Server knowledge source"},
            },
        ],
    }


def test_verifier_confirms_activity_and_references_for_both_sources() -> None:
    evidence = verify_dual_source_evidence(
        response_with_both_sources(),
        search_knowledge_source_name=SEARCH_SOURCE,
        mcp_knowledge_source_name=MCP_SOURCE,
    )

    assert evidence.both_participated
    assert evidence.search.reference_count == 1
    assert evidence.mcp.reference_count == 1


def test_verifier_rejects_activity_without_linked_reference() -> None:
    response = response_with_both_sources()
    response["references"] = response["references"][:1]

    with pytest.raises(RuntimeError, match="Cross-source verification failed"):
        verify_dual_source_evidence(
            response,
            search_knowledge_source_name=SEARCH_SOURCE,
            mcp_knowledge_source_name=MCP_SOURCE,
        )
