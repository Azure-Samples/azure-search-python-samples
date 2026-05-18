"""Foundry-backed chat service with retrieval grounding from Azure AI Search.

Two modes are supported, both of which use the Foundry project's hosted OpenAI
client and persist conversation state on the Foundry conversations API:

1. **Direct RAG** (default): the chat app retrieves grounding chunks from
   Azure AI Search and calls the OpenAI Responses API with a grounded system
   prompt. This is the out-of-the-box demo path and needs no agent
   provisioning.

2. **Agent reference**: if `AGENT_NAME` is set, the chat app delegates to a
   named Foundry agent via the `agent_reference` extension. Use this when you
   have already authored an agent in the Foundry portal with the same Azure AI
   Search index attached as a knowledge source.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from retrieval import RetrievedChunk, retrieve_context

try:  # Optional: embed the user's query for vector retrieval when configured.
    from openai import AzureOpenAI
except ImportError:  # pragma: no cover
    AzureOpenAI = None  # type: ignore[assignment]


_SYSTEM_PROMPT = (
    "You are the Pulse RAG assistant. Answer questions about the devices in "
    "the customer's environment using only the grounding context provided. "
    "If the answer is not in the context, say you do not know and suggest "
    "which device or room to ask about. Cite source ids in parentheses, e.g. "
    "(device-003)."
)


class FoundryChatError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class FoundryChatSettings:
    project_endpoint: str
    chat_model_deployment: str
    embedding_deployment: Optional[str]
    agent_name: Optional[str]
    tool_choice: str
    top_k: int


@dataclass(frozen=True, slots=True)
class ChatReply:
    conversation_id: str
    answer: str
    response_id: Optional[str]
    citations: list[str]


class FoundryChatService:
    def __init__(self, settings: FoundryChatSettings):
        self.settings = settings
        self.credential = DefaultAzureCredential()
        self.project_client = AIProjectClient(
            endpoint=self.settings.project_endpoint,
            credential=self.credential,
        )
        self.openai_client = self.project_client.get_openai_client()

    @classmethod
    def from_env(cls) -> "FoundryChatService":
        project_endpoint = os.getenv("PROJECT_ENDPOINT")
        chat_model = os.getenv("CHAT_MODEL_DEPLOYMENT")
        if not project_endpoint:
            raise FoundryChatError("PROJECT_ENDPOINT is required for the chat app.")
        if not chat_model:
            raise FoundryChatError(
                "CHAT_MODEL_DEPLOYMENT is required (the Azure OpenAI chat model deployment name)."
            )

        settings = FoundryChatSettings(
            project_endpoint=project_endpoint,
            chat_model_deployment=chat_model,
            embedding_deployment=os.getenv("EMBEDDING_DEPLOYMENT") or None,
            agent_name=os.getenv("AGENT_NAME") or None,
            tool_choice=os.getenv("TOOL_CHOICE", "auto"),
            top_k=int(os.getenv("RETRIEVAL_TOP_K", "5")),
        )
        return cls(settings)

    def create_conversation(self) -> str:
        conversation = self.openai_client.conversations.create()
        return conversation.id

    def _embed_query(self, query: str) -> Optional[list[float]]:
        deployment = self.settings.embedding_deployment
        if not deployment:
            return None
        try:
            response = self.openai_client.embeddings.create(model=deployment, input=query)
            return response.data[0].embedding
        except Exception:  # noqa: BLE001
            return None

    def _retrieve(self, query: str) -> list[RetrievedChunk]:
        vector = self._embed_query(query)
        return retrieve_context(query, top=self.settings.top_k, query_vector=vector)

    @staticmethod
    def _format_context(chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "No grounding context was retrieved."
        blocks = []
        for chunk in chunks:
            blocks.append(
                f"[source: {chunk.source_id} | title: {chunk.title}]\n{chunk.content}"
            )
        return "\n\n---\n\n".join(blocks)

    def send_message(self, message: str, conversation_id: str | None = None) -> ChatReply:
        normalized_message = message.strip()
        if not normalized_message:
            raise FoundryChatError("Message cannot be empty.")

        active_conversation_id = conversation_id or self.create_conversation()

        if self.settings.agent_name:
            response = self.openai_client.responses.create(
                conversation=active_conversation_id,
                tool_choice=self.settings.tool_choice,
                input=normalized_message,
                extra_body={
                    "agent": {
                        "name": self.settings.agent_name,
                        "type": "agent_reference",
                    }
                },
            )
            citations: list[str] = []
        else:
            chunks = self._retrieve(normalized_message)
            grounded_input = (
                f"Question: {normalized_message}\n\n"
                f"Grounding context:\n{self._format_context(chunks)}"
            )
            response = self.openai_client.responses.create(
                conversation=active_conversation_id,
                model=self.settings.chat_model_deployment,
                instructions=_SYSTEM_PROMPT,
                input=grounded_input,
            )
            citations = sorted({chunk.source_id for chunk in chunks if chunk.source_id})

        return ChatReply(
            conversation_id=active_conversation_id,
            answer=response.output_text,
            response_id=getattr(response, "id", None),
            citations=citations,
        )
