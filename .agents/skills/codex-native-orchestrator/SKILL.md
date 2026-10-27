---
name: codex-native-orchestrator
description: Plan, implement and check scoped repository work with native Codex roles when explicitly invoked or authorized by the current Ultra runtime. Dispatch independent ready work concurrently with narrow role assignments and no extra process.
---

# Codex Native Orchestration

Version 1.0.0. Both manual and Ultra entrypoints use the same 14-role model catalog and four-subagent concurrency policy.

## Activation: manual invocation or Ultra

Only the primary/host agent coordinates this workflow. Delegated children execute their assigned packet and never start another orchestration.

A new task requires either entrypoint:

- **Manual:** The user selects **Codex Native Orchestration** from the skill/slash menu or directly invokes `$codex-native-orchestrator` with a task. Typing `/codex` only filters the menu. Questions, quotations, screenshots and requests to inspect or edit this skill are not invocations.
- **Ultra:** The latest trusted runtime/developer `<multi_agent_mode>` instruction says **"Proactive multi-agent delegation is active"**, and the repository task benefits from division of the requested work. Simple questions and localized edits remain in the host.

An actual ZCode invocation takes priority over the automatic Ultra entrypoint: the user selects **Codex ZCode**, directly invokes `$codex-zcode` with a task, or directly asks to use ZCode for that task. Follow that choice instead of starting Native automatically. Discussion, quotations, screenshots and requests to inspect or edit ZCode or its skill do not invoke it.

Ordinary/Max task matching, the word `ultra`, full access, saved model settings, available agent tools and earlier skill use do not activate this skill. A later explicit-request-only runtime instruction disables automatic activation for new tasks. Unknown mode requires manual invocation. Keep `policy.allow_implicit_invocation: false`; the [activation block](references/activation.md) loads this skill conditionally.

Both entrypoints use the same workflow. Continue unfinished work from its existing plan and results; do not restart completed steps. Re-evaluate activation for independent new tasks. Do not inspect or change the host model/effort to match a role.

## Execution boundary

Do only the user's requested work and deliver the minimum working result. Do not add unsolicited security audits, compatibility layers, defensive wrappers, future abstractions, adjacent refactors, duplicate inspections or extra output files for hypothetical benefit. "More reliable", "more professional" and future traceability do not authorize extra steps.

Do not calculate SHA-256, MD5, checksums, fingerprints or signatures, create `.sha256` files, or add integrity/evidence layers by default. Hashing is allowed only when the user explicitly requests published checksums, deduplication, cache-hit decisions, or rejection against a known digest, and the result is actually published or consumed by that requested operation. A digest without a downstream consumer is forbidden. "Just in case", professionalism and future traceability are not authorization.

The planner may select any available role for actual parts of the user's task; the user need not name individual roles. Do not add tests, subagents, full reviews or adjacent refactors merely for reassurance. Specialist or test assignments must resolve a concrete in-scope question that existing source/results do not settle. An explicit user prohibition, such as no tests or read-only, takes precedence.

Minimize extra testing. Start with source/result inspection and reuse existing observations. Add a targeted test or command only when an important behavior or decision cannot be adequately resolved from those sources. Prefer existing focused tests; author new cases only for a concrete gap. Do not default to full suites, build matrices, benchmarks, A/B or mutation experiments, separate test environments or another review pass. A role's availability, task size or general importance alone is not a reason to use it. Say briefly which concrete question a selected specialist or test will resolve; do not create a new approval form, ledger or evidence layer.

When a proposed addition exceeds the requested scope, stop that addition, ask one sentence — “我想加 X，因为 Y，是否允许？” — and wait. Do not do it first or ask about routine work already authorized.

## Plan → implement → check → fix or release

1. **Plan:** Understand the goal, relevant source, constraints, dependencies and completion conditions. Decide the smallest implementation before editing. Keep one proportionate plan in the conversation; revise only facts that changed. The host handles simple work and `root-only`. For multi-role work, use one `conductor` to identify independent ready assignments and their dependencies from the full role catalog. Minimize unnecessary work, not useful parallelism. The host dispatches the plan without nested delegation.
2. **Implement:** Dispatch independent ready assignments together, up to the available four-subagent capacity. Multiple instances of the same role may own different scopes. Start work that unblocks later steps first; fill a freed slot with the next independent ready assignment instead of waiting for an entire batch. Give each child the relevant plan and paths, not the whole conversation. Writers own distinct paths and agreed interfaces; serialize edits with shared write targets or unresolved dependencies.
3. **Check once per question:** The host or a `reviewer` compares the actual result/diff with requirements and relevant callers. Important changes may use independent checks only for distinct, concrete functional questions; give each checker original requirements and relevant source before another checker's conclusions. Choose one owner per question and one host to consolidate; do not duplicate whole reviews, vote on correctness or add security audits. A targeted test needs a specific unresolved behavior within the task. Review-only requests produce findings and never authorize edits.
4. **Fix or release:** For an implementation request, fix concrete in-scope defects, then inspect only the repair and directly affected paths. Reuse unchanged conclusions. If the result meets the request and no concrete issue remains, deliver immediately. Do not append Guardian, a fresh reviewer, a test rerun or a diagnostic role as a routine final step. Add a role only for a concrete unresolved question that materially affects the result; rerun only a check whose relevant inputs changed. There is no fixed number of repair waves. If a repair needs new scope or a missing decision, explain that specific blocker.

See [routing](references/routing.md) when assigning work, [delegation](references/delegation-contract.md) when forming a packet, and [checking](references/quality-workflow.md) for the completion boundary.

## Roles and runtime

| Roles | Model | Effort |
| --- | --- | --- |
| conductor, design_critic, debugger, guardian | `gpt-6-astra` | `xhigh` |
| explorer, researcher, worker, tester | `gpt-6.1-terra` | `max` |
| reviewer, finding_validator, test_author | `gpt-6.1-sol` | `max` |
| scout, mechanic, check_runner | `gpt-6-luna` | `max` |

The [JSON manifest](codex-native-orchestrator.json) defines the named role models and efforts for both manual and Ultra runs. Preserve them; do not silently substitute built-in role defaults or the host's model. Use native agent tools directly. All 14 roles are available for concrete in-scope assignments; a useful subset of role types may have multiple parallel instances. A missing test report, digest or Guardian verdict alone does not block completion; a concrete important unresolved behavior does.

At most four subagents may run concurrently, excluding the host and subject to actual runtime capacity. This is not a four-instance lifetime limit. When four independent useful assignments are ready, dispatch all four rather than conserving slots. Multi-module exploration and independent source research should use the available parallelism; do not invent tasks or duplicate searches to fill slots. Reuse an existing child when its role and context still fit. Default to one writer unless edits have independent owned paths and settled interfaces. Honor `root-only`, `max agents N`, no-subagent and read-only instructions. Children cannot delegate. Role sandbox metadata does not override the active session's permissions.

If named-role metadata is stale, use a fresh generic child with the exact manifest model/effort and current role prompt when the runtime supports that. If it cannot, report the dispatch limitation without choosing a different model.

The old persistent CLI controller, mandatory test/evidence schemas and final-gate machinery are retired. Do not run `native-begin`, `native-gate`, `run` or `revise-run` from an older package as a hidden prerequisite. Existing historical run files are left alone; resume the requested work using its useful plan and results in the current chat. Do not create replacement ledgers, compatibility layers or migration receipts. Save progress to a file only if the user requests it.
