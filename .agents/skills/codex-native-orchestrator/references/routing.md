# Planner-led role selection and dispatch

After either manual or Ultra activation, conductor assesses multi-role work once; the host dispatches its plan using the same manifest models. Children never delegate. Simple work and root-only stay with the host. User naming of individual roles is not required, but explicit no-tests, no-subagent and read-only instructions remain binding.

Minimize unnecessary work, not useful parallelism. Judge scope by the work performed: splitting already requested work among capable agents does not expand scope or require separate approval. A role type is not a single-use slot: several scout, mechanic, explorer or worker instances may address different bounded tasks. Select assignments for the requested result, not to exercise the catalog.

## Use available capacity

Identify each assignment's goal, required inputs, dependencies, owned paths and completion condition in the existing conversation plan. Ready means its needed inputs are available and it can proceed without another unfinished assignment's result or conflicting writes. Start assignments that unblock later work first.

Dispatch independent ready work together, up to four running subagents and the actual runtime capacity. If four useful independent assignments are ready, use all four. For multi-module exploration or multi-source research, look for independent branches rather than defaulting to one or two agents. For example, three explorers can inspect separate frontend, service and caller scopes while one researcher resolves an external API question. Do not split a simple lookup or repeat a search merely to fill slots.

As a child finishes, use its result and fill available capacity with the next ready assignment. Do not wait for an entire batch when unrelated work can proceed. Four is the simultaneous execution limit, not the total number of instances over the task. Reuse a child when its role and context fit; otherwise use a fresh bounded instance. Shared write targets or unresolved interface dependencies require ordered edits. The host performs useful independent work while children run and does not duplicate their investigations.

## Choose a role for its concrete output

| Concrete need | Role and bounded result |
| --- | --- |
| Plan dependencies, ready branches and completion conditions | conductor; one plan returned to the host |
| Find implementation, callers and behavior in a bounded code area | explorer; paths, symbols and confirmed call/data flow |
| Retrieve an exact path, symbol or inventory | scout; the requested facts only |
| Resolve an external API or version fact required by implementation | researcher; primary source, applicable version and unresolved uncertainty |
| Implement agreed behavior in owned paths | worker; scoped change and any specific blocker |
| Apply an exact edit recipe | mechanic; the prescribed change only |
| Compare the result with requirements and direct callers | reviewer or host; one owner per concrete question |
| Diagnose a reported defect whose cause is unclear | debugger; supported cause and smallest repair direction, no retry-count trigger |
| Resolve an unsettled design choice in the current task | design_critic; consequence, tradeoff and concrete recommendation |
| Resolve a disputed finding affecting delivery | finding_validator; confirmed, refuted or unresolved for that finding |
| Resolve a distinct consequential result question left after ordinary inspection | guardian; that question only, never a routine final gate |
| Fill a demonstrated test gap in an assigned testing task | test_author; the smallest relevant case in owned test paths |
| Settle an assigned behavioral question through an existing test or reproduction | tester; actual command and outcome |
| Execute a necessary exact command list | check_runner; ordered command outcomes, not another tester on the same commands |

Prefer the smallest capable role from the fixed catalog. Use Luna max `scout` for exact retrieval, `mechanic` for prescribed edits and `check_runner` for a necessary exact command list. When several such assignments are independent, dispatch them concurrently instead of keeping them in the host or promoting them to a larger model by default. Do not force uncertain design or implementation into a mechanical packet merely to use Luna; use the appropriate catalog role when its capabilities are needed. Preserve each role's configured model and effort.

Terra assignments need a clear question or expected behavior and relevant context. Unsettled design decisions return to the host or an existing design/diagnostic role before implementation; do not silently change a role's model.

Use independent checks for important changes only when they answer distinct functional questions, such as changed behavior and its direct caller contract. Provide original requirements and source without asking a checker to endorse another conclusion. The host consolidates the grounds; a concrete disputed finding may need finding_validator, not a vote or a new full review.

Inspect source/results and reuse existing observations first. Do not invent extra work, duplicate checks or add unnecessary tests, security audits, full reviews or refactors for reassurance. This restriction does not limit useful parallel execution of the requested work. An additional diagnostic or checking assignment must resolve an actual in-scope unknown; prefer an existing focused test, and add a case only for an assigned concrete gap. No routine suites, benchmarks, experiments, extra logs or evidence files. Stop when the question is resolved, reuse unaffected results after repairs, and return scope-expanding proposals to the host before acting.
