import {useEffect, useRef, useState} from "react";

export const TerminalBlock = ({content}: {content: string}) => {
  const [displayedContent, setDisplayedContent] = useState("");
  const [isTyping, setIsTyping] = useState(true);
  const terminalRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    let index = 0;
    const normalizedContent = content.replace(/\\n/g, "\n");

    setIsTyping(true);
    setDisplayedContent(""); // Reset content when content prop changes

    // Terminal typing effect
    const typeEffect = () => {
      if (index < normalizedContent.length) {
        setDisplayedContent((prev) => prev + normalizedContent.charAt(index));
        index++;

        // Auto-scroll to bottom as content is being typed
        if (terminalRef.current) {
          terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
        }

        timer = setTimeout(typeEffect, 5);
      } else {
        setIsTyping(false);
      }
    };

    timer = setTimeout(typeEffect, 10);

    return () => clearTimeout(timer);
  }, [content]);

  // Function to convert plain text to HTML (handling line breaks and basic formatting)
  const formatTerminalOutput = (text: string) => {
    // Add styling for command prompts to match your UI theme
    return text
      .replace(/\n/g, "<br/>")
      .replace(/\*\*(.*?)\*\*/g, "<strong class='text-primary'>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em class='text-secondary'>$1</em>")
      .replace(/\$(.*?)$/gm, "<span class='text-emerald-500'>$ $1</span>");
  };

  // Custom CSS for blinking cursor
  const blinkingCursorStyle = {
    display: "inline-block",
    width: "2px",
    height: "16px",
    backgroundColor: "#10B981", // green-500
    position: "absolute" as const,
    bottom: "16px",
    marginLeft: "2px",
    animation: "blink 1s step-end infinite",
  };

  // Adding keyframes for the blinking animation to the document
  useEffect(() => {
    // Create and append the style element for the blinking animation
    const styleElement = document.createElement("style");
    styleElement.textContent = `
      @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0; }
      }
    `;
    document.head.appendChild(styleElement);

    // Clean up when component unmounts
    return () => {
      document.head.removeChild(styleElement);
    };
  }, []);

  return (
    <div className="relative">
      <pre
        ref={terminalRef}
        className="overflow-auto p-2 text-sm leading-6 text-gray-300 font-mono"
        style={{
          maxWidth: "100%",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
        dangerouslySetInnerHTML={{
          __html: formatTerminalOutput(displayedContent),
        }}
      />

      {isTyping && <span style={blinkingCursorStyle} />}
    </div>
  );
};
