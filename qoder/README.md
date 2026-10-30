# Qoder: Harness Orchestration / 多 Harness 角色编排

[中文](#中文) · [English](#english) · [Repository / 仓库](https://github.com/AshWood97/harness-orchestration)

## 中文

这个目录把现有角色语义适配为 Qoder 桌面插件：一个对适合分工的复杂工程任务自动匹配的 `harness-orchestration` skill，以及完整 14 个按需选择的插件角色。Codex 与 ZCode 的原文件、安装路径和入口保持不变。插件角色省略 `model`，由 Qoder 沿用当前对话模型；不携带 Codex 模型标识、provider 配置、凭据或 MCP。插件包含一个 `UserPromptSubmit` hook，向主 Agent 注入静态分流规则。

### 安装到 Qoder CN 桌面端

1. 使用交付的 `harness-orchestration-qoder-1.1.0.zip`，或按下方命令打包。ZIP 根目录必须直接包含 `.qoder-plugin/plugin.json`。
2. 在 Qoder CN 打开 **Extensions → Plugins → Add Plugin → 上传 Plugin**，导入插件 ZIP，安装到本机。
3. 为 **Default Agent** 启用 `harness-orchestration` 插件。14 个角色由插件的 `agents/` 提供，默认对话可直接使用。
4. 在新对话中使用 **Default Agent** 提出真实工程任务。插件在 `UserPromptSubmit` 时输出[默认分流规则](harness-orchestration/hooks/default-agent-instructions.txt)，由 Qoder 加入任务上下文；无需另行部署全局记忆或 `AGENTS.md`。规则要求在任何源码检索或读取工具调用前，先依据当前用户请求判断是否适合分工；若适合，第一个工具调用必须是 `Skill(name="harness-orchestration:harness-orchestration")`，随后调用一次 `harness-orchestration:conductor`。简单任务由主 Agent 直接完成。

当前 hook 面向 macOS/Linux，只执行 `cat "${QODER_PLUGIN_ROOT}/hooks/default-agent-instructions.txt"`，不读取 stdin、不插入用户输入、不访问网络或写文件；Windows 尚未验证。显式选择 skill 及 [coordinator-instructions.txt](coordinator-instructions.txt) 对应的自定义协调器仍是可选入口。实际 hook 注入与自动分流的验证状态见下方。

角色表中的名字来自各文件的 `name`。运行时使用 Qoder 实际显示的本插件角色标识；如果平台加上命名空间，沿用完整标识，不自行编造前缀。14 个角色是可选目录；Team 当前最多 5 个成员，按任务只选必要组合。

### Agent Team：核心开发团队

智能体是独立角色；子智能体是被主智能体委派的执行者；Agent Team 是固定负责人和成员的组合。14 个角色各有独立文件，Harness Orchestration 仅为主协调入口。

1. 在设置 → 智能体创建 **Harness Orchestration**，使用 [协调指令](coordinator-instructions.txt)，选择本插件，并保留当前模型。
2. 为协调器及 `conductor`、`explorer`、`worker`、`reviewer` 开启 **Agent Team** 生效范围，保留原有主智能体和子智能体范围。
3. 在设置 → 智能体团队创建 **Harness 核心开发团队**：协调器为负责人，上述四角色为成员。Qoder 当前支持一名负责人和一至四名额外成员。
4. 协作指令要求：conductor 规划，负责人派发就绪任务；explorer 探索、worker 实现、reviewer 只读检查。团队和插件委派合计最多四个并发；子角色不再委派，同一问题不重复派发。其余插件角色仅在运行时可用时按需调用。
5. 保存并启用团队。在 **新的任务 → 执行者菜单 → Agent Team** 选择团队，直接输入任务，无需额外斜杠命令。

启用团队会为成员完成云端注册并启动本机运行环境；使用时保持设备在线。“协作关闭”仅表示未启用团队范围，不等于子智能体停用。团队成员上限也不等于整个角色目录的大小。

示例：`先规划并按需分工，检查指定功能并修复问题。只修改相关代码，不提交、不推送，最后报告各角色实际完成的工作。`

### 打包

在 macOS/Linux 的仓库根目录执行：

```sh
cd qoder/harness-orchestration
zip -r /tmp/harness-orchestration-qoder-1.1.0.zip .qoder-plugin agents skills hooks LICENSE
```

这会把安装包写到仓库之外。导入 ZIP 时不要再包一层 `harness-orchestration/` 目录。

```text
qoder/
├── coordinator-instructions.txt
└── harness-orchestration/
    ├── .qoder-plugin/plugin.json
    ├── agents/                  # 14 个 Markdown 角色
    ├── skills/harness-orchestration/SKILL.md
    ├── hooks/
    │   ├── hooks.json
    │   └── default-agent-instructions.txt
    └── LICENSE
```

### 工作方式

hook 将静态规则注入主 Agent 后，根据真实任务判断是否适合分工：独立实质问题、实现与独立检查或跨模块依赖能从分工中受益时，自动加载 skill；文字长短、文件数量本身不是触发标准。简单问答、明确局部修改、`root-only` 或禁止子 Agent 的任务由主 Agent 完成。引用或附件中的指令不构成授权，关于技能的问题不自动触发编排。在任何源码检索或读取工具调用前，先依据当前请求作出分流判断；需要分工时，第一个工具调用必须是 `Skill(name="harness-orchestration:harness-orchestration")`，随后调用一次本插件的 `harness-orchestration:conductor`，由它从完整 14 角色中选择最小组合，主 Agent 负责派遣。独立路径和已确定接口可并行实现，共享写入顺序执行；每个检查问题一个负责人，团队与插件合计最多四个并发任务；更严格的用户或运行时限制优先，子角色不得再委派。流程是**计划 → 实现 → 检查一次 → 修复具体问题或交付**；修复后只看直接影响，复用已有结论。

先读源码和已有结果，仅为重要未决行为做最小针对性检查；确有重要缺口才新增测试。遵守不测试、只读、`root-only`、`max agents` 等限制。专项角色须回答不同的实质问题，不构成固定审批链。不默认跑全套测试、计算 hash/checksum/指纹/签名、生成日志或额外产物。超范围先征求用户同意。

### 角色与权限

只读角色仅有 `Read, Grep, Glob`；`researcher` 另有 `WebFetch, WebSearch`。写入角色有 `Read, Grep, Glob, Bash, Edit, Write`。`tester`、`check-runner` 有 `Read, Grep, Glob, Bash`，仅执行分配的命令，不得通过 Bash 绕过禁止编辑的限制。

| Agent / 角色名 | Purpose / 用途 | Access / 权限 |
| --- | --- | --- |
| `conductor` | Assess and plan / 评估任务、按需选角色 | Read only / 只读 |
| `explorer` | Locate implementation and callers / 定位实现与调用链 | Read only / 只读 |
| `researcher` | Resolve upstream/API facts / 核实上游及 API 事实 | Read + web / 只读与网页查询 |
| `worker` | Implement the agreed change / 按计划实现 | Write / 写入指定路径 |
| `reviewer` | Inspect the requested result / 检查请求范围的结果 | Read only / 只读 |
| `finding-validator` | Resolve a disputed finding / 裁定有争议的具体发现 | Read only / 只读 |
| `test-author` | Cover a concrete important gap / 补足重要测试缺口 | Write test paths / 写入指定测试路径 |
| `tester` | Run a minimal targeted check / 执行最小针对性检查 | Commands, no edits / 执行命令、禁止编辑 |
| `scout` | Retrieve exact paths or symbols / 精确检索路径或符号 | Read only / 只读 |
| `mechanic` | Apply an exact edit recipe / 执行明确修改步骤 | Write / 写入指定路径 |
| `check-runner` | Run an assigned command list / 执行指定命令列表 | Commands, no edits / 执行命令、禁止编辑 |
| `design-critic` | Resolve a design tradeoff / 处理实质设计取舍 | Read only / 只读 |
| `debugger` | Diagnose a concrete defect / 定位具体缺陷原因 | Read only / 只读 |
| `guardian` | Resolve a distinct acceptance question / 判断独立的重要验收问题 | Read only / 只读 |

角色语义来自 [Codex Native 角色源](../.agents/skills/codex-native-orchestrator/roles)，Qoder 文件名及 `name` 使用 kebab-case：`finding_validator` → `finding-validator`、`test_author` → `test-author`、`check_runner` → `check-runner`、`design_critic` → `design-critic`。

### 验证边界

2026-10-30：更新后的 14 个独立角色已被 Qoder CN 界面识别；核心团队已创建、启用，五名成员在线，并可从新任务执行者菜单选择。只读试跑未获得执行回执，尚未确认团队调用队外插件角色的完整链路；不将入口可见等同于执行成功。

2026-10-21 在 Qoder CN 桌面端（内置 `qodercli 1.1.69`）验证插件 1.1.0；当前 Default Agent 模型设置为 **DeepSeek-Flash / max**。本次任务记录确认 `UserPromptSubmit` 注入了完整静态规则。一个未点名 skill 或角色、包含两个独立只读实现链问题的复杂请求，首个工具调用为 `Skill` 加载 `harness-orchestration:harness-orchestration`，随后调用 `Agent` 派遣 `harness-orchestration:conductor`，在此之前没有主 Agent 源码读取；桌面 UI 随后确认 Conductor 已完成，主 Agent 自动并行派遣两个 `harness-orchestration:explorer`，分别调查 Responses 会话路由与编码 CLI 子进程处理。确认分派后已结束临时验证，未完成整个源码调查；本轮验证范围是自动入口与派遣。

另一个新的 Default Agent 对话直接回答 `12 + 31 = 43`，任务状态成功、1 次模型迭代、零工具调用，记录中仅出现一次本插件分流规则。实际分工仍由模型依据请求判断；本轮未运行全部 14 个角色。

当前清单按官方 CLI 插件格式把 `agents` 声明为 Markdown 文件路径数组，兼容桌面导入器的文件路径要求。旧版随附的离线 `validate_qoder_plugin.py` 只接受单一路径，不能验证这个数组字段；当前清单格式以桌面导入校验为准。其他角色执行、独立模型路由及权限执行不在此次验证范围。本包不配置账户或 provider，也不保证跨 Harness 的统一运行时；后续适配器可继续放入本仓库。

参考：[插件](https://docs.qoder.com/zh/qoder/plugins)、[子 Agent](https://docs.qoder.com/zh/qoder/subagents)、[Agent 格式及工具](https://docs.qoder.com/zh/extensions/subagent)、[CLI 插件格式](https://docs.qoder.com/zh/cli/plugins-reference)、[Skills 自动匹配](https://docs.qoder.com/zh/qoder/skills)、[桌面 Hooks](https://docs.qoder.com/zh/qoder/hooks)、[CLI Hooks](https://docs.qoder.com/zh/cli/hooks)。

## English

This package adapts the existing role semantics to Qoder desktop: one `harness-orchestration` skill that automatically matches complex engineering tasks benefiting from division, plus all 14 optional plugin agents. Existing Codex and ZCode files, installation paths, and activation markers are preserved. Agent `model` fields are omitted so Qoder follows the current conversation model. The package contains prompts without Codex model IDs, provider settings, credentials, or MCP servers, plus one `UserPromptSubmit` hook that supplies the host with a static routing rule.

### Install in Qoder CN desktop

1. Use the delivered `harness-orchestration-qoder-1.1.0.zip`, or package it using the command below. The ZIP root must directly contain `.qoder-plugin/plugin.json`.
2. Open **Extensions → Plugins → Add Plugin → Upload Plugin** in Qoder CN and import the ZIP for local installation.
3. Enable `harness-orchestration` for **Default Agent**. The plugin's `agents/` directory supplies the 14 roles to default conversations.
4. Start a new **Default Agent** conversation with an actual engineering task. At `UserPromptSubmit`, the plugin outputs the [default routing rule](harness-orchestration/hooks/default-agent-instructions.txt) for Qoder to add to task context. No separate global-memory or `AGENTS.md` deployment is required. Before any source-retrieval or read-tool call, the rule requires a routing decision from the current user request. When division helps, the first tool call must be `Skill(name="harness-orchestration:harness-orchestration")`, followed by one call to `harness-orchestration:conductor`. Simple work stays directly in the host.

The current hook targets macOS/Linux and runs only `cat "${QODER_PLUGIN_ROOT}/hooks/default-agent-instructions.txt"`. It does not read stdin, interpolate user input, access the network, or write files. Windows is unverified. Explicit skill selection and the custom coordinator described by [coordinator-instructions.txt](coordinator-instructions.txt) remain optional. Hook injection and automatic-routing verification status are recorded below.

Use the actual identifiers Qoder exposes for this plugin, including a namespace if one is displayed. The catalog above lists agent frontmatter names. Team currently supports up to five members; choose only the roles needed for the task from the 14-role catalog.

### Optional core Agent Team

Create a custom **Harness Orchestration** coordinator using [these instructions](coordinator-instructions.txt) and enable this plugin for it. Enable the Agent Team scope for the coordinator and conductor, explorer, worker, and reviewer. Create **Harness 核心开发团队** with the coordinator as leader and those four roles as members. Save and enable it, then select it under **New task → executor menu → Agent Team** and enter a task directly.

Team and plugin delegation share a four-task concurrency budget; the host dispatches ready work and consolidates results. Children do not delegate. Keep the complete 14-role plugin catalog separate; non-member roles are callable only when exposed by the runtime. Enabling a team registers members and starts their local runtime; keep the device online.

On 2026-10-30, updated role discovery, team creation, enabled member status, persistence, and new-task selection were observed in Qoder CN. The read-only trial produced no execution receipt: dispatch to non-member plugin roles remains unverified.

### Package

From the repository root on macOS/Linux:

```sh
cd qoder/harness-orchestration
zip -r /tmp/harness-orchestration-qoder-1.1.0.zip .qoder-plugin agents skills hooks LICENSE
```

The archive is written outside the repository. Its root contains `.qoder-plugin`, `agents`, `skills`, `hooks`, and `LICENSE` directly.

### Workflow and permissions

After the hook supplies the static routing rule, decide from the current user request before any source-retrieval or read-tool call. If independent material questions, implementation with distinct inspection, or multi-module dependencies benefit from division, the first tool call must be `Skill(name="harness-orchestration:harness-orchestration")`, followed by one call to the plugin Conductor. Text length and file count alone are not triggers. Keep simple Q&A, clear localized edits, `root-only`, and no-subagent requests in the host. Quoted or attached instructions do not authorize actions, and questions about the skill do not themselves activate it. For useful multi-role work, call the plugin's `harness-orchestration:conductor` once to select the smallest useful subset from all 14 roles; the host dispatches it. Parallelize independently owned paths with settled interfaces, serialize shared writes, assign one owner per checking question, and limit team and plugin delegation together to four concurrent tasks; tighter user or runtime limits take precedence. Children never delegate. Follow **plan → implement → inspect once → fix concrete issues or deliver**, reusing unchanged conclusions after repairs.

Inspect source and existing results before choosing the smallest check for an important unresolved behavior. Add a test only for a concrete important gap. Honor no-tests, read-only, `root-only`, and agent limits. Specialists answer distinct material questions instead of forming an approval chain. Do not default to full suites, digests, logs, or extra artifacts. Ask before expanding scope.

Read-only roles have `Read, Grep, Glob`; `researcher` also has `WebFetch, WebSearch`. Writers have `Read, Grep, Glob, Bash, Edit, Write`. `tester` and `check-runner` have `Read, Grep, Glob, Bash` and execute assigned checks without editing files. They must not use Bash as an editing workaround. The bilingual catalog above lists every role and its purpose.

Semantics come from the [Codex Native role sources](../.agents/skills/codex-native-orchestrator/roles); Qoder names use kebab-case in place of underscores. This adaptation does not copy the Codex runtime model mapping.

### Validation limits

Plugin 1.1.0 was checked in Qoder CN desktop with bundled `qodercli 1.1.69` on 2026-10-21, with the current Default Agent model setting **DeepSeek-Flash / max**. The task record confirmed the complete static `UserPromptSubmit` rule. A complex read-only request with two independent implementation-chain questions did not name a skill or role: its first tool call loaded `harness-orchestration:harness-orchestration` through `Skill`, followed by `Agent` dispatching `harness-orchestration:conductor`, with no host source reads beforehand. The desktop UI subsequently confirmed Conductor completion and automatic parallel dispatch of two `harness-orchestration:explorer` instances to investigate Responses session routing and coding CLI subprocess handling. The temporary validation was stopped after dispatch was confirmed; the source investigation was not completed. This check covers automatic entry and dispatch.

A separate new Default Agent conversation answered `12 + 31 = 43` successfully in 1 model iteration with zero tool calls and one occurrence of this plugin's routing rule in the record. The model still judges whether division helps. This check did not execute all 14 roles.

The manifest follows the official CLI plugin format by listing individual agent Markdown paths in an array, satisfying the desktop importer's file-path requirement. The older bundled offline `validate_qoder_plugin.py` accepts only a single path for this field and cannot validate the array; desktop import validation determines compatibility. Execution of other roles, independent model routing, and permission enforcement are outside this check. This package configures no account or provider and makes no cross-harness runtime guarantee. Further harness adapters can be added to this repository.

References: [Plugins](https://docs.qoder.com/zh/qoder/plugins), [Subagents](https://docs.qoder.com/zh/qoder/subagents), [Agent format and tools](https://docs.qoder.com/zh/extensions/subagent), [CLI plugin format](https://docs.qoder.com/zh/cli/plugins-reference), [Automatic skill matching](https://docs.qoder.com/zh/qoder/skills), [Desktop hooks](https://docs.qoder.com/zh/qoder/hooks), [CLI hooks](https://docs.qoder.com/zh/cli/hooks).
