/**
 * Browser-facing CopilotKit runtime (ADR-0004).
 *
 * Angular talks to this service; it proxies AG-UI runs to the Python agent.
 * No CopilotKit Intelligence: the runtime runs in SSE mode with an in-memory
 * runner, so nothing leaves our infrastructure except model calls the agent makes.
 *
 * Env: PORT (4000), AGENT_URL (http://localhost:8123/agent),
 *      ALLOWED_ORIGINS (comma-separated, default the Vite dev server).
 */
import { createServer } from 'node:http';
import { HttpAgent } from '@ag-ui/client';
import { CopilotRuntime } from '@copilotkit/runtime/v2';
import { createCopilotNodeListener } from '@copilotkit/runtime/v2/node';

const port = Number(process.env.PORT ?? 4000);
const agentUrl = process.env.AGENT_URL ?? 'http://localhost:8123/agent';
const allowedOrigins = (process.env.ALLOWED_ORIGINS ?? 'http://localhost:5173')
  .split(',')
  .map((origin) => origin.trim())
  .filter(Boolean);

const runtime = new CopilotRuntime({
  // "default" is the agent id <copilot-chat> uses when none is given.
  agents: { default: new HttpAgent({ url: agentUrl }) },
});

const listener = createCopilotNodeListener({
  runtime,
  basePath: '/api/copilotkit',
  cors: { origin: allowedOrigins },
  activateChannels: false,
});

createServer(listener).listen(port, () => {
  console.log(`copilot-runtime on :${port}/api/copilotkit -> ${agentUrl}`);
});
