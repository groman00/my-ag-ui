import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

export async function POST(request: NextRequest) {
  // const body = await request.json();
  // console.log({ request: body });
  const runtime = new CopilotRuntime({
    agents: {
      agentic_chat: new HttpAgent({ url: "http://localhost:8000/" }),
    },
  });
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter: new ExperimentalEmptyAdapter(),
    endpoint: `/api/chat`,
  });

  return handleRequest(request);
}
