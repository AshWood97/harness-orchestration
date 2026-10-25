import { fileURLToPath } from "node:url";
import { serveStdio } from "@modelcontextprotocol/server/stdio";
import {
  TaskStore, BridgeTaskManager, DirectWorkspaceProvider, createWorkerSpawner,
  createPlatformProbe, createBridgeServer, ZCodeModelSettings, runBridgeDoctor,
  BridgeError,
} from "codex-zcode-bridge/core";
import { hostProfile, runtimeEnvironment, applyEnvironment } from "./policy.mjs";
import { cancelTask } from "./cancel.mjs";

const host = hostProfile(process.env, undefined,
  fileURLToPath(new URL("../worker/worker-main.mjs", import.meta.url)));
applyEnvironment(runtimeEnvironment(host));
const env = process.env;
const store = new TaskStore(env.ZCODE_BRIDGE_DATA_DIR);
const manager = new BridgeTaskManager({
  store,
  workspaceProvider: new DirectWorkspaceProvider(),
  maxConcurrentWorkers: Number(env.ZCODE_BRIDGE_MAX_CONCURRENT_WORKERS),
  spawnWorker: createWorkerSpawner(host), probe: createPlatformProbe(),
});
const settings = new ZCodeModelSettings(env, { host });
const refusePersistentModel = async () => {
  throw new BridgeError("provider_config_invalid", "Use zcode_task.model for an explicit task selection; codex-zcode always inherits ZCode defaults otherwise");
};
const server = createBridgeServer({
  taskManager: {
    createTask: task => manager.createTask(task),
    getStatus: id => manager.getStatus(id),
    getResult: id => manager.getResult(id),
    continueTask: input => manager.continueTask(input),
    cancelTask: id => cancelTask(manager, store, id),
    getEvents: input => manager.getEvents(input),
    getFeedback: input => manager.getFeedback(input),
    replyToInteraction: input => manager.replyToInteraction(input),
  },
  doctor: () => runBridgeDoctor({ env, dataRoot: env.ZCODE_BRIDGE_DATA_DIR, resolver: { host } }),
  modelSettings: {
    listModels: workspace => settings.listModels(workspace),
    getDefaultModel: async () => ({ configured: false, model: null }),
    setDefaultModel: refusePersistentModel, clearDefaultModel: refusePersistentModel,
  },
  serverInfo: { name: "codex-zcode", version: "5.0.0" },
  instructions: "Use only when the user selects codex-zcode or explicitly asks ZCode to execute. Omit task.model unless the user specifies it. Dispatch bounded tasks, follow events, review actual files, and continue or cancel by task_id. No computer-use or UI fallback. ZCode workers must not delegate again.",
});
const transport = serveStdio(() => server);
let closing = false;
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.once(signal, () => {
    if (closing) return;
    closing = true;
    void transport.close().finally(() => {
      manager.dispose();
      process.exit(0);
    });
  });
}
