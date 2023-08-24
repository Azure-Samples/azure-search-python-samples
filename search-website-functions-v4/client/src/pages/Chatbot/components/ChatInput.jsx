import React, { useState } from "react";

export const ChatInput = ({ onSendMessage, onClearChat, messages }) => {
  const [inputText, setInputText] = useState("");

  const handleInputChange = (event) => {
    setInputText(event.target.value);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (inputText.trim() !== "") {
      onSendMessage(inputText);
      setInputText("");
    }
  };

  const handleClearChatClick = () => {
    const shouldClear = window.confirm("¿Seguro que quieres borrar el chat?");
    if (shouldClear) {
      onClearChat();
    }
  };

  return (
    <form className="flex p-3 gap-3" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Escribe aqui"
        className="input input-bordered w-full"
        value={inputText}
        onChange={handleInputChange}
      />
      <button type="submit" className="btn btn-neutral">
        Enviar
      </button>
      <button
        className="btn btn-error"
        onClick={handleClearChatClick}
        disabled={messages.length === 0}
      >
        Limpiar Chat
      </button>
    </form>
  );
};
