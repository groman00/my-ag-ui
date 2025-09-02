"use client";
import React, { useState } from "react";
import "@copilotkit/react-ui/styles.css";
import "./style.css";
import { CopilotKit, useCopilotAction } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";

// interface AgenticChatProps {}

const AgenticChat: React.FC = () => {
  return (
    <CopilotKit
      runtimeUrl={`/api/chat`}
      showDevConsole={true}
      // agent lock to the relevant agent
      agent="agentic_chat"
    >
      <Chat />
    </CopilotKit>
  );
};

const Chat = () => {
  const [background, setBackground] = useState<string>(
    "--copilot-kit-background-color"
  );

  // Tools
  // There can be more than one of these
  useCopilotAction({
    name: "change_background",
    description:
      "Change the background color of the chat. Can be anything that the CSS background attribute accepts. Regular colors, linear of radial gradients etc.",
    parameters: [
      {
        name: "background",
        type: "string",
        description: "The background. Prefer gradients.",
      },
    ],
    handler: ({ background }) => {
      setBackground(background);
      return {
        status: "success",
        message: `Background changed to ${background}`,
      };
    },
  });

  useCopilotAction({
    name: "dinner_suggest",
    description:
      "Suggest a dinner option.  If the user wants something savory, suggest a hot chicken dish.  If the user wants something sweet, suggest a dessert.",
    parameters: [
      {
        name: "dinner",
        type: "string",
        description: "The dinner. Prefer savory or sweet.",
      },
    ],
    handler: ({ dinner }) => {
      return {
        status: "success",
        message: `How about ${dinner}`,
      };
    },
  });

  return (
    <div
      className="flex justify-center items-center h-full w-full"
      style={{ background }}
    >
      <div className="h-full w-full md:w-8/10 md:h-8/10 rounded-lg">
        <CopilotChat
          className="h-full rounded-2xl"
          labels={{ initial: "Hi, I'm an agent. Want to chat?" }}
        />
      </div>
    </div>
  );
};

export default AgenticChat;
