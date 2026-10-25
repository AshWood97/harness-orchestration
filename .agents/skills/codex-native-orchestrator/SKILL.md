---
name: codex-native-orchestrator
description: Plan, implement and check scoped repository work with native Codex roles when explicitly invoked or authorized by the current Ultra runtime. Let the planner select the roles actually needed, while minimizing extra tests and repeated review.
---

# Codex Native Orchestration

## Activation: manual invocation or Ultra

Only the primary/host agent coordinates this workflow. Delegated children execute their assigned packet and never start another orchestration.

A new task requires either entrypoint:

- **Manual:** The user selects **Codex Native Orchestration** from the skill/slash menu or directly invokes `$codex-native-orchestrator` with a task. Typing `/codex` only filters the menu. Questions, quotations, screenshots and requests to inspect or edit this skill are not invocations.
- **Ultra:** The latest trusted runtime/developer `<multi_agent_mode>` instruction says **"Proactive multi-agent delegation is active"**, and the repository task benefits from division of the requested work. Simple questions and localized edits remain in the host.

An actual ZCode invocation takes priority over the automatic Ultra entrypoint: the user selects **Codex ZCode**, directly invokes `$codex-zcode` with a task, or directly asks to use ZCode for that task. Follow that choice instead of starting Native automatically. Discussion, quotations, screenshots and requests to inspect or edit ZCode or its skill do not invoke it.

Ordinary/Max task matching, the word `ultra`, full access, saved model settings, available agent tools and earlier skill use do not activate this skill. A later explicit-request-only runtime instruction disables automatic activation for new tasks. Unknown mode requires manual invocation. Keep `policy.allow_implicit_invocation: false`; the [activation block](references/activation.md) loads this skill conditionally.

Both entrypoints use the same workflow. Continue unfinished work from its existing plan and results; do not restart completed steps. Re-evaluate activation for independent new tasks. Do not inspect or change the host model/effort to match a role.

## Execution boundary

Do only the user's requested work and deliver the minimum working result. Do not add compatibility layers, defensive wrappers, future abstractions, adjacent refactors, duplicate inspections or extra output files for hypothetical benefit.

Do not calculate SHA-256, MD5, checksums, fingerprints or signatures, create `.sha256` files, or add integrity/evidence layers by default. Hashing is allowed only when the user explicitly requests published checksums, deduplication, cache-hit decisions, or rejection against a known digest, and the result is actually published or consumed by that requested operation. A digest without a downstream consumer is forbidden. "Just in case", professionalism and future traceability are not authorization.

The planner may select any available role, including test and specialist review roles, when a concrete need within the user's task justifies it. The user does not need to name each role or separately request each necessary check. An explicit user prohibition, such as no tests or read-only, still takes precedence.

Minimize extra testing. Start with source/result inspection and reuse existing observations. Add a targeted test or command only when an important behavior or decision cannot be adequately resolved from those sources. Prefer existing focused tests; author new cases only for a concrete gap. Do not default to full suites, build matrices, benchmarks, A/B or mutation experiments, separate test environments or another review pass. A role's availability, task size or general importance alone is not a reason to use it. Say briefly which concrete question a selected specialist or test will resolve; do not create a new approval form, ledger or evidence layer.

When a proposed addition exceeds the requested scope, stop that addition, ask one sentence — “我想加 X，因为 Y，是否允许？” — and wait. Do not do it first or ask about routine work already authorized.

## Plan → implement → check → fix or release

1. **Plan:** Understand the goal, relevant source, constraints, dependencies and completion conditions. Decide the smallest implementation before editing. Keep one proportionate plan in the conversation; revise only facts that changed. The host handles simple work and `root-only`. For work entering multi-role orchestration, use one `conductor` to assess the task and select the roles it actually needs. Give it access to the full role catalog; do not restrict specialists to user-named requests. The host dispatches its selections without nested delegation.
2. **Implement:** The host or one suitable writer makes the scoped change. Delegate only actual parts of the authorized work. Share the relevant plan and paths, not the whole conversation. Order dependent edits; use parallel writers only when the requested work actually needs independent parts.
3. **Check once:** The host or one `reviewer` compares the actual result/diff with the requirements and relevant callers. This is a focused content/code inspection. The plan may separately assign a minimal targeted test or specialist to resolve a concrete important question. Choose one owner for each question; do not repeat the same check in the host and another role. A review-only request produces findings and never authorizes edits.
4. **Fix or release:** For an implementation request, fix concrete in-scope defects, then inspect only the repair and directly affected paths. Reuse unchanged conclusions. If the result meets the request and no concrete issue remains, deliver immediately. Do not append Guardian, a fresh reviewer, a test rerun or a diagnostic role as a routine final step. Add a role only for a concrete unresolved question that materially affects the result; rerun only a check whose relevant inputs changed. There is no fixed number of repair waves. If a repair needs new scope or a missing decision, explain that specific blocker.

See [routing](references/routing.md) when assigning work, [delegation](references/delegation-contract.md) when forming a packet, and [checking](references/quality-workflow.md) for the completion boundary.

## Roles and runtime

| Roles | Model | Effort |
| --- | --- | --- |
| conductor, explorer, researcher, worker, reviewer, finding_validator, test_author, tester | `gpt-6.1-sol` | `max` |
| scout, mechanic, check_runner | `gpt-6-luna` | `max` |
| design_critic, debugger, guardian | `gpt-6-astra` | `xhigh` |

The JSON manifest defines the named role models and efforts. Preserve them; do not silently substitute. Use native agent tools directly. All roles, including `test_author`, `tester`, `check_runner`, `guardian`, `design_critic` and `finding_validator`, are available for planner selection based on the actual task. Do not require the user to request these names. Selecting roles means choosing a useful subset, not running the entire catalog. A missing test report, digest or Guardian verdict alone does not block completion; a concrete important unresolved behavior does.

Default to one writer and at most four children, only as needed. Honor `root-only`, `max agents N` and `read-only`; `root-only` uses the host for planning, implementation and inspection. Children cannot delegate. Sandbox metadata describes the requested profile, not stronger permissions than the active session grants.

If named-role metadata is stale, use a fresh generic child with the exact manifest model/effort and current role prompt when the runtime supports that. If it cannot, report the dispatch limitation without choosing a different model.

Version 4 removes the old persistent CLI controller, mandatory test/evidence schemas and final-gate machinery. Do not run `native-begin`, `native-gate`, `run` or `revise-run` from an older package as a hidden prerequisite. Existing historical run files are left alone; resume the requested work using its useful plan and results in the current chat. Do not create replacement ledgers, compatibility layers or migration receipts. Save progress to a file only if the user requests it.
