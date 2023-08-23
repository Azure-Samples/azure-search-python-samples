import React, { useState } from "react";

export const ChatInput = ({ onSendMessage }) => {
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

  return (
    <form className="flex p-3" onSubmit={handleSubmit}>
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
    </form>
  );
};
