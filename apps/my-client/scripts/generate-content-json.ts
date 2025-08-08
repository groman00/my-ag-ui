import fs from "fs";
import path from "path";

// Function to parse agents.ts file and extract agent keys without executing
function parseAgentsFile(): Array<{ id: string; agentKeys: string[] }> {
  const agentsFilePath = path.join(__dirname, "../src/agents.ts");
  const agentsContent = fs.readFileSync(agentsFilePath, "utf8");

  const agentConfigs: Array<{ id: string; agentKeys: string[] }> = [];

  // Split the content to process each agent configuration individually
  const agentBlocks = agentsContent.split(/(?=\s*{\s*id:\s*["'])/);

  for (const block of agentBlocks) {
    // Extract the ID
    const idMatch = block.match(/id:\s*["']([^"']+)["']/);
    if (!idMatch) continue;

    const id = idMatch[1];

    // Find the return object by looking for the pattern and then manually parsing balanced braces
    const returnMatch = block.match(/agents:\s*async\s*\(\)\s*=>\s*{\s*return\s*{/);
    if (!returnMatch) continue;

    const startIndex = returnMatch.index! + returnMatch[0].length;
    const returnObjectContent = extractBalancedBraces(block, startIndex);

    // Extract keys from the return object - only capture keys that are followed by a colon and then 'new'
    // This ensures we only get the top-level keys like "agentic_chat: new ..." not nested keys like "url: ..."
    const keyRegex = /^\s*(\w+):\s*new\s+\w+/gm;
    const keys: string[] = [];
    let keyMatch;
    while ((keyMatch = keyRegex.exec(returnObjectContent)) !== null) {
      keys.push(keyMatch[1]);
    }

    agentConfigs.push({ id, agentKeys: keys });
  }

  return agentConfigs;
}

// Helper function to extract content between balanced braces
function extractBalancedBraces(text: string, startIndex: number): string {
  let braceCount = 0;
  let i = startIndex;

  while (i < text.length) {
    if (text[i] === "{") {
      braceCount++;
    } else if (text[i] === "}") {
      if (braceCount === 0) {
        // Found the closing brace for the return object
        return text.substring(startIndex, i);
      }
      braceCount--;
    }
    i++;
  }

  return "";
}

const agentConfigs = parseAgentsFile();

const featureFiles = ["page.tsx", "style.css", "README.mdx"];

async function getFile(_filePath: string | undefined, _fileName?: string) {
  if (!_filePath) {
    console.warn(`File path is undefined, skipping.`);
    return {};
  }

  const fileName = _fileName ?? _filePath.split("/").pop() ?? "";
  const filePath = _fileName ? path.join(_filePath, fileName) : _filePath;

  // Check if it's a remote URL
  const isRemoteUrl = _filePath.startsWith("http://") || _filePath.startsWith("https://");

  let content: string;

  try {
    if (isRemoteUrl) {
      // Convert GitHub URLs to raw URLs for direct file access
      let fetchUrl = _filePath;
      if (_filePath.includes("github.com") && _filePath.includes("/blob/")) {
        fetchUrl = _filePath
          .replace("github.com", "raw.githubusercontent.com")
          .replace("/blob/", "/");
      }

      // Fetch remote file content
      console.log(`Fetching remote file: ${fetchUrl}`);
      const response = await fetch(fetchUrl);
      if (!response.ok) {
        console.warn(`Failed to fetch remote file: ${fetchUrl}, status: ${response.status}`);
        return {};
      }
      content = await response.text();
    } else {
      // Handle local file
      if (!fs.existsSync(filePath)) {
        console.warn(`File not found: ${filePath}, skipping.`);
        return {};
      }
      content = fs.readFileSync(filePath, "utf8");
    }

    const extension = fileName.split(".").pop();
    let language = extension;
    if (extension === "py") language = "python";
    else if (extension === "css") language = "css";
    else if (extension === "md" || extension === "mdx") language = "markdown";
    else if (extension === "tsx") language = "typescript";
    else if (extension === "js") language = "javascript";
    else if (extension === "json") language = "json";
    else if (extension === "yaml" || extension === "yml") language = "yaml";
    else if (extension === "toml") language = "toml";

    return {
      name: fileName,
      content,
      language,
      type: "file",
    };
  } catch (error) {
    console.error(`Error reading file ${filePath}:`, error);
    return {};
  }
}

async function getFeatureFrontendFiles(featureId: string) {
  const featurePath = path.join(
    __dirname,
    `../src/app/[integrationId]/feature/${featureId as string}`,
  );
  const retrievedFiles = [];

  for (const fileName of featureFiles) {
    retrievedFiles.push(await getFile(featurePath, fileName));
  }

  return retrievedFiles;
}

const integrationsFolderPath = "../../../integrations";
const agentFilesMapper: Record<string, (agentKeys: string[]) => Record<string, string>> = {
  "openai-server": () => ({
    agentic_chat: path.join(__dirname, integrationsFolderPath, `/openai-server/src/index.ts`),
  }),
  "middleware-starter": () => ({
    agentic_chat: path.join(__dirname, integrationsFolderPath, `/middleware-starter/src/index.ts`),
  }),
  "pydantic-ai": (agentKeys: string[]) => {
    return agentKeys.reduce(
      (acc, agentId) => ({
        ...acc,
        [agentId]: `https://github.com/pydantic/pydantic-ai/blob/main/examples/pydantic_ai_examples/ag_ui/api/${agentId}.py`,
      }),
      {},
    );
  },
  "server-starter": () => ({
    agentic_chat: path.join(
      __dirname,
      integrationsFolderPath,
      `/server-starter/server/python/example_server/__init__.py`,
    ),
  }),
  "server-starter-all-features": (agentKeys: string[]) => {
    return agentKeys.reduce(
      (acc, agentId) => ({
        ...acc,
        [agentId]: path.join(
          __dirname,
          integrationsFolderPath,
          `/server-starter/server/python/example_server/${agentId}.py`,
        ),
      }),
      {},
    );
  },
  mastra: () => ({
    agentic_chat: path.join(
      __dirname,
      integrationsFolderPath,
      `/mastra/example/src/mastra/agents/weather-agent.ts`,
    ),
  }),
  "mastra-agent-lock": () => ({
    agentic_chat: path.join(
      __dirname,
      integrationsFolderPath,
      `/mastra/example/src/mastra/agents/weather-agent.ts`,
    ),
  }),
  "vercel-ai-sdk": () => ({
    agentic_chat: path.join(__dirname, integrationsFolderPath, `/vercel-ai-sdk/src/index.ts`),
  }),
  langgraph: (agentKeys: string[]) => {
    return agentKeys.reduce(
      (acc, agentId) => ({
        ...acc,
        [agentId]: path.join(
          __dirname,
          integrationsFolderPath,
          `/langgraph/examples/agents/${agentId}/agent.py`,
        ),
      }),
      {},
    );
  },
  "langgraph-fastapi": (agentKeys: string[]) => {
    return agentKeys.reduce(
      (acc, agentId) => ({
        ...acc,
        [agentId]: path.join(
          __dirname,
          integrationsFolderPath,
          `/langgraph/python/ag_ui_langgraph/examples/agents/${agentId}.py`,
        ),
      }),
      {},
    );
  },
  agno: () => ({}),
  "llama-index": (agentKeys: string[]) => {
    return agentKeys.reduce(
      (acc, agentId) => ({
        ...acc,
        [agentId]: path.join(
          __dirname,
          integrationsFolderPath,
          `/llamaindex/server-py/server/routers/${agentId}.py`,
        ),
      }),
      {},
    );
  },
  crewai: (agentKeys: string[]) => {
    return agentKeys.reduce(
      (acc, agentId) => ({
        ...acc,
        [agentId]: path.join(
          __dirname,
          integrationsFolderPath,
          `/crewai/python/ag_ui_crewai/examples/${agentId}.py`,
        ),
      }),
      {},
    );
  },
};

async function runGenerateContent() {
  const result = {};
  for (const agentConfig of agentConfigs) {
    // Use the parsed agent keys instead of executing the agents function
    const agentsPerFeatures = agentConfig.agentKeys;

    const agentFilePaths = agentFilesMapper[agentConfig.id](agentConfig.agentKeys);
    // Per feature, assign all the frontend files like page.tsx as well as all agent files
    for (const featureId of agentsPerFeatures) {
      // @ts-expect-error -- redundant error about indexing of a new object.
      result[`${agentConfig.id}::${featureId}`] = [
        // Get all frontend files for the feature
        ...(await getFeatureFrontendFiles(featureId)),
        // Get the agent (python/TS) file
        await getFile(agentFilePaths[featureId]),
      ];
    }
  }

  return result;
}

(async () => {
  const result = await runGenerateContent();
  fs.writeFileSync(path.join(__dirname, "../src/files.json"), JSON.stringify(result, null, 2));

  console.log("Successfully generated src/files.json");
})();
