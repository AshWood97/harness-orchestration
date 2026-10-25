// Maintainer-only: rebuild the committed bundles from the pinned upstream checkout.
import { createRequire } from "node:module";
import { readFile, mkdir, copyFile, writeFile, readdir } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const revision = "0e74ee1c64b179752a24317574916a98c77a5ef1";
const upstream = process.argv[2] && path.resolve(process.argv[2]);
if (!upstream) throw new Error("Usage: node scripts/build_zcode_runtime.mjs /path/to/codex-zcode-bridge (npm ci first)");
if (execFileSync("git", ["rev-parse", "HEAD"], { cwd: upstream, encoding: "utf8" }).trim() !== revision) {
  throw new Error("Upstream checkout does not match the pinned revision");
}
const require = createRequire(path.join(upstream, "package.json"));
const { build } = require("esbuild");
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const skill = path.join(root, ".agents", "skills", "codex-zcode");
const runtime = path.join(skill, "runtime");
await mkdir(path.join(runtime, "dist"), { recursive: true });
await mkdir(path.join(runtime, "worker"), { recursive: true });
const shared = {
  bundle: true, platform: "node", target: "node22.18", format: "esm",
  minify: true, legalComments: "eof", packages: "bundle",
  alias: { "codex-zcode-bridge/core": path.join(upstream, "src", "core.ts") },
  nodePaths: [path.join(upstream, "node_modules")],
};
await Promise.all([
  build({ ...shared, entryPoints: [path.join(skill, "src", "host.mjs")], outfile: path.join(runtime, "dist", "bridge.mjs") }),
  build({ ...shared, entryPoints: [path.join(skill, "src", "worker.mjs")], outfile: path.join(runtime, "worker", "worker-main.mjs") }),
]);
const plugin = path.join(upstream, "plugins", "codex-zcode-bridge");
await copyFile(path.join(plugin, "LICENSE"), path.join(runtime, "LICENSE"));
await writeFile(path.join(runtime, "NOTICE"),
  "Codex ZCode distribution note\n\nThis distribution includes the shared core and the host/worker adapters. It omits the optional browser backend and playwright-core described in the unmodified upstream notice below.\n\n--- Upstream NOTICE ---\n\n" +
  await readFile(path.join(plugin, "NOTICE"), "utf8"));
await mkdir(path.join(runtime, "licenses"), { recursive: true });
for (const name of await readdir(path.join(plugin, "licenses"))) {
  if (!name.startsWith("PLAYWRIGHT")) await copyFile(path.join(plugin, "licenses", name), path.join(runtime, "licenses", name));
}
await writeFile(path.join(runtime, "package.json"), JSON.stringify({ name: "codex-zcode-runtime", version: "5.0.0", type: "module", private: true }, null, 2) + "\n");
await writeFile(path.join(runtime, "UPSTREAM.json"), JSON.stringify({
  repository: "https://github.com/Sandyzzx/codex-zcode-bridge", revision, version: "1.2.7",
  integration: "Unmodified shared core bundled with this skill's host/worker policy adapters. Browser backend is not distributed or enabled.",
}, null, 2) + "\n");
console.log("Built codex-zcode host and worker from pinned shared core (no browser backend).");
