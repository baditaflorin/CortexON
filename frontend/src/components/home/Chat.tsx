import {ChatPageProps} from "@/types/chatTypes";

import {useState} from "react";
import ChatList from "./ChatList";
import Landing from "./Landing";

const Chat = ({messages, setMessages}: ChatPageProps) => {
  const [isLoading, setIsLoading] = useState<boolean>(false);

  return (
    <div className="flex justify-center items-center h-[92vh] overflow-auto scrollbar-thin">
      {messages.length === 0 ? (
        <Landing
          messages={messages}
          setMessages={setMessages}
          isLoading={isLoading}
          setIsLoading={setIsLoading}
        />
      ) : (
        <ChatList
          messages={messages}
          setMessages={setMessages}
          isLoading={isLoading}
          setIsLoading={setIsLoading}
        />
      )}
    </div>
  );
};

export default Chat;
