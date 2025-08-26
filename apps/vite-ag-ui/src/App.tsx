import "./App.css";
import { CopilotKit, useCopilotAction } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";

function App() {
  return (
    <CopilotKit
      // runtimeUrl={`/api/chat`}
      runtimeUrl="http://localhost:3002/runtime"
      showDevConsole={true}
      // agent lock to the relevant agent
      agent="agentic_chat"
    >
      <Chat />
    </CopilotKit>
  );
}

const Chat = () => {
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
      // style={{ background }}
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

export default App;
