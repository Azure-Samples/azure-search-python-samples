from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from azure.core.credentials import AzureKeyCredential, TokenCredential
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


DEFAULT_QUERY = """
Use the indexed Contoso Trail Guide release brief to state the Wave B date and
response-time SLO. Then use the current Microsoft Learn MCP Server knowledge
source guide to identify the exact `maxRuntimeInSeconds` request property that
should exceed that SLO and explain how the `activity` and `references` response
sections prove that both sources participated. Return one recommendation that
cites facts from both source types.
""".strip()


@dataclass(frozen=True)
class Settings:
    search_endpoint: str
    azure_openai_endpoint: str
    azure_openai_deployment: str
    azure_openai_model: str
    index_name: str = "foundry-iq-multi-source-index"
    search_knowledge_source_name: str = "foundry-iq-search-source"
    mcp_knowledge_source_name: str = "foundry-iq-learn-mcp-source"
    knowledge_base_name: str = "foundry-iq-multi-source-kb"
    mcp_server_url: str = "https://learn.microsoft.com/api/mcp"
    mcp_tool_name: str = "microsoft_docs_search"
    search_api_key: str | None = None
    azure_openai_api_key: str | None = None

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        return cls(
            search_endpoint=_required("SEARCH_ENDPOINT"),
            azure_openai_endpoint=_required("AZURE_OPENAI_ENDPOINT").rstrip("/"),
            azure_openai_deployment=_required("AZURE_OPENAI_DEPLOYMENT"),
            azure_openai_model=_required("AZURE_OPENAI_MODEL"),
            index_name=os.getenv("INDEX_NAME", cls.index_name),
            search_knowledge_source_name=os.getenv(
                "SEARCH_KNOWLEDGE_SOURCE_NAME",
                cls.search_knowledge_source_name,
            ),
            mcp_knowledge_source_name=os.getenv(
                "MCP_KNOWLEDGE_SOURCE_NAME",
                cls.mcp_knowledge_source_name,
            ),
            knowledge_base_name=os.getenv(
                "KNOWLEDGE_BASE_NAME",
                cls.knowledge_base_name,
            ),
            mcp_server_url=os.getenv("MCP_SERVER_URL", cls.mcp_server_url),
            mcp_tool_name=os.getenv("MCP_TOOL_NAME", cls.mcp_tool_name),
            search_api_key=os.getenv("SEARCH_API_KEY"),
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        )

    @property
    def data_path(self) -> Path:
        return Path(__file__).resolve().parents[2] / "data" / "release-brief.json"

    @property
    def output_path(self) -> Path:
        return Path(__file__).resolve().parents[2] / ".outputs" / "latest-result.json"

    @property
    def manifest_path(self) -> Path:
        return Path(__file__).resolve().parents[2] / ".outputs" / "resources.json"

    def search_credential(self) -> AzureKeyCredential | TokenCredential:
        if self.search_api_key:
            return AzureKeyCredential(self.search_api_key)
        return DefaultAzureCredential()


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing {name}. Copy sample.env to .env and set the required values."
        )
    return value
