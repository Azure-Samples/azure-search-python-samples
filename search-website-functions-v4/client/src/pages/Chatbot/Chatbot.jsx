import React, { useState } from "react";
import { ChatMessages } from "./components/ChatMessages";
import { ChatInput } from "./components/ChatInput";

export const Chatbot = () => {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hello, how can I assist you?" },
  ]);

  const handleSendMessage = (content) => {
    const newMessage = { role: "user", content };
    setMessages([...messages, newMessage]);
    //implement chatbot api
  };

  return (
    <div className="flex-grow bg-slate-100 ml-64 mr-64 p-4 flex flex-col">
      <div className="bg-white rounded shadow-md overflow-hidden flex-1 flex flex-col">
        <h1 className="bg-neutral text-2xl text-white p-3 text-center">
          Chatbot
        </h1>
        <ChatMessages messages={messages} />
      </div>

      <div className="h-full">
        <ChatInput onSendMessage={handleSendMessage} />
      </div>
    </div>
  );
};
