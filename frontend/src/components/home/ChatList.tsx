import {BrainCircuit, Globe, SquareCode, SquareSlash} from "lucide-react";
import {useEffect, useRef, useState} from "react";
import favicon from "../../assets/Favicon-contexton.svg";
import {ScrollArea} from "../ui/scroll-area";

import Markdown from "react-markdown";
import rehypeRaw from "rehype-raw";
import remarkBreaks from "remark-breaks";
import {Skeleton} from "../ui/skeleton";

import {ChatListPageProps, SystemMessage} from "@/types/chatTypes";
import useWebSocket, {ReadyState} from "react-use-websocket";
import {Card} from "../ui/card";
import {CodeBlock} from "./CodeBlock";
import {ErrorAlert} from "./ErrorAlert";
import LoadingView from "./Loading";
import {TerminalBlock} from "./TerminalBlock";

const {VITE_WEBSOCKET_URL} = import.meta.env;

const getTimeAgo = (dateString: string): string => {
  const date =
    dateString.charAt(dateString.length - 1) === "Z"
      ? new Date(dateString)
      : new Date(dateString + "Z");

  const now = new Date();

  const diffTime = Math.abs(now.getTime() - date.getTime());
  const diffSeconds = Math.floor(diffTime / 1000);

  // Less than a minute
  if (diffSeconds < 60) {
    return `${diffSeconds} ${diffSeconds === 1 ? "second" : "seconds"} ago`;
  }

  // Less than an hour
  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) {
    return `${diffMinutes} ${diffMinutes === 1 ? "minute" : "minutes"} ago`;
  }

  // Less than a day
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 12) {
    return `${diffHours} ${diffHours === 1 ? "hour" : "hours"} ago`;
  }

  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return "Today";
  } else if (diffDays === 1) {
    return "Yesterday";
  } else if (diffDays < 7) {
    return `${diffDays} days ago`;
  } else if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7);
    return `${weeks} ${weeks === 1 ? "week" : "weeks"} ago`;
  } else if (diffDays < 365) {
    const months = Math.floor(diffDays / 30);
    return `${months} ${months === 1 ? "month" : "months"} ago`;
  } else {
    const years = Math.floor(diffDays / 365);
    return `${years} ${years === 1 ? "year" : "years"} ago`;
  }
};

const ChatList = ({
  messages,
  setMessages,
  isLoading,
  setIsLoading,
}: ChatListPageProps) => {
  const [isHovering, setIsHovering] = useState<boolean>(false);
  const [isIframeLoading, setIsIframeLoading] = useState<boolean>(true);
  const [liveUrl, setLiveUrl] = useState<string>("");
  const [animateIframeEntry, setAnimateIframeEntry] = useState<boolean>(false);

  // Create a ref for the scroll container
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Create another ref to track the previous messages length
  const prevMessagesLengthRef = useRef(0);
  const prevSystemMessageLengthRef = useRef(0);

  const {sendMessage, lastJsonMessage, readyState} = useWebSocket(
    VITE_WEBSOCKET_URL,
    {
      onOpen: () => {
        if (
          messages.length > 0 &&
          messages[0]?.prompt &&
          messages[0].prompt.length > 0
        ) {
          sendMessage(messages[0].prompt);
        }
      },
      onError: () => {
        setIsLoading(false);
      },
      reconnectAttempts: 3,
      retryOnError: true,
    }
  );

  const scrollToBottom = (smooth = true) => {
    if (scrollAreaRef.current) {
      // Get the actual scrollable div inside the ScrollArea component
      const scrollableDiv = scrollAreaRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (scrollableDiv) {
        // Find the last message element to scroll to
        const lastMessageElement = scrollAreaRef.current.querySelector(
          ".space-y-4 > div:last-child"
        );

        if (lastMessageElement) {
          // Use scrollIntoView for smooth scrolling behavior
          lastMessageElement.scrollIntoView({
            behavior: smooth ? "smooth" : "auto",
            block: "end",
          });
        } else {
          // Fallback to traditional scrollTop if element not found
          scrollableDiv.scrollTo({
            top: scrollableDiv.scrollHeight,
            behavior: smooth ? "smooth" : "auto",
          });
        }
      }
    }
  };

  useEffect(() => {
    if (!lastJsonMessage) return;

    setMessages((prev) => {
      const lastMessage = prev[prev.length - 1];
      if (lastMessage?.role === "system") {
        setIsLoading(true);

        const lastMessageData = lastMessage.data || [];
        const {agent_name, instructions, steps, output, status_code, live_url} =
          lastJsonMessage as SystemMessage;

        // Update live URL if provided
        if (live_url) {
          setLiveUrl(live_url);
          setIsIframeLoading(true);
          // Trigger animation for iframe container
          setAnimateIframeEntry(true);
        } else if (agent_name !== "Web Surfer Agent") {
          setLiveUrl("");
        }

        // Find the agent name in the last message data and update the fields
        const agentIndex = lastMessageData.findIndex(
          (agent) => agent.agent_name === agent_name
        );

        if (agentIndex !== -1) {
          let filteredSteps = steps;
          if (agent_name === "Web Surfer Agent") {
            const plannerStep = steps.find((step) => step.startsWith("Plan"));
            filteredSteps = plannerStep
              ? [
                  plannerStep,
                  ...steps.filter((step) => step.startsWith("Current")),
                ]
              : steps.filter((step) => step.startsWith("Current"));
          }
          lastMessageData[agentIndex] = {
            agent_name,
            instructions,
            steps: filteredSteps,
            output,
            status_code,
            live_url,
          };
        } else {
          lastMessageData.push({
            agent_name,
            instructions,
            steps,
            output,
            status_code,
            live_url,
          });
        }

        if (agent_name === "Orchestrator" && output && output.length > 0) {
          setIsLoading(false);
        }

        // Create a new array to ensure state update
        return [
          ...prev.slice(0, prev.length - 1),
          {
            ...lastMessage,
            data: [...lastMessageData],
          },
        ];
      }
      return [...prev];
    });

    if (lastJsonMessage && messages.length > 0) {
      setTimeout(scrollToBottom, 300);
    }
  }, [lastJsonMessage, messages.length, setIsLoading, setMessages]);

  const getOutputBlock = (type: string, output: string | undefined) => {
    if (!output) return null;

    switch (type) {
      case "Coder Agent":
        return <CodeBlock content={output} />;
      case "Code Executor Agent":
        return <TerminalBlock content={output} />;
      case "Executor Agent":
        return <TerminalBlock content={output} />;
      default:
        return (
          <span className="text-base break-words max-w-[95%]">
            <Markdown
              remarkPlugins={[remarkBreaks]}
              rehypePlugins={[rehypeRaw]}
            >
              {output}
            </Markdown>
          </span>
        );
    }
  };

  const getAgentIcon = (type: string) => {
    switch (type) {
      case "Coder Agent":
        return (
          <SquareCode size={20} absoluteStrokeWidth className="text-primary" />
        );

      case "Coder Executor Agent":
        return (
          <SquareSlash size={20} absoluteStrokeWidth className="text-primary" />
        );

      case "Executor Agent":
        return (
          <SquareSlash size={20} absoluteStrokeWidth className="text-primary" />
        );

      case "Web Surfer Agent":
        return <Globe size={20} absoluteStrokeWidth className="text-primary" />;

      default:
        return (
          <BrainCircuit
            size={20}
            absoluteStrokeWidth
            className="text-primary"
          />
        );
    }
  };

  useEffect(() => {
    // Only scroll if messages have been added
    const currentMessagesLength = messages.length;
    let shouldScroll = false;

    if (currentMessagesLength > prevMessagesLengthRef.current) {
      shouldScroll = true;
    } else if (
      currentMessagesLength > 0 &&
      messages[currentMessagesLength - 1].role === "system"
    ) {
      // Check if system message data has changed
      const systemMessage = messages[currentMessagesLength - 1];
      const currentSystemDataLength = systemMessage.data?.length || 0;

      if (currentSystemDataLength > prevSystemMessageLengthRef.current) {
        shouldScroll = true;
      }

      // Update system message data length ref
      prevSystemMessageLengthRef.current = currentSystemDataLength;
    }

    // Update messages length ref
    prevMessagesLengthRef.current = currentMessagesLength;

    // Scroll with a slight delay to ensure content has rendered
    if (shouldScroll) {
      setTimeout(scrollToBottom, 100);
    }
  }, [messages]);

  // Additional useEffect to handle scrolling on initial load
  useEffect(() => {
    // Initial scroll without smooth behavior for immediate positioning
    scrollToBottom(false);

    // Add window resize listener to maintain scroll position
    const handleResize = () => {
      scrollToBottom(false);
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  // Reset iframe animation flag when iframe is hidden
  useEffect(() => {
    if (!liveUrl) {
      setAnimateIframeEntry(false);
    }
  }, [liveUrl]);

  window.addEventListener("message", function (event) {
    if (event.data === "browserbase-disconnected") {
      console.log("Message received from iframe:", event.data);
      // Handle the disconnection logic here
      setLiveUrl("");
    }
  });

  // Calculate width based on whether liveUrl is present
  const chatContainerWidth = liveUrl ? "50%" : "65%";

  return (
    <div className="w-full h-full flex justify-center items-center px-4 gap-4">
      <div
        className="h-full flex flex-col items-center space-y-10 pt-8 transition-all duration-500 ease-in-out"
        style={{width: chatContainerWidth}}
      >
        <ScrollArea className="h-[95%] w-full" ref={scrollAreaRef}>
          <div className="space-y-4 pr-5 w-full">
            {messages.map((message, idx) => {
              return message.role === "user" ? (
                <div
                  className="flex flex-col justify-end items-end space-y-1 animate-fade-in animate-once animate-duration-300 animate-ease-in-out"
                  key={idx}
                  onMouseEnter={() => setIsHovering(true)}
                  onMouseLeave={() => setIsHovering(false)}
                >
                  {message.sent_at && message.sent_at.length > 0 && (
                    <p
                      className={`text-sm transition-colors duration-300 ease-in-out ${
                        !isHovering
                          ? "text-background"
                          : "text-muted-foreground"
                      }`}
                    >
                      {getTimeAgo(message.sent_at)}
                    </p>
                  )}
                  <div
                    className="bg-secondary text-secondary-foreground rounded-lg p-3 break-words 
                      max-w-[80%] transform transition-all duration-300 hover:shadow-md hover:-translate-y-1 animate-fade-right animate-once animate-duration-500"
                  >
                    {message.prompt}
                  </div>
                </div>
              ) : (
                <div
                  className="space-y-2 animate-fade-in animate-once animate-duration-500"
                  key={idx}
                >
                  {readyState === ReadyState.CONNECTING ? (
                    <>
                      <Skeleton className="h-[3vh] w-[10%] animate-pulse" />
                      <Skeleton className="h-[2vh] w-[80%] animate-pulse animate-delay-100" />
                      <Skeleton className="h-[2vh] w-[60%] animate-pulse animate-delay-200" />
                      <Skeleton className="h-[2vh] w-[40%] animate-pulse animate-delay-300" />
                    </>
                  ) : (
                    <>
                      <div className="flex item-center gap-4 animate-fade-down animate-once animate-duration-500">
                        <img
                          src={favicon}
                          className="animate-spin-slow animate-duration-3000 hover:animate-bounce"
                        />
                        <p className="text-2xl animate-fade-right animate-once animate-duration-700">
                          CortexOn
                        </p>
                      </div>
                      <div className="ml-12 max-w-[87%]">
                        {message.data?.map((systemMessage, index) =>
                          systemMessage.agent_name === "Orchestrator" ? (
                            <div
                              className="space-y-5 bg-background mb-4 max-w-full animate-fade-in animate-once animate-delay-300"
                              key={index}
                            >
                              <div className="flex flex-col gap-3 text-gray-300">
                                {systemMessage.steps &&
                                  systemMessage.steps.map((text, i) => (
                                    <div
                                      key={i}
                                      className="flex gap-2 text-gray-300 items-start animate-fade-left animate-once animate-duration-500"
                                      style={{
                                        animationDelay: `${i * 150}ms`,
                                      }}
                                    >
                                      <div className="h-4 w-4 flex-shrink-0 mt-[0.15rem] transition-transform duration-300 hover:scale-125">
                                        <SquareSlash
                                          size={20}
                                          absoluteStrokeWidth
                                          className="text-[#BD24CA]"
                                        />
                                      </div>
                                      <span className="text-base break-words">
                                        {text}
                                      </span>
                                    </div>
                                  ))}
                              </div>
                            </div>
                          ) : (
                            <Card
                              key={index}
                              className="p-4 bg-background mb-4 w-[98%] transition-all duration-500 ease-in-out transform hover:shadow-md hover:-translate-y-1 animate-fade-up animate-once animate-duration-700"
                              style={{animationDelay: `${index * 300}ms`}}
                            >
                              <div className="bg-secondary border flex items-center gap-2 mb-4 px-3 py-1 rounded-md w-max transform transition-transform duration-300 hover:scale-110 animate-fade-right animate-once animate-duration-500">
                                {getAgentIcon(systemMessage.agent_name)}
                                <span className="text-white text-base">
                                  {systemMessage.agent_name}
                                </span>
                              </div>
                              <div className="space-y-3 px-2">
                                <div className="flex flex-col gap-2 text-gray-300 animate-fade-in animate-once animate-duration-700">
                                  <span className="text-base break-words">
                                    {systemMessage.instructions}
                                  </span>
                                </div>
                                {systemMessage.steps &&
                                  systemMessage.steps.length > 0 && (
                                    <div className="flex flex-col gap-2 text-gray-300">
                                      <p className="text-muted-foreground text-base animate-fade-in animate-once animate-duration-500">
                                        Steps:
                                      </p>
                                      {systemMessage.steps.map((text, i) => (
                                        <div
                                          key={i}
                                          className="flex gap-2 text-gray-300 items-start animate-fade-in animate-once animate-duration-700"
                                          style={{
                                            animationDelay: `${i * 150}ms`,
                                          }}
                                        >
                                          <div className="h-4 w-4 flex-shrink-0 mt-[0.15rem] transition-transform duration-300 hover:scale-125">
                                            <SquareSlash
                                              size={20}
                                              absoluteStrokeWidth
                                              className="text-[#BD24CA]"
                                            />
                                          </div>
                                          <span className="text-base break-words">
                                            <Markdown
                                              rehypePlugins={[rehypeRaw]}
                                            >
                                              {text}
                                            </Markdown>
                                          </span>
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                {systemMessage.output && (
                                  <div className="flex flex-col gap-2 text-gray-300 w-[98%]">
                                    <p className="text-muted-foreground text-base animate-fade-in animate-once animate-duration-500">
                                      Output:
                                    </p>
                                    <div className="animate-fade-in animate-once animate-delay-500 animate-duration-1000 w-[98%]">
                                      {getOutputBlock(
                                        systemMessage.agent_name,
                                        systemMessage.output
                                      )}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </Card>
                          )
                        )}
                        {/* Add output of the orchestrator */}
                        {message.data &&
                          message.data.find(
                            (systemMessage) =>
                              systemMessage.agent_name === "Orchestrator" &&
                              systemMessage.output
                          ) && (
                            <div className="space-y-3 animate-fade-in animate-once animate-delay-700 animate-duration-1000 w-[98%]">
                              {message.data.find(
                                (systemMessage) =>
                                  systemMessage.agent_name === "Orchestrator"
                              )?.status_code === 200 ? (
                                <div className="flex flex-col gap-2 text-gray-300 w-[98%]">
                                  <p className="text-muted-foreground text-base animate-fade-in animate-once animate-duration-500">
                                    Summary:
                                  </p>
                                  <div className="transition-all duration-500 ease-in transform hover:translate-x-1 animate-fade-in animate-once animate-duration-1000 w-[98%]">
                                    {getOutputBlock(
                                      "Orchestrator",
                                      message.data.find(
                                        (systemMessage) =>
                                          systemMessage.agent_name ===
                                          "Orchestrator"
                                      )?.output
                                    )}
                                  </div>
                                </div>
                              ) : (
                                <ErrorAlert
                                  errorMessage={
                                    message.data.find(
                                      (systemMessage) =>
                                        systemMessage.agent_name ===
                                        "Orchestrator"
                                    )?.output
                                  }
                                />
                              )}
                            </div>
                          )}
                      </div>
                      {isLoading && <LoadingView />}
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </div>
      {liveUrl && (
        <div
          className={`border-2 rounded-xl w-[50%] flex flex-col h-[95%] justify-between items-center transition-all duration-700 ease-in-out ${
            animateIframeEntry
              ? "animate-fade-in animate-once animate-duration-1000"
              : "opacity-0"
          }`}
        >
          <div className="bg-secondary rounded-t-xl h-[8vh] w-full flex items-center justify-between px-8 animate-fade-down animate-once animate-duration-700">
            <p className="text-2xl text-secondary-foreground animate-fade-right animate-once animate-duration-700">
              Web Agent
            </p>
          </div>
          <div className="w-[98%]">
            {isIframeLoading && (
              <Skeleton className="h-[55vh] w-full rounded-none animate-pulse animate-infinite animate-duration-1500" />
            )}
            <iframe
              key={liveUrl}
              src={liveUrl}
              className={`w-full aspect-video bg-transparent transition-all duration-700 ${
                isIframeLoading
                  ? "opacity-0 scale-95"
                  : "opacity-100 scale-100 animate-fade-in animate-once animate-duration-1000"
              }`}
              title="Browser Preview"
              sandbox="allow-scripts allow-same-origin allow-modals allow-forms allow-popups"
              onLoad={() => {
                setTimeout(() => setIsIframeLoading(false), 300); // Delay to show transition
              }}
              onError={(e) => {
                console.error("Iframe load error:", e);
                setIsIframeLoading(false);
              }}
              style={{
                display: isIframeLoading ? "none" : "block",
                pointerEvents: "none",
                transformOrigin: "top left",
              }}
            />
          </div>
          <div className="bg-secondary h-[7vh] flex w-full rounded-b-xl justify-end px-4 animate-fade-up animate-once animate-duration-700">
            {/* Browser session footer */}
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatList;
