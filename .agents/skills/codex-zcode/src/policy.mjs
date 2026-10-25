import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";

export const MODEL_KEYS = [
  "ZCODE_BRIDGE_DEFAULT_PROVIDER_ID",
  "ZCODE_BRIDGE_DEFAULT_MODEL_ID",
  "ZCODE_BRIDGE_DEFAULT_REASONING_LEVEL",
];

const RUNTIME_KEYS = [
  "ZCODE_BRIDGE_NODE", "ZCODE_BRIDGE_ZCODE_CJS", "ZCODE_BRIDGE_DATA_DIR",
  "ZCODE_BUILTIN_PROVIDER_CONFIG_FILE", "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE",
  "ZCODE_HOME", "ZCODE_DATA_BASE_DIR", "ZCODE_WINDOWS_APP_INSTALL_DIR",
  "ZCODE_BRIDGE_MODE", "ZCODE_BRIDGE_MAX_CONCURRENT_WORKERS",
  "ZCODE_BRIDGE_TIMEOUT_MS", "ZCODE_BRIDGE_BROWSER_USE",
];

export function hostProfile(env = process.env, home = homedir(), workerEntryPath) {
  const codexHome = env.CODEX_HOME?.trim() || path.join(home, ".codex");
  if (!path.isAbsolute(codexHome)) throw new Error("CODEX_HOME must be an absolute path");
  const settingsDirectory = path.join(codexHome, "codex-zcode");
  return {
    name: "codex-zcode", settingsDirectory,
    defaultDataRoot: path.join(settingsDirectory, "state"),
    ...(workerEntryPath ? { workerEntryPath } : {}),
  };
}

/** The host and every detached worker apply the same installed policy. */
export function runtimeEnvironment(host, source = process.env) {
  const file = path.join(host.settingsDirectory, "runtime-config.json");
  let config;
  try {
    const raw = readFileSync(file, "utf8");
    if (Buffer.byteLength(raw) > 65536) throw new Error("oversized configuration");
    config = JSON.parse(raw);
    if (!config || Array.isArray(config) || typeof config !== "object") throw new Error("invalid configuration");
  } catch {
    throw new Error("Run codex-zcode/scripts/install.py --apply to configure this CODEX_HOME");
  }
  if (MODEL_KEYS.some(key => config[key] != null && config[key] !== "")) {
    throw new Error("codex-zcode inherits ZCode defaults; remove stored bridge model overrides using install.py --apply");
  }
  if (config.ZCODE_BRIDGE_BROWSER_USE && config.ZCODE_BRIDGE_BROWSER_USE !== "off") {
    throw new Error("codex-zcode requires browser hosting off; no computer-control fallback is available");
  }
  const env = { ...source };
  for (const key of Object.keys(env)) {
    if (key.startsWith("ZCODE_BRIDGE_") || RUNTIME_KEYS.includes(key)) delete env[key];
  }
  for (const key of RUNTIME_KEYS) {
    const value = config[key];
    if (value == null) continue;
    if (typeof value !== "string") throw new Error(`Invalid codex-zcode setting: ${key}`);
    env[key] = value.trim();
  }
  for (const key of MODEL_KEYS) env[key] = "";
  env.ZCODE_BRIDGE_BROWSER_USE = "off";
  env.ZCODE_BRIDGE_DATA_DIR ||= host.defaultDataRoot;
  env.ZCODE_BRIDGE_MODE ||= "build";
  env.ZCODE_BRIDGE_MAX_CONCURRENT_WORKERS ||= "2";
  env.ZCODE_BRIDGE_TIMEOUT_MS ||= "3600000";
  if (!path.isAbsolute(env.ZCODE_BRIDGE_DATA_DIR)) throw new Error("Task storage must be an absolute path");
  if (!/^[1-8]$/.test(env.ZCODE_BRIDGE_MAX_CONCURRENT_WORKERS)) throw new Error("Worker limit must be 1..8");
  return env;
}

export function applyEnvironment(env) {
  for (const key of Object.keys(process.env)) {
    if (!(key in env)) delete process.env[key];
  }
  Object.assign(process.env, env);
}
