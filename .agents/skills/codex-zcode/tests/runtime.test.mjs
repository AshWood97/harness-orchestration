import assert from "node:assert/strict";
import test from "node:test";
import { mkdtemp, mkdir, readFile, writeFile, copyFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { once } from "node:events";
import { hostProfile, runtimeEnvironment, MODEL_KEYS } from "../src/policy.mjs";

const skill = fileURLToPath(new URL("..", import.meta.url));
const bridge = path.join(skill, "runtime", "dist", "bridge.mjs");
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function fixture() {
  const root = await mkdtemp(path.join(tmpdir(), "codex-zcode test "));
  const codexHome = path.join(root, "custom codex");
  const host = hostProfile({ CODEX_HOME: codexHome });
  const zcodeHome = path.join(root, ".zcode");
  await mkdir(host.settingsDirectory, { recursive: true });
  await mkdir(path.join(zcodeHome, "v2"), { recursive: true });
  const entry = path.join(root, "app-server.cjs");
  await copyFile(new URL("fixtures/app-server.cjs", import.meta.url), entry);
  await writeFile(path.join(root, "default.json"), JSON.stringify({ providerId: "test-provider", modelId: "default-a", options: { reasoningLevel: "low" } }));
  const builtin = path.join(root, "builtin.json");
  const personal = path.join(zcodeHome, "v2", "provider_config.json");
  await writeFile(builtin, JSON.stringify({ config: {} }));
  await writeFile(personal, JSON.stringify({ config: { providerConfigRules: { providerRules: { "test-provider": {} } } } }));
  const config = {
    ZCODE_BRIDGE_NODE: process.execPath, ZCODE_BRIDGE_ZCODE_CJS: entry,
    ZCODE_BUILTIN_PROVIDER_CONFIG_FILE: builtin, ZCODE_PERSONAL_PROVIDER_CONFIG_FILE: personal,
    ZCODE_HOME: zcodeHome, ZCODE_BRIDGE_DATA_DIR: host.defaultDataRoot,
    ZCODE_BRIDGE_BROWSER_USE: "off", ...Object.fromEntries(MODEL_KEYS.map(key => [key, null])),
  };
  const configFile = path.join(host.settingsDirectory, "runtime-config.json");
  await writeFile(configFile, JSON.stringify(config));
  return { root, codexHome, host, config, configFile, env: {
    ...process.env, CODEX_HOME: codexHome, CODEX_ZCODE_TEST_SECRET: "fixture-secret",
    ZCODE_BRIDGE_DEFAULT_MODEL_ID: "stale-model", ZCODE_BRIDGE_DEFAULT_PROVIDER_ID: "stale-provider",
    ZCODE_BRIDGE_DEFAULT_REASONING_LEVEL: "high", ZCODE_BRIDGE_BROWSER_USE: "headless",
    ZCODE_BRIDGE_DATA_DIR: path.join(root, "old-data"),
  } };
}

class Client {
  constructor(env) {
    this.process = spawn(process.execPath, [bridge], { env, stdio: ["pipe", "pipe", "pipe"], windowsHide: true });
    this.pending = new Map();
    this.id = 0;
    this.diagnostics = "";
    this.process.stderr.on("data", data => { this.diagnostics += data; });
    createInterface({ input: this.process.stdout }).on("line", line => {
      const message = JSON.parse(line);
      const handler = this.pending.get(message.id);
      if (handler) { this.pending.delete(message.id); handler(message); }
    });
    this.process.on("exit", () => {
      for (const handler of this.pending.values()) handler({ error: { message: this.diagnostics } });
      this.pending.clear();
    });
  }
  send(message) { this.process.stdin.write(JSON.stringify(message) + "\n"); }
  request(method, params) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { this.pending.delete(id); reject(new Error("MCP timeout: " + this.diagnostics)); }, 15000);
      this.pending.set(id, message => { clearTimeout(timer); message.error ? reject(new Error(message.error.message)) : resolve(message.result); });
      this.send({ jsonrpc: "2.0", id, method, params });
    });
  }
  async initialize() {
    await this.request("initialize", { protocolVersion: "2025-03-26", capabilities: {}, clientInfo: { name: "fixture", version: "1" } });
    this.send({ jsonrpc: "2.0", method: "notifications/initialized" });
  }
  async call(name, args = {}) {
    const result = await this.request("tools/call", { name, arguments: args });
    if (result.isError) throw new Error(JSON.stringify(result.structuredContent || result.content));
    return result.structuredContent || JSON.parse(result.content[0].text);
  }
  async close() {
    if (this.process.exitCode !== null || this.process.signalCode !== null) return;
    const exited = once(this.process, "exit");
    this.process.kill();
    await exited;
  }
}

async function terminal(client, taskId) {
  for (let i = 0; i < 150; i++) {
    const status = await client.call("zcode_status", { task_id: taskId });
    if (["completed", "failed", "cancelled", "waiting_for_master"].includes(status.status)) {
      return { status, result: await client.call("zcode_result", { task_id: taskId }) };
    }
    await delay(100);
  }
  throw new Error("Task did not finish: " + taskId);
}

function task(root, taskId, objective = "Fixture task") {
  return { task_id: taskId, workspace: root, objective, requirements: ["Do not delegate"], allowed_paths: [], forbidden_paths: [], acceptance_criteria: [], test_commands: [] };
}

test("CODEX_HOME policy isolates stale model, storage and browser environment", async () => {
  const f = await fixture();
  try {
    const env = runtimeEnvironment(f.host, f.env);
    assert.equal(env.ZCODE_BRIDGE_DATA_DIR, f.host.defaultDataRoot);
    assert.equal(env.ZCODE_BRIDGE_BROWSER_USE, "off");
    for (const key of MODEL_KEYS) assert.equal(env[key], "");
    for (const patch of [{ ZCODE_BRIDGE_DEFAULT_MODEL_ID: "pinned" }, { ZCODE_BRIDGE_BROWSER_USE: "headless" }]) {
      await writeFile(f.configFile, JSON.stringify({ ...f.config, ...patch }));
      assert.throws(() => runtimeEnvironment(f.host, f.env), /inherits ZCode defaults|browser hosting off/);
    }
  } finally { await rm(f.root, { recursive: true, force: true }); }
});

test("bundled stdio host inherits runtime defaults, scopes override, resumes and survives caller restart", { timeout: 45000 }, async () => {
  const f = await fixture();
  let client = new Client(f.env);
  try {
    await client.initialize();
    await assert.rejects(client.call("zcode_set_default_model", { provider_id: "test-provider", model_id: "explicit-model" }), /task selection/);
    await client.call("zcode_task", task(f.root, "default-a"));
    await client.close();
    client = new Client(f.env);
    await client.initialize();
    const first = await terminal(client, "default-a");
    assert.equal(first.status.status, "completed", JSON.stringify(first.result));
    await writeFile(path.join(f.root, "default.json"), JSON.stringify({ providerId: "test-provider", modelId: "default-b", options: { reasoningLevel: "medium" } }));
    await client.call("zcode_task", task(f.root, "default-b"));
    assert.equal((await terminal(client, "default-b")).status.status, "completed");
    await client.call("zcode_task", { ...task(f.root, "explicit"), model: { provider_id: "test-provider", model_id: "explicit-model", reasoning_level: "high" } });
    assert.equal((await terminal(client, "explicit")).status.status, "completed");
    const continuation = { task_id: "default-a", feedback: "Return another fixture report", operation_id: "revision-1" };
    await client.call("zcode_continue", continuation);
    const resumed = await terminal(client, "default-a");
    assert.equal(resumed.status.zcode_session_id, first.status.zcode_session_id);
    assert.equal(resumed.status.attempt, 2);
    await client.call("zcode_continue", continuation);
    assert.equal((await client.call("zcode_status", { task_id: "default-a" })).attempt, 2);
    const log = (await readFile(path.join(f.root, "requests.jsonl"), "utf8")).trim().split("\n").map(JSON.parse);
    const overrides = log.filter(message => message.method === "session/setModel");
    assert.equal(overrides.length, 1);
    assert.equal(overrides[0].params.persistAsWorkspaceLastUsed, false);
    const creates = log.filter(message => message.method === "session/create");
    assert.equal(creates.length, 3);
    assert.ok(creates.every(message => !message.params.model && !message.params.reasoning_level));
    assert.equal(JSON.parse(await readFile(path.join(f.root, first.status.zcode_session_id + ".json"))).modelId, "default-a");
    const defaultB = await client.call("zcode_status", { task_id: "default-b" });
    assert.equal(JSON.parse(await readFile(path.join(f.root, defaultB.zcode_session_id + ".json"))).modelId, "default-b");
    assert.equal(JSON.parse(await readFile(path.join(f.root, "default.json"))).modelId, "default-b");
    const launches = log.filter(message => message.argv);
    assert.ok(launches.every(message => message.argv.includes("app-server") && message.argv.includes("--stdio") && !message.secretPresent));
    assert.deepEqual(JSON.parse(await readFile(f.configFile)), f.config);
  } finally { await client.close(); await rm(f.root, { recursive: true, force: true }); }
});

test("permission roundtrip and running-task cancellation need only stdio", { timeout: 30000 }, async () => {
  const f = await fixture();
  const client = new Client(f.env);
  try {
    await client.initialize();
    await client.call("zcode_task", task(f.root, "permission", "PERMISSION_ROUNDTRIP"));
    let request;
    let next = 0;
    for (let i = 0; i < 30 && !request; i++) {
      const page = await client.call("zcode_events", { task_id: "permission", after_seq: next, wait_ms: 500, view: "raw" });
      request = page.events.find(event => event.type === "interaction_requested");
      next = page.next_seq;
    }
    assert.ok(request, "permission event was delivered");
    await client.call("zcode_interaction_reply", { task_id: "permission", request_id: request.details.request_id, decision: "allow", reason: "Fixture permission" });
    assert.equal((await terminal(client, "permission")).status.status, "completed");
    await client.call("zcode_task", task(f.root, "cancel", "WAIT_FOR_CANCEL"));
    let sent = false;
    next = 0;
    for (let i = 0; i < 30 && !sent; i++) {
      const page = await client.call("zcode_events", { task_id: "cancel", after_seq: next, wait_ms: 500, view: "raw" });
      sent = page.events.some(event => event.type === "turn_started");
      next = page.next_seq;
    }
    assert.ok(sent, "runtime started before cancellation");
    await client.call("zcode_cancel", { task_id: "cancel" });
    assert.equal((await terminal(client, "cancel")).status.status, "cancelled");
  } finally {
    for (const taskId of ["permission", "cancel"]) {
      await client.call("zcode_cancel", { task_id: taskId }).catch(() => {});
      await terminal(client, taskId).catch(() => {});
    }
    await client.close();
    await rm(f.root, { recursive: true, force: true });
  }
});
