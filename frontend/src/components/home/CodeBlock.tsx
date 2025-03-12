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

  // Extract filename if it exists in the format "# filename: <filename>"
  let filename = "example.py";
  const filenameMatch = codeBlock.match(/# filename: ([^\n]+)/);
  if (filenameMatch && filenameMatch[1]) {
    filename = filenameMatch[1].trim();
  }

  const [isCopied, setIsCopied] = useState(false);
  const codeRef = useRef<HTMLDivElement>(null);

  const handleCopyClick = () => {
    if (codeRef.current) {
      navigator.clipboard
        .writeText(codeRef.current.innerText)
        .then(() => {
          setIsCopied(true);
          setTimeout(() => setIsCopied(false), 2000);
        })
        .catch((err) => console.error("Failed to copy text: ", err));
    }
  };

  return (
    <div className="w-full transition-all duration-300 transform">
      <div className="rounded-lg w-full bg-zinc-900 overflow-hidden shadow-lg transition-all duration-300">
        <div className="flex items-center justify-between px-4 py-2 bg-zinc-800/50 transition-colors duration-300">
          <span className="text-sm text-gray-400">{filename}</span>
          <div className="flex space-x-2">
            <div className="w-3 h-3 rounded-full bg-red-500 opacity-60 transition-opacity duration-300 hover:opacity-100"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500 opacity-60 transition-opacity duration-300 hover:opacity-100"></div>
            <div className="w-3 h-3 rounded-full bg-green-500 opacity-60 transition-opacity duration-300 hover:opacity-100"></div>
          </div>
        </div>
        <div className="relative overflow-x-auto [&::-webkit-scrollbar]:h-2 [&::-webkit-scrollbar-track]:bg-zinc-800 [&::-webkit-scrollbar-thumb]:bg-zinc-700 [&::-webkit-scrollbar-thumb]:rounded-full text-sm leading-6 whitespace-pre py-2 px-1">
          <button
            onClick={handleCopyClick}
            className="absolute top-2 right-2 bg-gray-700 text-white px-2 py-1 rounded text-xs hover:bg-gray-600 transition-colors duration-300"
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
                      language={match[1]}
                      style={tomorrow}
                      className="animate-fade-in"
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
      </div>
    </div>
  );
};
