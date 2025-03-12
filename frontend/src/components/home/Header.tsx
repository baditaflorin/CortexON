import {ChatPageProps} from "@/types/chatTypes";
import {MessageCirclePlus} from "lucide-react";
import Logo from "../../assets/CortexON_logo_dark.svg";
import {Button} from "../ui/button";
const Header = ({setMessages}: ChatPageProps) => {
  return (
    <div className="h-[8vh] border-b-2 flex justify-between items-center px-8">
      <div className="w-[12%]" onClick={() => setMessages([])}>
        <img src={Logo} alt="Logo" />
      </div>
      <Button onClick={() => setMessages([])}>
        <MessageCirclePlus size={20} absoluteStrokeWidth />
        New Chat
      </Button>
    </div>
  );
};

export default Header;
