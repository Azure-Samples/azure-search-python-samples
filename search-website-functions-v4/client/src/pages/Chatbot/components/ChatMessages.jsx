import React, { useRef, useEffect } from "react";

export const ChatMessages = ({ messages }) => {
  const messagesContainerRef = useRef(null);

  useEffect(() => {
    // Scroll to the bottom of the container with smooth animation
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop =
        messagesContainerRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="flex-grow flex flex-col justify-end p-5 h-96 overflow-hidden">
      <div
        ref={messagesContainerRef}
        className="flex-grow overflow-y-scroll overflow-x-hidden transition-all ease-in-out duration-300 custom-scrollbar p-3"
        style={{ scrollBehavior: "smooth" }}
      >
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
    </div>
  );
};
