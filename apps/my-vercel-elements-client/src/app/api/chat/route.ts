import { streamText, UIMessage, convertToModelMessages } from "ai";
import { google } from "@ai-sdk/google";

// Allow streaming responses up to 30 seconds
export const maxDuration = 30;

export async function POST(req: Request) {
  const json = await req.json();
  console.log({ request: json });
  const {
    messages,
    model,
    webSearch,
  }: { messages: UIMessage[]; model: string; webSearch: boolean } = json;

  const result = streamText({
    // model: webSearch ? "perplexity/sonar" : model,
    model: google("gemini-2.5-flash"),
    messages: convertToModelMessages(messages),
    system:
      // "You are a helpful assistant that can answer questions and help with tasks",
      "You are a helpful assistant that can convert colors into hex codes.  You can do nothing else.",
  });

  // send sources and reasoning back to the client
  return result.toUIMessageStreamResponse({
    sendSources: true,
    sendReasoning: true,
  });
}
