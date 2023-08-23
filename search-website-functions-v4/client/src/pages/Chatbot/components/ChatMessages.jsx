import React from "react";

export const ChatMessages = ({ messages }) => {
  console.log(messages);
  return (
    <div className="flex-grow flex flex-col justify-end p-5">
      {messages.map((message, index) => (
        <div
          key={index}
          className={`chat ${
            message.role === "user" ? "chat-end" : "chat-start"
          }`}
        >
          <div className="chat-bubble">{message.content}</div>
        </div>
      ))}
    </div>
  );
};
