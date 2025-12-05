import os
import json
import requests
from dataclasses import dataclass
from dotenv import load_dotenv

from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential


@dataclass
class SearchService:
    endpoint: str
    api_key: str

    def get_search_client(self, index_name: str) -> SearchClient:
        if self.api_key:
            # Use API key authentication if available
            credential = AzureKeyCredential(self.api_key)
        else:
            # Use Azure Active Directory (AAD) authentication if API key is empty
            credential = DefaultAzureCredential()

        return SearchClient(
            endpoint=self.endpoint,
            index_name=index_name,
            credential=credential,
        )

    @classmethod
    def from_env(cls) -> "SearchService":
        """Create a SearchService instance from environment variables."""
        load_dotenv()
        endpoint = os.getenv(f"AZURE_SEARCH_ENDPOINT")
        api_key = os.getenv(f"AZURE_SEARCH_API_KEY")

        return cls(endpoint=endpoint, api_key=api_key)


def knowledge_base_retrieval(
    search_service: SearchService,
    kb_name: str,
    question: str,
    answer_synthesis: bool = True,
    enable_image_serving: bool = False,
):
    endpoint = f"{search_service.endpoint}/knowledgebases/{kb_name}/retrieve"
    params = {
        "api-version": "2025-11-01-preview",
        "enable-image-serving": str(enable_image_serving).lower(),
    }
    payload = {
        "retrievalReasoningEffort": {"kind": "medium"},
        "outputMode": "answerSynthesis" if answer_synthesis else "extractiveData",
        "messages": [{"role": "user", "content": [{"text": question, "type": "text"}]}],
    }
    headers = {"Content-Type": "application/json", "api-key": search_service.api_key}

    response = requests.post(
        endpoint, params=params, headers=headers, data=json.dumps(payload)
    )

    return response.json()
