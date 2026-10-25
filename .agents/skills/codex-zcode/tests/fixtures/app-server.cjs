// Deterministic protocol fixture: no model/API, browser, or OS automation.
const fs = require("node:fs");
const path = require("node:path");
const readline = require("node:readline");
const { randomUUID } = require("node:crypto");
if (process.argv.includes("--version")) {
  console.log("0.17.0");
  process.exit(0);
}
const root = __dirname;
const log = message => fs.appendFileSync(path.join(root, "requests.jsonl"), JSON.stringify(message) + "\n");
log({ argv: process.argv.slice(2), secretPresent: Boolean(process.env.CODEX_ZCODE_TEST_SECRET) });
let sessionId;
let selected;
const sessionFile = () => path.join(root, sessionId + ".json");
const save = () => fs.writeFileSync(sessionFile(), JSON.stringify(selected));
const send = message => process.stdout.write(JSON.stringify(message) + "\n");
const snapshot = () => ({
  session: { sessionId }, runtime: { eventSeq: 0 },
  settings: { model: { current: selected, available: [
    selected, { providerId: "test-provider", modelId: "explicit-model" },
  ].map(ref => ({ ref, label: ref.modelId })) } },
});
const finish = () => send({ method: "session/event", params: {
  seq: 2, type: "turn.completed", payload: { resultType: "success", usage: { totalTokens: 1 },
    response: JSON.stringify({ summary: "Fixture task completed", files_changed: [], tests: [], issues: [], needs_master_decision: false }),
  },
} });
readline.createInterface({ input: process.stdin }).on("line", line => {
  const message = JSON.parse(line);
  log(message);
  if (message.id === "permission-rpc" && message.result) return finish();
  const reply = result => send({ id: message.id, result });
  switch (message.method) {
    case "session/create":
      sessionId = "sess_" + randomUUID();
      selected = JSON.parse(fs.readFileSync(path.join(root, "default.json"), "utf8"));
      save();
      reply(snapshot());
      break;
    case "session/resume":
      sessionId = message.params.sessionId;
      selected = JSON.parse(fs.readFileSync(sessionFile(), "utf8"));
      reply(snapshot());
      break;
    case "session/setModel":
      selected = message.params.model;
      save();
      reply(snapshot());
      break;
    case "session/setMode": reply(snapshot()); break;
    case "session/send":
      reply({});
      send({ method: "session/event", params: { seq: 1, type: "turn.started", payload: {} } });
      if (JSON.stringify(message.params).includes("WAIT_FOR_CANCEL")) break;
      if (JSON.stringify(message.params).includes("PERMISSION_ROUNDTRIP")) {
        send({ id: "permission-rpc", method: "interaction/requestPermission", params: {
          requestId: "permission-1", sessionId, toolCallId: "tool-1", toolName: "Write",
          input: { file_path: path.join(root, "output.txt"), content: "fixture" },
          options: [{ kind: "allow_once" }, { kind: "deny" }],
        } });
      } else finish();
      break;
    default: if (message.id != null) reply({});
  }
});
