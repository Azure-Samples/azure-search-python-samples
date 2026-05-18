from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session

from foundry_chat import FoundryChatError, FoundryChatService
from sync_inspector import bp as sync_inspector_bp


load_dotenv(override=False)


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv(
    "FLASK_SESSION_SECRET",
    "pulse-rag-dev-only-secret",
)
app.register_blueprint(sync_inspector_bp)

chat_service: FoundryChatService | None = None
chat_service_error: str | None = None


def get_chat_service() -> FoundryChatService:
    global chat_service, chat_service_error

    if chat_service is not None:
        return chat_service

    if chat_service_error is not None:
        raise FoundryChatError(chat_service_error)

    try:
        chat_service = FoundryChatService.from_env()
    except FoundryChatError as exc:
        chat_service_error = str(exc)
        raise

    return chat_service


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.get("/api/session")
def session_state():
    return jsonify(
        {
            "conversationId": session.get("conversation_id"),
            "hasConversation": bool(session.get("conversation_id")),
            "configured": chat_service_error is None,
            "configurationError": chat_service_error,
        }
    )


@app.post("/api/chat")
def chat():
    req_body = request.get_json(silent=True) or {}
    message = str(req_body.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    conversation_id = session.get("conversation_id")

    try:
        service = get_chat_service()
        reply = service.send_message(message, conversation_id=conversation_id)
    except FoundryChatError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Foundry request failed: {exc}"}), 502

    session["conversation_id"] = reply.conversation_id
    return jsonify(
        {
            "conversationId": reply.conversation_id,
            "answer": reply.answer,
            "responseId": reply.response_id,
            "citations": reply.citations,
        }
    )


@app.post("/api/reset")
def reset():
    previous_conversation_id = session.pop("conversation_id", None)
    return jsonify(
        {
            "reset": True,
            "previousConversationId": previous_conversation_id,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=True)
