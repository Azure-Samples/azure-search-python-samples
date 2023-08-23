import React, { useState, useEffect } from "react";
import { ChatMessages } from "./components/ChatMessages";
import { ChatInput } from "./components/ChatInput";
import axios from "axios";

export const Chatbot = () => {
  const [messages, setMessages] = useState([]);

  const handleMessageSubmit = async (content) => {
    const newMessage = { role: "user", content };
    setMessages((prevMessages) => [...prevMessages, newMessage]);

    try {
      const response = await axios.post("/api/Chatbot", {
        messages: [...messages, newMessage],
        query: content,
      });

      const assistantResponse = response.data.choices[0].message.content; // Extract assistant's response

      const assistantMessage = {
        role: "assistant",
        content: assistantResponse,
      };
      setMessages((prevMessages) => [...prevMessages, assistantMessage]);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    console.log(messages);
  }, [messages]);

  return (
    <div className="flex-grow bg-slate-100 ml-64 mr-64 p-4 flex flex-col">
      <div className="bg-white rounded shadow-md overflow-hidden flex-1 flex flex-col">
        <h1 className="bg-neutral text-2xl text-white p-3 text-center">
          Chatbot
        </h1>
        <ChatMessages messages={messages} />
      </div>

      <div className="h-full">
        <ChatInput onSendMessage={handleMessageSubmit} />
      </div>
    </div>
  );
};
