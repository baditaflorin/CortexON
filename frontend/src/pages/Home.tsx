import Chat from "@/components/home/Chat";
import Header from "@/components/home/Header";
import {Message} from "@/types/chatTypes";
import {useState} from "react";

const Home = () => {
  const [messages, setMessages] = useState<Message[]>([]);

  return (
    <div className="h-[100vh] w-[100vw]">
      <Header setMessages={setMessages} messages={messages} />
      <Chat setMessages={setMessages} messages={messages} />
    </div>
  );
};

export default Home;
