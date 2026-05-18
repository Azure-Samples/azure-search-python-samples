const STORAGE_KEY = "pulse-rag-p0-chat";

const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message");
const resetButton = document.getElementById("reset-chat");
const statusPill = document.getElementById("conversation-status");
const messageTemplate = document.getElementById("message-template");

function loadMessages() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveMessages(messages) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
}

function renderMessages(messages) {
  chatLog.innerHTML = "";
  if (!messages.length) {
    appendMessage("assistant", "Ask about a device or a recent update to start a persistent Foundry-backed conversation.");
    return;
  }

  for (const message of messages) {
    appendMessage(message.role, message.content);
  }
}

function appendMessage(role, content) {
  const fragment = messageTemplate.content.cloneNode(true);
  const root = fragment.querySelector(".message");
  root.classList.add(role);
  fragment.querySelector(".message-role").textContent = role === "user" ? "User" : "Assistant";
  fragment.querySelector(".message-body").textContent = content;
  chatLog.appendChild(fragment);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function refreshConversationStatus() {
  const response = await fetch("/api/session");
  const payload = await response.json();
  statusPill.textContent = payload.hasConversation
    ? `Conversation active: ${payload.conversationId}`
    : "No conversation yet";
}

async function sendMessage(message) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }

  return payload;
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) {
    return;
  }

  const messages = loadMessages();
  messages.push({ role: "user", content: message });
  saveMessages(messages);
  renderMessages(messages);
  messageInput.value = "";
  statusPill.textContent = "Waiting for Foundry response...";

  try {
    const payload = await sendMessage(message);
    const answerText = payload.citations && payload.citations.length
      ? `${payload.answer}\n\nSources: ${payload.citations.join(", ")}`
      : payload.answer;
    messages.push({ role: "assistant", content: answerText });
    saveMessages(messages);
    renderMessages(messages);
    statusPill.textContent = `Conversation active: ${payload.conversationId}`;
  } catch (error) {
    messages.push({ role: "assistant", content: `Error: ${error.message}` });
    saveMessages(messages);
    renderMessages(messages);
    statusPill.textContent = "Conversation error";
  }
});

resetButton.addEventListener("click", async () => {
  await fetch("/api/reset", { method: "POST" });
  localStorage.removeItem(STORAGE_KEY);
  renderMessages([]);
  statusPill.textContent = "No conversation yet";
});

renderMessages(loadMessages());
refreshConversationStatus();
