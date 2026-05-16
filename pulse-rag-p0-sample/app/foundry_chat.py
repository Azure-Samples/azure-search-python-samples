from __future__ import annotations

from dataclasses import dataclass
import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


class FoundryChatError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class FoundryChatSettings:
    project_endpoint: str
    agent_name: str
    tool_choice: str


@dataclass(frozen=True, slots=True)
class ChatReply:
    conversation_id: str
    answer: str
    response_id: str | None


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
        agent_name = os.getenv("AGENT_NAME")

        if not project_endpoint:
            raise FoundryChatError("PROJECT_ENDPOINT is required for the chat app.")
        if not agent_name:
            raise FoundryChatError("AGENT_NAME is required for the chat app.")

        settings = FoundryChatSettings(
            project_endpoint=project_endpoint,
            agent_name=agent_name,
            tool_choice=os.getenv("TOOL_CHOICE", "required"),
        )
        return cls(settings)

    def create_conversation(self) -> str:
        conversation = self.openai_client.conversations.create()
        return conversation.id

    def send_message(self, message: str, conversation_id: str | None = None) -> ChatReply:
        normalized_message = message.strip()
        if not normalized_message:
            raise FoundryChatError("Message cannot be empty.")

        active_conversation_id = conversation_id or self.create_conversation()
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

        return ChatReply(
            conversation_id=active_conversation_id,
            answer=response.output_text,
            response_id=getattr(response, "id", None),
        )
