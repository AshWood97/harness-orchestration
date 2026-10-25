import { runWorkerTask, validateHostProfile } from "codex-zcode-bridge/core";
import { runtimeEnvironment, applyEnvironment } from "./policy.mjs";

const [dataRoot, taskId, attemptText] = process.argv.slice(2);
try {
  if (!dataRoot || !taskId || !/^[1-9]\d*$/.test(attemptText || "") || !Number.isSafeInteger(Number(attemptText))) {
    throw new Error("Usage: worker-main.mjs <dataRoot> <taskId> <attempt>");
  }
  const host = validateHostProfile(JSON.parse(process.env.ZCODE_BRIDGE_HOST_PROFILE || "null"));
  applyEnvironment(runtimeEnvironment(host));
  if (process.env.ZCODE_BRIDGE_DATA_DIR !== dataRoot) throw new Error("Worker storage does not match the installed host");
  await runWorkerTask({ dataRoot, taskId, attempt: Number(attemptText), host });
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
}
