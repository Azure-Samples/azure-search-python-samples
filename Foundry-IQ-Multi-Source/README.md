# Foundry IQ with a Search index and external MCP source

This sample creates one Foundry IQ knowledge base that references both a
`SearchIndexKnowledgeSource` and an `McpServerKnowledgeSource`. A single
complex query combines fictional public release facts from an Azure AI Search
index with current product guidance from the public Microsoft Learn MCP server.
The run fails unless the returned `activity` and `references` prove that both
sources contributed.

## What the sample proves

```text
Complex query
    |
    v
Foundry IQ knowledge base
    |-- SearchIndexKnowledgeSource --> bundled Contoso release brief
    `-- McpServerKnowledgeSource ----> https://learn.microsoft.com/api/mcp
                                           microsoft_docs_search
    |
    v
Synthesized answer + activity + references
```

The bundled query asks for a Wave B date and response-time SLO that exist only
in `data/release-brief.json`, plus current MCP retrieval guidance available
through Microsoft Learn. This makes a one-source answer incomplete by design.

## Prerequisites

- Python 3.11 or later.
- Azure AI Search in a region and API deployment that supports MCP Server
  knowledge sources (`2026-05-01-preview`).
- Semantic ranker enabled on the Search service.
- An Azure OpenAI chat deployment supported by Foundry IQ.
- Permission to create indexes, knowledge sources, and knowledge bases.

The sample uses `DefaultAzureCredential` for Azure AI Search by default. Assign
your user the Search Service Contributor and Search Index Data Contributor
roles. For keyless model access, enable a managed identity on the Search
service and grant it Cognitive Services OpenAI User on the Azure OpenAI
resource. Optional key environment variables are supported for environments
where RBAC isn't configured.

## Run from scratch

```powershell
cd Foundry-IQ-Multi-Source
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item sample.env .env
```

Edit `.env`, sign in, and run:

```powershell
az login
foundry-iq-multi-source run
```

The `run` action creates the index, uploads the bundled public sample data,
creates both knowledge sources and the knowledge base, executes the
cross-source query, verifies source participation, writes the full response to
`.outputs/latest-result.json`, and deletes the created resources.

Setup refuses to overwrite any existing resource with the configured names.
Each successful creation is recorded in the ignored
`.outputs/resources.json` ownership manifest. Cleanup deletes only resources
listed in that manifest and uses the creation ETag with a conditional delete.
A failed or interrupted run therefore can't delete unrelated, modified, or
replacement resources with similar names.

To inspect resources before cleanup:

```powershell
foundry-iq-multi-source run --keep-resources
foundry-iq-multi-source cleanup
```

The actions are also independently runnable:

```powershell
foundry-iq-multi-source setup
foundry-iq-multi-source query
foundry-iq-multi-source cleanup
```

## How both sources are made reliable

| Control | Setting | Why |
|---|---|---|
| Search request routing | `always_query_source=True` | The indexed release brief is always queried. |
| MCP tool inclusion | `inclusion_mode="always"` | Parsed MCP output isn't dropped during final reranking. |
| Initial reranker floor | `reranker_threshold=0.0` on both sources | Validation starts permissively so evidence isn't filtered before tuning. |
| Failure behavior | `fail_on_error=True` on both sources | A missing source is visible instead of producing a plausible partial answer. |
| Per-source document cap | `max_output_documents=50` | Uses the preview API's minimum accepted value (50–200). |
| Runtime budget | `max_runtime_in_seconds=120` | Remote MCP calls can take longer than index retrieval. |
| Trace visibility | `include_activity=True`, `include_references=True`, and `include_reference_source_data=True` | The response contains auditable routing and grounding evidence. |

`always_query_source` is intentionally omitted from
`McpServerKnowledgeSourceParams`: MCP Server knowledge sources don't support
that request-time control. The cross-source query and retrieval instructions
make the tool relevant, while tool-level `inclusion_mode="always"` keeps its
parsed output in the candidate set.

After the flow is stable, change MCP inclusion to `"reranked"` and increase
`reranker_threshold` gradually while checking the same trace verifier. Don't
optimize those settings from answer text alone.

## Expected evidence

The CLI prints a compact result similar to:

```json
{
  "search": {
    "knowledge_source_name": "foundry-iq-search-source",
    "activity_count": 1,
    "reference_count": 2
  },
  "mcp": {
    "knowledge_source_name": "foundry-iq-learn-mcp-source",
    "activity_count": 1,
    "reference_count": 3
  },
  "both_participated": true
}
```

The verifier doesn't trust names in prose. Each reference must either name the
knowledge source or link through `activitySource` to an activity record for
that source.

## Troubleshooting

- **`mcpServer` is rejected during knowledge-source creation:** The Search
  service deployment or region doesn't expose the preview feature.
- **Only the Search source appears:** Keep the query's explicit request for
  current Microsoft Learn guidance, retain MCP `inclusion_mode="always"`, and
  inspect MCP activity errors.
- **MCP activity exists but no MCP reference survives:** Keep the initial
  `reranker_threshold=0.0`; confirm `include_references` and
  `include_reference_source_data` are enabled.
- **The request times out:** Increase `max_runtime_in_seconds`; don't lower it
  below the latency budget required by the remote tool.
- **Model authorization fails:** Grant the Search service managed identity
  Cognitive Services OpenAI User, or set `AZURE_OPENAI_API_KEY` locally.
- **A configured resource name already exists:** Choose different names in
  `.env`. The sample never updates or deletes a resource it didn't create.

## External service boundary

The Microsoft Learn MCP endpoint is public and unauthenticated, but content
still leaves the Search service boundary for the external tool call. Review
the MCP server's terms, data-handling behavior, network reachability, and
compliance fit before replacing the public sample with enterprise data.

References:

- [Create an MCP Server knowledge source](https://learn.microsoft.com/azure/search/agentic-knowledge-source-how-to-mcp-server)
- [Create a knowledge base](https://learn.microsoft.com/azure/search/agentic-retrieval-how-to-create-knowledge-base)
- [Retrieve from a knowledge base](https://learn.microsoft.com/azure/search/agentic-retrieval-how-to-retrieve)
