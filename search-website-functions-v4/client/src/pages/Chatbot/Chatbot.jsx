import React, { useState, useEffect } from "react";
import { ChatMessages } from "./components/ChatMessages";
import { ChatInput } from "./components/ChatInput";
import axios from "axios";

export const Chatbot = () => {
  const [messages, setMessages] = useState(() => {
    const storedMessages = localStorage.getItem("chatMessages");
    return storedMessages ? JSON.parse(storedMessages) : [];
  });

  const handleMessageSubmit = async (content) => {
    const newMessage = { role: "user", content };
    const updatedMessages = [...messages, newMessage];
    setMessages(updatedMessages);
    localStorage.setItem("chatMessages", JSON.stringify(updatedMessages));

    try {
      const response = await axios.post("/api/Chatbot", {
        messages: updatedMessages,
        query: content,
      });

      const assistantResponse = response.data.choices[0].message.content; // extract chatbot response

      const assistantMessage = {
        role: "assistant",
        content: assistantResponse,
      };

      const updatedMessagesWithAssistant = [
        ...updatedMessages,
        assistantMessage,
      ];
      setMessages(updatedMessagesWithAssistant);
      localStorage.setItem(
        "chatMessages",
        JSON.stringify(updatedMessagesWithAssistant)
      );
    } catch (error) {
      console.error(error);
    }
  };
  const handleClearChat = () => {
    setMessages([]);
    localStorage.removeItem("chatMessages");
  };

  useEffect(() => {
    console.log(messages);
  }, [messages]);

  return (
    <div className="flex-grow bg-slate-100 ml-64 mr-64 p-4 flex flex-col">
      <div className="bg-white rounded shadow-md flex-1 flex flex-col overflow-hidden">
        <h1 className="bg-neutral text-2xl text-white p-3 text-center">
          Chatbot
        </h1>
        <ChatMessages messages={messages} />
      </div>

      <div className="h-full">
        <ChatInput
          onSendMessage={handleMessageSubmit}
          onClearChat={handleClearChat}
          messages={messages}
        />
      </div>
    </div>
  );
};
