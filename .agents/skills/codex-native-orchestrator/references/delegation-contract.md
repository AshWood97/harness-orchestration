# Bounded task packets

Design reference for ongoing review: [DeepSeek dsh-superagent research prototype](https://github.com/deepseek-ai/dsh-superagent-prototype), especially its execution and authorization documentation. It is experimental and runs on DeepSeek Harness; adapt relevant ideas to Codex and the user's constraints rather than treating it as a runtime dependency.

Each child gets one objective and one narrow direction for this assignment. Use the role's persistent developer instructions for its working method and the task message for current facts. A frontend, service, caller or documentation focus is an assignment, not a new permanent role.

Include only what the child needs:

- The question or requested behavior, and the condition that makes it complete.
- Original user requirements or accurate excerpts that affect the judgment, relevant evidence locations, files/symbols, known interfaces or external versions, and already established results.
- Read scope, owned edit paths when applicable, dependencies and any concurrently edited neighboring scope.
- The user's boundaries, including no-tests, read-only or other explicit restrictions.
- The expected actual result: answer/change, necessary source locations, and a specific unresolved item if one remains.

Use a fresh child with only the packet context (`fork_turns="none"`) for narrow assignments when the runtime supports it. Reuse the same child for a continuation that benefits from its existing context. Do not forward unrelated conversation history. Prefer the smallest capable catalog role; for mechanic, provide the exact edit recipe, and for check_runner, the exact ordered command list. For an additional diagnostic or checking assignment, identify the concrete in-scope question and why existing inspection/results do not settle it. Selecting agents for already authorized work does not require the user to name them or approve the agent count; it never overrides a user prohibition.

The host's summary must not add requirements or override the user's original intent. If essential original context is unavailable, the child reports what is missing to the host instead of treating the summary as complete.

Route a user's correction or related follow-up to its existing owner when it fits; reuse the child when possible instead of starting duplicate work. If frequent exchanges reveal that a work unit needs shared context or continuous judgment, the host adjusts its boundary rather than repeatedly handing it between owners. A child returns input concerning another task or beyond its assignment to the host for routing and scope decisions. Related context alone does not expand authorization; honor explicit new user instructions and existing constraints.

When a long-running command may need to receive follow-ups, start it with a short yield and retain its session. While it runs, use short waits (about 5 seconds when the runtime permits), handle delivered messages between waits, and continue the same session to its actual result. Do not restart the command just to check progress. Tool calls can delay message delivery, so do not promise a response deadline.

Native children execute only their packet and return useful further subdivisions to the host for dispatch. Their no-delegation boundary applies to those children, not to host parallelism or ZCode's configured internal agents. Writers modify only owned paths and preserve other edits. Planners, researchers and reviewers remain read-only; a finding is not permission to repair it. A missing interface decision or required input is a specific blocker to return to the host, not a reason to invent broader behavior or change models.

Return the actual result, key supporting evidence and its locations, and unresolved questions; avoid a bare conclusion or entire tool output when a concise result suffices. Separate confirmed facts from inferences. Distinguish completed work, waiting for a necessary result and blocked work; do not claim completion while a command or subtask needed for the delivery conclusion is still running. For assigned commands, give the command and observed outcome in chat. Stop once the completion condition is met. Do not create a packet file, hashes, signatures, evidence bundle, log or receipt unless the user explicitly requested that output within the skill's execution boundary.
