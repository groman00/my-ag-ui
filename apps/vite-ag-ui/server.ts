import express from "express";
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNodeHttpEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";

const app = express();
const port = 3002;

app.use(express.static("dist"));

app.post("/runtime", (req, res) => {
  const runtime = new CopilotRuntime({
    agents: {
      agentic_chat: new HttpAgent({ url: "http://localhost:8000/" }),
    },
  });
  const handler = copilotRuntimeNodeHttpEndpoint({
    runtime,
    serviceAdapter: new ExperimentalEmptyAdapter(),
    endpoint: `/runtime`,
  });

  return handler(req, res);
});

app.listen(port, () => {
  console.log(`Example app listening on port ${port}`);
});
