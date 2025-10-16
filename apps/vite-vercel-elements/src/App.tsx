import { useState } from "react";
import "./App.css";
import { useChat } from "@ai-sdk/react";
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "./components/conversation";
import {
  Source,
  Sources,
  SourcesContent,
  SourcesTrigger,
} from "./components/sources";
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "./components/reasoning";
import { Response } from "./components/response";
import { Loader } from "./components/loader";
import { Message, MessageContent } from "./components/message";
import {
  PromptInput,
  PromptInputButton,
  PromptInputModelSelect,
  PromptInputModelSelectContent,
  PromptInputModelSelectItem,
  PromptInputModelSelectTrigger,
  PromptInputModelSelectValue,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputToolbar,
  PromptInputTools,
} from "./components/prompt-input";
import {
  CopyIcon,
  GlobeIcon,
  RefreshCcwIcon,
  ThumbsDownIcon,
  ThumbsUpIcon,
} from "lucide-react";
import { DefaultChatTransport, type SourceUrlUIPart } from "ai";
import { mockMessages } from "./mockMessages";
import { Action, Actions } from "./components/actions";

const models = [
  {
    name: "GPT 4o",
    value: "openai/gpt-4o",
  },
  {
    name: "Deepseek R1",
    value: "deepseek/deepseek-r1",
  },
];

const ChatBotDemo = () => {
  const [input, setInput] = useState("");
  const [model, setModel] = useState<string>(models[0].value);
  const [webSearch, setWebSearch] = useState(false);
  const { messages, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({
      // api: "http://localhost:8001/chat",
      api: "http://localhost:8000/api/chat",
      headers: {
        Authorization: "dev.dev.dev",
      },
      prepareSendMessagesRequest: ({ id, messages }) => {
        return {
          body: {
            id,
            message: messages[messages.length - 1], // Send only the last message object
          },
        };
      },
    }),
    // messages: mockMessages,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      sendMessage(
        { text: input },
        {
          body: {
            model: model,
            webSearch: webSearch,
          },
        }
      );
      setInput("");
    }
  };

  const actions = [
    {
      icon: RefreshCcwIcon,
      label: "Retry",
      onClick: () => {},
    },
    {
      icon: ThumbsUpIcon,
      label: "Like",
      onClick: () => {},
    },

    {
      icon: ThumbsDownIcon,
      label: "Dislike",
      onClick: () => {},
    },
    {
      icon: CopyIcon,
      label: "Copy",
      onClick: () => {},
    },
    // {
    //   icon: ShareIcon,
    //   label: 'Share',
    //   onClick: () => handleShare(),
    // },
  ];

  return (
    <div className="relative size-full h-screen">
      <div className="flex flex-col h-full">
        <Conversation className="relative h-full">
          <ConversationContent>
            {messages.map((message) => (
              <div key={message.id}>
                <Message
                  from={message.role}
                  key={message.id}
                  className={`flex flex-col gap-2 ${
                    message.role === "assistant" ? "items-start" : "items-end"
                  }`}
                >
                  <MessageContent className="agent-chat-messages">
                    {message.parts.map((part, i) => {
                      switch (part.type) {
                        case "text":
                          return (
                            <Response key={`${message.id}-${i}`}>
                              {part.text}
                            </Response>
                          );
                        case "reasoning":
                          return (
                            <Reasoning
                              key={`${message.id}-${i}`}
                              className="w-full"
                              isStreaming={status === "streaming"}
                            >
                              <ReasoningTrigger />
                              <ReasoningContent>{part.text}</ReasoningContent>
                            </Reasoning>
                          );
                        default:
                          return null;
                      }
                    })}
                  </MessageContent>
                  {message.role === "assistant" && (
                    <Actions className="mt-2">
                      {actions.map((action) => (
                        <Action key={action.label} label={action.label}>
                          <action.icon className="size-4" />
                        </Action>
                      ))}
                    </Actions>
                  )}
                </Message>
                {message.role === "assistant" && (
                  <MessageSources
                    sources={message.parts.filter(
                      (part) => part.type === "source-url"
                    )}
                  />
                )}
              </div>
            ))}
            {status === "submitted" && <Loader />}
          </ConversationContent>
          <ConversationScrollButton />
        </Conversation>
        <div className="m-4">
          <PromptInput onSubmit={handleSubmit}>
            <PromptInputTextarea
              onChange={(e) => setInput(e.target.value)}
              value={input}
            />
            <PromptInputToolbar className="justify-end">
              {/* <PromptInputTools>
                <PromptInputButton
                  variant={webSearch ? "default" : "ghost"}
                  onClick={() => setWebSearch(!webSearch)}
                >
                  <GlobeIcon size={16} />
                  <span>Search</span>
                </PromptInputButton>
                <PromptInputModelSelect
                  onValueChange={(value) => {
                    setModel(value);
                  }}
                  value={model}
                >
                  <PromptInputModelSelectTrigger>
                    <PromptInputModelSelectValue />
                  </PromptInputModelSelectTrigger>
                  <PromptInputModelSelectContent>
                    {models.map((model) => (
                      <PromptInputModelSelectItem
                        key={model.value}
                        value={model.value}
                      >
                        {model.name}
                      </PromptInputModelSelectItem>
                    ))}
                  </PromptInputModelSelectContent>
                </PromptInputModelSelect>
              </PromptInputTools> */}
              <PromptInputSubmit disabled={!input} status={status} />
            </PromptInputToolbar>
          </PromptInput>
        </div>
      </div>
    </div>
  );
};

interface MessageSourcesProps {
  sources: SourceUrlUIPart[];
}
function MessageSources({ sources }: MessageSourcesProps) {
  if (!sources.length) return null;
  return (
    <Sources>
      <>
        <SourcesTrigger count={sources.length} />
        <SourcesContent>
          {sources.map((source) => (
            <Source
              key={source.sourceId}
              href={source.url}
              title={source.url}
            />
          ))}
        </SourcesContent>
      </>
    </Sources>
  );
}

export default ChatBotDemo;
