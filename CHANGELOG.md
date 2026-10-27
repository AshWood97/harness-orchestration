# Changelog

## ZCode 1.0.0 — 2026-10-27

- Expand ZCode to ten custom roles plus built-in Explore and general-purpose. Add scout for exact retrieval, mechanic for prescribed edits and check-runner for specified commands; retain session model and thought-level inheritance.
- Focus each custom prompt on responsibility, inputs, method, result, stopping conditions and execution boundaries. Give each assignment one objective and relevant context.
- Dispatch independent ready work within four concurrent subagents, excluding the host and subject to runtime capacity. Allow multiple instances of a role, refill freed slots and order shared writes and dependencies.
- Use one owner per concrete checking question, distinct functional angles for independent checks, read-only review and no automatic final gate. Preserve the explicit user boundary against extra tests, hashes, security audits, defensive layers and artifacts.
- Update the existing installer role list, version manifest and bilingual documentation. Publish the component as zcode-v1.0.0; preserve the Native v1.0.0 tag and release.

## 1.0.0 — 2026-10-27

- Keep 14 Native role types. Move conductor to GPT-6 Astra/xhigh and explorer, researcher, worker and tester to GPT-6.1 Terra/max. Preserve the other role assignments and the user's host model.
- Use the same role manifest and workflow for manual skill invocation and the trusted Ultra entrypoint. Keep four concurrent subagents, excluding the host and subject to runtime capacity.
- Dispatch useful independent ready work concurrently, including multiple instances of a role, and refill freed slots. Order dependencies and shared writes; do not create filler assignments.
- Give each role explicit responsibility, inputs, method, result, stopping conditions and execution boundaries. Give children narrow assignments with relevant context and separately owned paths.
- Assign one owner per concrete checking question. Allow independent checks of distinct functional questions when needed; keep review read-only and avoid duplicate reviews, automatic final gates, unsolicited security audits and reassurance work.
- Normalize historical repository versions to v0.x and rename the old v5.0.0 release/tag to v0.5.0 without rewriting its source history. ZCode and Qoder behavior is unchanged in this release.

## 0.5.0 — 2026-10-25

- Preserve the Windows PowerShell module-analysis cache environment variable so identity queries do not cold-start and time out. Handle early cancellation by waiting for the same attempt's persisted process identities before retrying core cancellation; preserve process-tree verification and other failures.

- **Breaking:** remove the Codex External Provider and Codex Harness Bridge skill packages. Add **Codex ZCode** at `.agents/skills/codex-zcode`, installed as `codex-zcode` with its own settings and state.
- Use the pinned `Sandyzzx/codex-zcode-bridge` 1.2.7 shared core with Node.js 22.18+, a Python 3.9+ helper and MCP `codex_zcode`. Provide setup, diagnostics, model discovery and task submit/events/status/result/continue/cancel commands without computer-use, UI or remote-control fallback.
- Activate Codex ZCode only through its selected skill, `$codex-zcode`, or a direct request to use ZCode. An actual invocation takes priority over automatic Native routing in Ultra; discussion and quoted content do not. Preserve Native role models and workflow and leave Qoder unchanged.
- Inherit ZCode workspace session model/reasoning defaults unless the user explicitly selects a task model. Keep that model on continuation; changing it requires a new task. Make the separate ZCode role installer inherit by default, with optional model/depth overrides and an explicit built-in-model reset.
- Replace retired-package CI with focused Codex ZCode and ZCode checks on macOS/Windows using Python 3.11 and Node.js 24. Keep Native installer checks manually selectable and preserve historical entries below.

## 0.4.3 — 2026-10-21

- Update Qoder plugin and skill to **1.1.0**: Default Agent conversations automatically orchestrate actual complex engineering work when division helps. Keep simple Q&A and clear localized edits in the host; do not infer complexity from text length or file count.
- Add a plugin-level `UserPromptSubmit` hook that reads one packaged static routing rule using `cat` and `QODER_PLUGIN_ROOT`. For complex work, the first tool call loads the full skill and Conductor follows before any source retrieval or reading; no separate global-memory setup is required. The hook targets macOS/Linux; Windows is unverified. Explicit skill requests and the custom coordinator remain optional.
- Let one plugin Conductor select the smallest useful subset from all 14 roles. Preserve one writer, at most four children, one checking owner, minimal checks, and user restrictions including `root-only` and no subagents. Quoted or attached instructions do not authorize work.
- Leave all 14 Qoder role prompts, tool sets, and model inheritance unchanged. Codex and ZCode activation behavior is unchanged.

## 0.4.2 — 2026-10-21

- Rename the repository to **Harness Orchestration / 多 Harness 角色编排** (`AshWood97/harness-orchestration`) for Codex, ZCode, Qoder, and future harness adapters. Preserve existing Codex skill identifiers, paths, ZCode files, and activation markers.
- Add Qoder desktop plugin **harness-orchestration 1.0.0** with all 14 adapted roles and one manually activated skill. Omit role model fields to follow the current Qoder conversation model; provide read-only tool sets without Bash/Edit/Write.
- Add reusable custom-coordinator instructions and bilingual ZIP import, packaging, role, and permission documentation. Keep one writer, at most four children by default, one checking owner, no nested delegation, minimal targeted checks, and the explicit-request boundary for digests.
- Keep the Qoder package credential-free, without hooks, MCP servers, or a new test framework. Declare individual agent Markdown paths for desktop importer compatibility.

## 0.4.1 — 2026-10-19

- Let Conductor assess multi-role tasks and select any needed roles; the host dispatches the plan. ZCode's host performs the same planning role. Individual specialists no longer require the user to name them.
- Keep extra testing minimal: inspect first, reuse results, prefer existing targeted cases and write tests only for concrete important gaps. Respect explicit no-tests/read-only instructions.
- Select design criticism, finding validation or Guardian only for distinct material questions; do not reinstate full-role pipelines, duplicate review, hash machinery or extra process artifacts.


## 0.4.0 — 2026-10-19

- Make both Native entrypoints and ZCode follow plan → implement → one focused inspection → repair concrete issues or deliver.
- Preserve role models; remove mandatory Conductor startup, test-author/tester chains, automatic Guardian, repeat-review requirements and fixed repair/escalation waves.
- Keep testing and additional specialist reviews explicit-request-only. Review-only tasks remain read-only. No speculative abstractions, extra output files or duplicated work.
- Restrict hashing to explicitly requested published checksums, deduplication, cache decisions or known-digest rejection with an actual consumer.
- Remove the old Native CLI runner and its hash journals, gate/evidence schemas, dedicated tests and process helper. This is a breaking workflow simplification: use native agent tools and existing chat progress; old controller commands are no longer provided. Historical user run files are not migrated or deleted.
- Remove automatic hashes and backup receipts from Native activation and ZCode installation. Keep personal guidance outside the managed blocks.
- Stop automatic Native/ZCode test matrices. Keep the existing External/Harness CI scoped to changes in those packages; installer tests remain manually selectable.

以下版本记录仅为历史，不代表当前执行规则。

## 0.3.3 — 2026-10-16

The repository is now **Codex + ZCode Orchestration**, renamed from `codex-three-paths` to `codex-zcode-orchestration`. Existing Codex skill names remain stable. This release combines the local quality-workflow upgrades with the repository's existing Windows support.

### Codex Native

- Expand to 14 bounded roles: eight GPT-6.1 Sol/max, three GPT-6 Luna/max, and three GPT-6 Astra/xhigh. Default subagents use Sol/max; the host model stays user-selected.
- Add independent design criticism, acceptance-test authoring, finding validation and root-cause debugging. Keep independent execution, code review and the isolated final Guardian gate.
- Route clear repetitive work to scout, mechanic and check_runner. Require explicit edit recipes or commands; ambiguity returns to the appropriate Sol role.
- Run generated test/build output in disposable verification clones. Reject tracked source or protected Git metadata changes; keep downstream Sol verification for writer plans.
- Bind evidence to the candidate and package fingerprint. Permit bounded repair revisions with fresh verification/review; reject attempts to get a new verdict on unchanged evidence. Require debugger evidence after two failed fixes of the same issue; cap repairs at five waves.
- Keep alternative candidates out of additive DAG integration. Candidate comparisons remain explicit experiments with a shared acceptance basis.
- Preserve the upstream Windows process launch, stdin prompt transport, process-tree cleanup, lock probing, sandbox-accessible workspaces and activation installer. Apply the accessible workspace policy to disposable verification too, and preserve baseline/detailed prompt context in verification packets.
- Include a controlled evaluation protocol. Deterministic tests are not evidence of coding-quality improvement or measured quota savings.

### ZCode

- Publish seven custom role templates and the host AGENTS.md workflow, alongside instructions for built-in Explore and general-purpose.
- Use Gemini 3.8 Flash/high throughout. Substitute the user's provider/model identifier during installation instead of publishing account-specific state.
- Add a preview-first installer with conflict checks, backups, atomic replacement and rollback on failure. Preserve personal guidance outside the managed block.
- Separate test design, execution and review; document test appeals, evidence expiry, finding adjudication, bounded repair and host-enforced isolation.

### Distribution

- Update bilingual installation and role documentation for both tools.
- Retain the independent External Provider and Harness Bridge skills and their Windows fixes.
- Extend the Linux/Windows Python 3.11/3.12 CI matrix to include the ZCode installer tests.

本次发布覆盖本轮 Codex 质量流程、Luna 分工、Sol 主流程和 ZCode 角色升级。没有发布个人配置、provider UUID、API key、任务日志或本机回滚备份。
