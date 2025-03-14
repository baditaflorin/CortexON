import {useRef, useState} from "react";
import Markdown from "react-markdown";
import {Prism as SyntaxHighlighter} from "react-syntax-highlighter";
import {tomorrow} from "react-syntax-highlighter/dist/esm/styles/prism";
import rehypeRaw from "rehype-raw";
import remarkBreaks from "remark-breaks";

export const CodeBlock = ({content}: {content: string}) => {
  const codeBlock = content.includes("content='")
    ? content.split("content='")[1]
    : content;

  const [isCopied, setIsCopied] = useState(false);
  const codeRef = useRef<HTMLDivElement>(null);

  const handleCopyClick = () => {
    if (codeRef.current) {
      navigator.clipboard
        .writeText(codeRef.current.innerText)
        .then(() => {
          setIsCopied(true);
          // Add a visual pulse effect
          if (codeRef.current) {
            codeRef.current.classList.add("copy-pulse");
            setTimeout(() => {
              if (codeRef.current) {
                codeRef.current.classList.remove("copy-pulse");
              }
            }, 1000);
          }
          setTimeout(() => setIsCopied(false), 2000);
        })
        .catch((err) => console.error("Failed to copy text: ", err));
    }
  };

  return (
    <div className="relative w-full overflow-x-auto scrollbar-thin text-sm leading-6 whitespace-pre">
      <button
        onClick={handleCopyClick}
        className="absolute top-4 right-4 bg-gray-700 text-white px-2 py-1 rounded text-xs hover:bg-gray-600 transition-colors duration-300"
      >
        {isCopied ? "Copied!" : "Copy"}
      </button>
      <div ref={codeRef}>
        <Markdown
          children={codeBlock.replace(/\\n/g, "\n")}
          rehypePlugins={[rehypeRaw]}
          remarkPlugins={[remarkBreaks]}
          components={{
            code(props) {
              const {children, className, ...rest} = props;
              const match = /language-(\w+)/.exec(className || "");
              return match ? (
                <SyntaxHighlighter
                  PreTag="div"
                  language={match[1] || "python"}
                  style={tomorrow}
                  className="animate-fade-in w-full overflow-x-auto scrollbar-thin"
                >
                  {String(children).replace(/\n$/, "")}
                </SyntaxHighlighter>
              ) : (
                <code {...rest} className={className}>
                  {children}
                </code>
              );
            },
          }}
        />
      </div>
    </div>
  );
};
