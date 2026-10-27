# Harness Orchestration / 多 Harness 角色编排

Plan → implement → inspect → fix or deliver · Codex · ZCode · Qoder

计划 → 执行 → 检查 → 有问题修改、没问题放行 · Codex · ZCode · Qoder

[中文](#中文) · [English](#english)

## 中文

这个仓库提供两个独立安装、按任务选择的 Codex skill、一套 [ZCode 角色编排包](zcode/README.md)，以及 [Qoder 插件](qoder/README.md)。仓库现名为 [AshWood97/harness-orchestration](https://github.com/AshWood97/harness-orchestration)，曾用名为 `codex-three-paths`、`codex-zcode-orchestration`。

| Skill | 用途 |
| --- | --- |
| [Codex Native Orchestration](.agents/skills/codex-native-orchestrator/SKILL.md) | 由规划者按需选择原生 Codex 角色，完成实现与检查。 |
| [Codex ZCode](.agents/skills/codex-zcode/SKILL.md) | 由 Codex 规划、提交有明确边界的 ZCode 任务，并检查实际结果。 |

**v1.0.0** 更新 Native 的 14 个角色：Astra 负责规划和复杂判断，Terra 负责四类高频执行任务，并强化独立任务并发与窄范围提示词。手动技能与 Ultra 使用同一套编排。旧发布编号统一为 v0.x；v0.5.0 引入了专用的 Codex ZCode 接入。

### 安装

在 Codex 中使用内置 `$skill-installer`，从本仓库安装需要的路径：

```text
仓库：AshWood97/harness-orchestration
路径：.agents/skills/codex-native-orchestrator
      .agents/skills/codex-zcode
```

skill 安装到 `${CODEX_HOME:-~/.codex}/skills/`。已有同名安装时先检查个人改动。安装 Codex ZCode 后，再执行运行时设置：

```sh
python3 /absolute/path/to/CODEX_HOME/skills/codex-zcode/scripts/install.py --apply
```

Codex ZCode 需要 **Node.js 22.18+** 和 **Python 3.9+**。安装器使用固定版本的 [Sandyzzx/codex-zcode-bridge 1.2.7](https://github.com/Sandyzzx/codex-zcode-bridge) 共享核心，注册 MCP `codex_zcode`；独立设置位于 `$CODEX_HOME/codex-zcode/runtime-config.json`，任务状态位于同目录的 `state/`。`CODEX_HOME` 默认是 `~/.codex`，可用 `--codex-home` 指定。迁移时可加 `--retire-old-skills`，移除该目录下旧的 External Provider、Harness Bridge 和已安装的 `zcode-orchestrator` 原型；此选项须明确传入。

Native 的 skill 安装和命名 agent 配置是两步；按下方 Native 部分部署固定角色与入口，再开始新会话。调用 skill 不改变用户选择的主会话模型。

### Codex ZCode 使用

从技能菜单选择 **Codex ZCode**、用 `$codex-zcode` 加任务，或直接要求 Codex 使用 ZCode。讨论 ZCode、引用内容或普通任务复杂度不会启用它。实际的 ZCode 调用优先于 Ultra 自动 Native 路由。

默认不传 `model` 或推理参数，沿用 ZCode 当前工作区新会话的默认值；只有用户为当前任务明确指定时才覆盖模型。续接任务保留原模型，换模型应新建任务。默认直接提交 JSON 任务书；指定模型时才查询目录：

```sh
python3 /absolute/path/to/CODEX_HOME/skills/codex-zcode/scripts/zcode.py doctor
python3 /absolute/path/to/CODEX_HOME/skills/codex-zcode/scripts/zcode.py submit --file /absolute/path/to/task.json
# 仅在明确选择模型时查询：
python3 /absolute/path/to/CODEX_HOME/skills/codex-zcode/scripts/zcode.py models --workspace /absolute/path/to/workspace
```

`events`、`status`、`result` 用于跟踪和读取结果，`continue` 用于续接，`cancel` 用于取消；参数与任务格式见 [skill](.agents/skills/codex-zcode/SKILL.md)。运行时仅通过已配置的 ZCode 接口执行任务，不提供 computer-use、UI 或远程控制回退。

### Native 角色与流程

默认流程是 **充分考虑的计划 → 最小实现 → 针对具体问题检查一次 → 有问题修改、没问题放行**。简单任务留在主会话；复杂任务分派确实需要完成的部分。每个检查问题由一个负责人处理，主会话汇总；修复后只看修复和直接影响。用户只要求 Review 时保持只读。

| 角色 | 模型 | 推理强度 |
| --- | --- | --- |
| conductor、design_critic、debugger、guardian | `gpt-6-astra` | `xhigh` |
| explorer、researcher、worker、tester | `gpt-6.1-terra` | `max` |
| reviewer、finding_validator、test_author | `gpt-6.1-sol` | `max` |
| scout、mechanic、check_runner | `gpt-6-luna` | `max` |

保留 14 种角色，不增加永久角色。多角色任务先由 **Conductor 评估依赖并选择实际需要的角色**，主会话负责派遣；同一角色可以有多个不同范围的实例。简单任务、root-only 和禁止子代理的任务留在主会话。专项角色按具体问题选择，不要求用户逐个点名，也不运行整个角色目录。

最多同时运行 **4 个子代理，不含主会话**，并受实际运行时容量限制。输入齐备、依赖已完成且无写入冲突的任务可以并行；有四项必要任务就同时派发四项，空位出现后接续就绪任务。独立模块的探索、资料研究及接口已确定的独立文件实现都可并发；共享写入和依赖保持有序。不为凑满并发制造任务，四个并发也不等于整个任务只能创建四个实例。

每个角色提示词明确职责、输入、工作方法、结果格式、停止条件和执行边界；任务书再给出一个目标、窄方向、相关上下文和文件范围。减少无关历史，并在上下文仍适合时复用子代理。重要改动可从不同的具体功能角度独立检查，先看原始需求和代码，再参考其他结论；不投票、不重复全量 review、不设置自动最终 Guardian。

尽量少做额外测试：先读源码和结果、复用已有观察；重要行为无法据此判断时才安排最小针对性检查，优先现有用例，确有具体缺口才补测试。不因“更稳妥”增加测试、子代理、全量审查、主动安全审查、防御性包装、兼容层、未来抽象或额外校验层。用户明确的不测试、只读等限制优先遵守。

默认禁止 hash/checksum/指纹/签名与额外产物。仅当用户明确要求发布校验、去重、缓存命中或对照已知摘要做拒绝，且结果实际用于该操作时才计算。超出用户任务范围的动作先问一句“我想加 X，因为 Y，是否允许？”，等答复再做。详见[执行规则](.agents/skills/codex-native-orchestrator/SKILL.md)。

将 `.agents/skills/codex-native-orchestrator/roles/*.toml` 放到个人 `CODEX_HOME/agents`，把清单中的 `config_values` 合并到 `CODEX_HOME/config.toml`，保留其他设置和用户选择的主模型。不要追加重复 TOML 键。开始新会话加载更新后的提示词。

#### 技能与 Ultra 入口

从技能菜单选择 **Codex Native Orchestration** 或直接用 `$codex-native-orchestrator` 加任务，手动启用。普通/Max 不按任务内容自动启用。

Ultra 自动入口仅以当前受信 runtime/developer 的 **“Proactive multi-agent delegation is active”** 指令为准；适合分工的项目任务自动加载技能，简单任务仍留在主会话。文字 `ultra`、截图、完整权限和历史使用均不算启用信号。主会话模型和深度不变。**两种入口加载同一份 14 角色清单、固定模型和四子代理并发规则**：Astra/xhigh Conductor 评估，主会话派遣所需角色，包括上述四个 Terra/max 角色。没有固定的 Tester → Reviewer → Guardian 流水线。

实际选择 **Codex ZCode**、用 `$codex-zcode` 加任务或直接要求使用 ZCode 时，该选择优先于 Ultra 的自动 Native 路由；只是讨论、引用或检查 ZCode 不算启用。

安装后可将带标记的入口合并到个人 `CODEX_HOME/AGENTS.md`，保留其他规则；不加 `--apply` 时只显示是否需要更新：

```sh
python /absolute/path/to/CODEX_HOME/skills/codex-native-orchestrator/scripts/install_activation.py --apply
```

安装脚本不计算摘要，不生成备份凭据或日志。

旧持久 CLI runner、哈希证据机制和自动最终 gate 已移除，以及只服务于这些机制的 schema/测试。旧 `native-begin`、`native-gate`、`run`、`revise-run` 等控制器命令不再提供；工作直接由原生 agent 工具协调。旧运行记录不改动，续接时复用已有计划和结论，不迁移、不重复执行，也不默认生成新账本。

### ZCode 角色编排

[ZCode 角色包](zcode/README.md)独立于 Codex ZCode 接入，提供七个自定义角色，配合内置 Explore 和 general-purpose。默认省略模型与推理深度，继承 ZCode 当前会话设置。主 Agent 规划任务、按需选角色，采用相同的计划、执行、检查流程。

安装器默认不改内置角色的模型覆盖。`--model` 是可选覆盖，`--thought-level` 仅与 `--model` 一起使用；需要清理内置模型覆盖时明确传入 `--reset-builtin-models`。带标记的工作流合并保留个人规则，不计算 hash 或生成备份凭据；完整命令见 [ZCode 安装说明](zcode/README.md)。

### Qoder 角色编排

[Qoder 安装说明](qoder/README.md)提供 `harness-orchestration` 1.1.0 桌面插件：完整 14 个角色和一个对适合分工的复杂工程任务自动匹配的 skill。角色省略 `model` 以沿用当前对话模型，只读角色没有 Bash/Edit/Write，保留默认一个写入者、最多四个子角色、一个检查负责人和按需最小检查的规则。

在 Qoder CN 中通过 **Extensions → Plugins → Add Plugin → 上传 Plugin** 导入 ZIP；ZIP 根目录须直接包含 `.qoder-plugin/plugin.json`。为 **Default Agent** 启用本插件后，`UserPromptSubmit` hook 将[默认规则](qoder/harness-orchestration/hooks/default-agent-instructions.txt)加入任务上下文。规则要求先依据当前请求判断；适合分工的复杂工程任务首个工具调用加载完整 skill，随后由插件 Conductor 选角色，在此之前不检索或读取源码；简单任务、`root-only` 和禁止子 Agent 的任务由主 Agent 完成，无需手选入口或另配全局记忆。hook 当前仅用 `cat` 读取插件内静态文本，面向 macOS/Linux，Windows 未验证；实际自动入口检查状态见安装说明。[自定义协调器](qoder/coordinator-instructions.txt) 保留为可选方式。14 角色是可选目录，Team 最多 5 个成员；打包命令及中英文完整步骤见 [Qoder README](qoder/README.md)。

### 公开仓库与验证范围

本仓库只包含源码、文档、占位符示例和测试。不要提交 API key、个人配置、私有模型目录、任务 brief、运行日志或报告。Codex ZCode 的测试验证本地协议和安装行为，不代表所有 ZCode 版本或在线服务均已验证。

CI 只对 Codex ZCode 与 `zcode/` 路径的改动运行相关测试，使用 macOS/Windows、Python 3.11 和 Node.js 24。Native 安装器测试保留为手动选择。日常编排任务不自动触发测试矩阵。见[变更记录](CHANGELOG.md)。

## English

This repository provides two Codex skills installed and selected independently, a [ZCode role package](zcode/README.md), and a [Qoder plugin](qoder/README.md). The repository is [AshWood97/harness-orchestration](https://github.com/AshWood97/harness-orchestration), previously `codex-three-paths` and `codex-zcode-orchestration`.

| Skill | Purpose |
| --- | --- |
| [Codex Native Orchestration](.agents/skills/codex-native-orchestrator/SKILL.md) | Let the planner select native Codex roles for scoped implementation and inspection. |
| [Codex ZCode](.agents/skills/codex-zcode/SKILL.md) | Plan in Codex, submit bounded ZCode tasks, and inspect their actual results. |

**v1.0.0** updates Native's 14 roles: Astra handles planning and difficult judgments, Terra handles four frequent execution roles, and focused prompts support concurrent independent assignments. Manual and Ultra entrypoints share the same orchestration. Historical releases use v0.x numbering; v0.5.0 introduced the dedicated Codex ZCode integration.

### Install

Ask the built-in `$skill-installer` in Codex to install the paths you need from this repository:

```text
Repository: AshWood97/harness-orchestration
Paths: .agents/skills/codex-native-orchestrator
       .agents/skills/codex-zcode
```

Skills install into `${CODEX_HOME:-~/.codex}/skills/`. Inspect an existing installation before replacing personal changes. After installing Codex ZCode, set up its runtime:

```sh
python3 /absolute/path/to/CODEX_HOME/skills/codex-zcode/scripts/install.py --apply
```

Codex ZCode requires **Node.js 22.18+** and **Python 3.9+**. Setup uses the pinned [Sandyzzx/codex-zcode-bridge 1.2.7](https://github.com/Sandyzzx/codex-zcode-bridge) shared core and registers MCP `codex_zcode`. It keeps independent settings at `$CODEX_HOME/codex-zcode/runtime-config.json` and task state in the adjacent `state/` directory. `CODEX_HOME` defaults to `~/.codex`; use `--codex-home` to select another home. Explicitly pass `--retire-old-skills` during migration to remove the installed External Provider, Harness Bridge and `zcode-orchestrator` prototype from that home.

Native skill installation and named-agent configuration are separate steps. Deploy its fixed roles and entrypoint as described below, then start a new session. Invoking the skill does not change the selected host model.

### Use Codex ZCode

Select **Codex ZCode** in the skill menu, invoke `$codex-zcode` with a task, or directly ask Codex to use ZCode. Discussion, quoted content and ordinary task complexity do not activate it. An actual ZCode invocation takes priority over automatic Native routing in Ultra.

Omit `model` and reasoning parameters by default to inherit the ZCode workspace's new-session defaults. Override the model only when the user explicitly selects one for the task. Continuations retain the original model; use a new task to change it. Submit a JSON task file directly; inspect the catalog only for an explicit model selection:

```sh
python3 /absolute/path/to/CODEX_HOME/skills/codex-zcode/scripts/zcode.py doctor
python3 /absolute/path/to/CODEX_HOME/skills/codex-zcode/scripts/zcode.py submit --file /absolute/path/to/task.json
# Only for an explicit model selection:
python3 /absolute/path/to/CODEX_HOME/skills/codex-zcode/scripts/zcode.py models --workspace /absolute/path/to/workspace
```

Use `events`, `status` and `result` to track work and read results, `continue` to resume, and `cancel` to cancel. See the [skill](.agents/skills/codex-zcode/SKILL.md) for arguments and task format. The runtime uses the configured ZCode interface with no computer-use, UI or remote-control fallback.

### Native roles and workflow

Use **plan → implement → inspect each concrete question once → fix concrete issues or deliver**. Understand the requirements and relevant source before editing. Keep simple work in the host and delegate necessary parts of the request. Assign one owner per checking question; the host consolidates the results. After a repair, inspect that repair and its effects; reuse unchanged conclusions. Review-only requests never authorize edits.

| Roles | Model | Effort |
| --- | --- | --- |
| conductor, design_critic, debugger, guardian | `gpt-6-astra` | `xhigh` |
| explorer, researcher, worker, tester | `gpt-6.1-terra` | `max` |
| reviewer, finding_validator, test_author | `gpt-6.1-sol` | `max` |
| scout, mechanic, check_runner | `gpt-6-luna` | `max` |

Keep 14 role types without adding permanent roles. For multi-role work, **Conductor assesses dependencies and selects the roles needed**, and the host dispatches them. A role may have several instances with different scopes. Simple work, root-only and no-subagent requests remain in the host. Specialists answer concrete questions; the user need not name each role. Do not run the entire catalog.

Run at most **four subagents concurrently, excluding the host**, within actual runtime capacity. An assignment is ready when inputs are available, dependencies are satisfied and writes do not conflict. Dispatch all four when four useful assignments are ready, and refill freed slots. Independent exploration, research and edits to separately owned files with settled interfaces can run concurrently; order shared writes and dependencies. Do not invent filler tasks. Four is a concurrency limit, not a limit on total instances over the task.

Each role prompt specifies responsibility, inputs, method, result, stopping conditions and execution boundaries. Each assignment adds one objective, a narrow direction, relevant context and owned paths. Avoid unrelated history; reuse a child when its context still fits. Important changes may receive independent checks of distinct concrete functional questions, using original requirements and source before other conclusions. No voting, duplicate full reviews or automatic final Guardian.

Minimize extra testing: inspect source/results and reuse observations first. Choose the smallest targeted check only for important unresolved behavior, preferring existing cases and adding tests only for a concrete gap. Do not add tests, subagents, full reviews, unsolicited security audits, defensive wrappers, compatibility layers, future abstractions or extra verification layers for reassurance. Explicit no-tests and read-only instructions take precedence.

Do not calculate hashes, checksums, fingerprints or signatures unless the user explicitly requests published checksums, deduplication, cache-hit decisions or known-digest rejection and the result serves that operation. Do not create extra files or logs for traceability. Ask before a scope-expanding action, then wait. See the [skill](.agents/skills/codex-native-orchestrator/SKILL.md).

Place the role TOMLs in personal `CODEX_HOME/agents` and merge the manifest's `config_values` into personal `CODEX_HOME/config.toml`. Preserve unrelated settings and the user's host model; avoid duplicate keys. Start a new session to load updated prompts.

#### Manual and Ultra entrypoints

Keep `allow_implicit_invocation: false`. Select **Codex Native Orchestration** in the skill menu or directly invoke `$codex-native-orchestrator` with a task. Ordinary/Max task matching does not activate it.

The Ultra entrypoint requires the current trusted runtime/developer instruction **"Proactive multi-agent delegation is active"**. It loads the skill for suitable repository work while simple tasks remain in the host. Text saying `ultra`, screenshots, permissions, saved settings and past usage are not activation. **Both entrypoints load the same 14-role manifest, fixed models and four-subagent concurrency rules**: Astra/xhigh Conductor assesses multi-role work, and the host dispatches the selected roles, including the four Terra/max roles above. Preserve the user's host model and effort. No fixed Tester/Reviewer/Guardian chain is imposed. Delegated children do not orchestrate.

Selecting **Codex ZCode**, invoking `$codex-zcode` with a task, or directly asking to use ZCode takes priority over automatic Native routing in Ultra. Discussion, quotations and requests to inspect ZCode do not activate that override.

Run `python /absolute/path/to/CODEX_HOME/skills/codex-native-orchestrator/scripts/install_activation.py --apply` to merge the marked personal AGENTS.md entrypoint, preserving other guidance. Omit `--apply` for a read-only check. It creates no digest, backup receipt or log.

The old persistent CLI runner, hash evidence machinery and automatic final gate have been removed, together with their dedicated schemas/tests. The old controller commands, including `native-begin`, `native-gate`, `run` and `revise-run`, are no longer available. Coordinate work through native agent tools. Historical run files remain untouched; reuse useful plans and results without a migration layer or replacement ledger.

### ZCode role orchestration

The [ZCode role package](zcode/README.md) is independent of the Codex ZCode integration. It supplies seven custom roles alongside built-in Explore and general-purpose. Model and reasoning-depth overrides are omitted by default so roles inherit the current ZCode session settings. The host plans, selects necessary roles, implements and inspects the result.

Installation leaves built-in model overrides intact by default. `--model` is optional, and `--thought-level` requires `--model`; explicitly use `--reset-builtin-models` to clear built-in model overrides. Marked guidance preserves surrounding personal rules without hashes or backup receipts. See the [ZCode installation guide](zcode/README.md) for commands.

### Qoder role orchestration

The [Qoder package](qoder/README.md) ships a desktop plugin named `harness-orchestration`, at version 1.1.0, with all 14 roles and a skill that automatically matches complex engineering work benefiting from division. Agent `model` fields are omitted to follow the conversation model. Read-only roles have no Bash/Edit/Write tools. The workflow defaults to one writer, at most four children, one checking owner, and minimal checks for concrete unresolved questions.

Import the ZIP in Qoder CN through **Extensions → Plugins → Add Plugin → Upload Plugin**. The ZIP root must directly contain `.qoder-plugin/plugin.json`. Enable the plugin for **Default Agent**; its `UserPromptSubmit` hook adds the [default rule](qoder/harness-orchestration/hooks/default-agent-instructions.txt) to task context. The rule decides from the current request: when division helps, the first tool call loads the full skill, followed by the plugin Conductor selecting roles before any source retrieval or reading; simple tasks, `root-only`, and no-subagent requests stay in the host without a manual picker or separate global-memory setup. The hook uses only `cat` to read packaged static text and targets macOS/Linux; Windows is unverified. See the installation guide for automatic-entry check status. The [custom coordinator](qoder/coordinator-instructions.txt) remains optional. Choose necessary roles from the 14-role catalog; Team supports up to five members. See the [bilingual installation and packaging guide](qoder/README.md).

### Public repository and verification limits

This repository contains source, documentation, placeholder examples and tests. Do not commit API keys, personal configuration, private model catalogs, task briefs, run logs or reports. Codex ZCode tests cover local protocol and installation behavior; they do not establish compatibility with every ZCode release or live service.

CI runs relevant checks for changes under Codex ZCode and `zcode/`, using macOS/Windows, Python 3.11 and Node.js 24. Native installer tests remain manually selectable. Everyday orchestration does not automatically trigger a test matrix. See the [changelog](CHANGELOG.md).
