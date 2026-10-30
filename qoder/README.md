# Qoder: Harness Orchestration

[中文](#中文) · [English](#english) · [Repository](https://github.com/AshWood97/harness-orchestration)

## 中文

**使用插件宿主 `orchestrator`，在一个会话中按需调用 14 个独立专业角色。** 插件 v1.1.2 包含 15 个 agent 定义：一个主协调宿主和 14 个子角色。保留当前会话模型/provider，不复制 Codex 模型配置。

[下载 v1.1.2 安装包](https://github.com/AshWood97/harness-orchestration/releases/tag/qoder-v1.1.2) · [同事复用指南](Harness-Orchestration-1.1.2-同事复用指南.md)

### 安装与新会话调用

1. 从 [v1.1.2 Release](https://github.com/AshWood97/harness-orchestration/releases/tag/qoder-v1.1.2) 下载并导入插件 ZIP；ZIP 根目录直接包含 `.qoder-plugin/plugin.json`。
2. 新建会话，在顶部 Agent 选择器选择 **orchestrator**，描述为“主协调器（插件宿主）”。不要选择用户级 **Harness Orchestration** 来直接派发插件角色。
3. 首条消息先自检，确认实际工具暴露插件角色，再开始任务：

```text
先列出你实际可用的 agent 类型，确认包含 harness-orchestration:conductor、
harness-orchestration:explorer、harness-orchestration:worker、
harness-orchestration:reviewer 等 14 个插件角色。
未确认前不要开始任务；缺失时报告具体限制，不模拟角色回答。
全程最多 4 个并发，共享写入串行，子角色不得继续委派。
任务：<你的任务>
```

也可以先只发送自检，看到实际角色清单后再提交任务。不要将提示词中的角色名字当作可用性证据。

若选择器未出现宿主，先确认插件已安装并启用，再新建会话检查。此前的本地安装中，用户也曾明确要求另一个具备 `create_chat_session` 工具的 Qoder 会话，使用以下标识创建宿主会话：

```text
agent-definition:["plugin","harness-orchestration@local","orchestrator"]
```

例如：“用 orchestrator 开一个新会话，任务是……”。此 ID 适用于当时的 `@local` 安装；其他安装来源必须使用运行时实际暴露的 ID。该创建方式在当时用户环境中继承 `dfmodel`，没有切换模型/provider。已有正确宿主会话也可继续复用。插件入口、roster、所需角色或运行时不可用时，v1.1.2 要求当前宿主报告限制并停止或询问，不得自行换入口、换宿主、换角色或自动重试；用户另行明确请求创建会话属于单独操作。

### 为什么之前的入口不成功

| 检查点 | 用户级 Harness Orchestration | 插件宿主 orchestrator |
| --- | --- | --- |
| 本次观察的设置源 | 空 setting-sources | user |
| 实际可派发类型 | 3 个内置类型加自身 | 上述 4 个加 14 个插件角色 |
| 插件角色调用 | Unknown agent type | 使用完整命名空间成功 |
| 判断依据 | UI 显示角色不足以证明可调用 | 实际工具类型与派发回执 |

这是本次 Qoder CN 环境的装载行为，不能推断所有版本都相同。Settings 中启用角色、Agent Team 成员在线、清单注册成功，均不等于当前会话加载了这些定义。以可用的 `list_agents` 或 Agent 工具实际暴露类型及真实派发结果为准。

### 数量、并发与验证边界

用户于 **2026-10-30** 提供的 **v1.1.1** 真实运行结果：宿主会话暴露 18 个可派发类型，包含 `general-purpose`、`Explore`、`Plan`、用户级 `Harness Orchestration`，以及 14 个 `harness-orchestration:<role>`。按 **4/4/4/4/2** 五批派发 18 次，检查了 18 份子会话 transcript、工具状态 `ok` 和最后回复：**18/18 成功，0 失败**。

这是用户报告的实际验证，本次文档同步没有重新执行这些调用，也不公开私人 transcript 或会话 ID。18 是该环境的类型数量，不是保证所有安装都有 18 类型；10+ 表示一个会话累计调用数量，不是同时运行数量。团队与插件委派合计最多四个并发，并服从实际运行时更低上限。

真实任务只选择必要角色，通常 conductor、explorer、worker、reviewer 即可。独立就绪任务可并行，同角色可有多个独立实例，槽位空出后及时补充；共享写入和未确定接口按顺序执行。子角色不继续委派，每个检查问题一个负责人。检查只读，仅为具体未决行为安排最小必要测试。

### 中断、继续与写入恢复

v1.1.2 将恢复规则写入插件：手动中断后等待用户明确要求继续；即使只发送“继续”，也复用有效计划、已完成结果、任务状态和文件归属，不重复派发已完成或仍在运行的任务。只补派依赖已满足的未完成任务，按实际空闲槽位推进。切换模型不代表权限变化，也不直接沿用旧模型对失败原因的判断。

写入任务重派前核对归属路径和实际改动：已完成的不重写，部分完成只补剩余内容，状态不明先核对；共享路径继续串行。明确权限拒绝、用户明确取消整个任务或运行时不可用时停止或询问，不自动重试；无法确定任务状态时先核对，仍不能确定则询问。`interrupted`、`cancelled` 或 `failed` 等文本本身不等于权限拒绝或用户明确取消。

[同事复用指南](Harness-Orchestration-1.1.2-同事复用指南.md)提供中断、可选换模型、发送“继续”的测试步骤和预期结果；本次同步没有重新运行这些恢复测试，不能将 v1.1.1 的派发结果当作 v1.1.2 恢复测试通过的证据。

### 插件更新与旧快照

本次仅切换插件 enabled 开关仍复用了旧 roster。将版本 **1.1.0 → 1.1.1** 并重装本地包后，桌面重新解析出包含 orchestrator 的 15 个定义；用户观察到 roster generation 7。generation 是本地状态，不是安装要求。

以后修改插件文件：同步更新 manifest 和 skill 版本、重新打包并重装，再新建宿主会话检查实际类型和必要派发。不要把开关切换当成重装。平台内部指纹变化只是本次缓存刷新观察，不要求用户计算 hash，也不增加摘要文件。

### Agent Team 与子角色

Agent Team 是固定负责人和成员组合，当前配置界面支持一名负责人加一至四名成员；它不是 14 角色目录。此前 **Harness 核心开发团队** 使用用户级 Harness Orchestration 为负责人，团队创建、启用和选择已验证，但这不能证明其可调用队外插件角色。

**目前推荐使用已验证的 orchestrator 单会话入口来调用完整角色目录。** 不将本次宿主的 18/18 结果当作旧团队执行链的验证。需要尝试团队时，可评估将插件宿主作为负责人，但须独立验证其运行时类型和成员派发；本指南不宣称这一组合已经通过。

### 打包

在仓库根目录执行（macOS/Linux）：

```sh
cd qoder/harness-orchestration
zip -r /tmp/harness-orchestration-qoder-1.1.2.zip .qoder-plugin agents skills hooks LICENSE
```

不要在 ZIP 外包一层目录。hook 使用 `cat` 读取静态规则；Windows 尚未验证。

### 角色与权限

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


角色语义来自 [Codex Native](../.agents/skills/codex-native-orchestrator/roles)，Qoder 名称采用连字符。只读角色无 Bash/Edit/Write；researcher 可查询网页。tester 与 check-runner 仅执行分配的检查，不借 Bash 修改文件。orchestrator 是宿主，其他 14 个角色不继续委派。

## English

### Start with the plugin host

Version **1.1.2** contains **15 agent definitions: one orchestrator host and 14 specialist roles**. Download the package from the [v1.1.2 Release](https://github.com/AshWood97/harness-orchestration/releases/tag/qoder-v1.1.2), import it, start a new chat, and select **orchestrator** (主协调器（插件宿主）). Do not assume the user-level **Harness Orchestration** agent loads the plugin roster. The [colleague guide](Harness-Orchestration-1.1.2-同事复用指南.md) includes installation, verification prompts and troubleshooting.

Before assigning work, ask the host to list the agent types actually exposed by its tools. Confirm all 14 `harness-orchestration:<role>` identifiers. Use full namespaced identifiers, not bare names such as `conductor`. Missing types must be reported, never simulated or silently replaced with built-ins.

If the UI does not list the host, first confirm the plugin is installed and enabled, then check a new session. In a previous local installation, the user explicitly asked another Qoder session with `create_chat_session` to create a host using `agent-definition:["plugin","harness-orchestration@local","orchestrator"]`. Resolve the actual ID for other installation sources. That reported session inherited its existing model (`dfmodel`) without provider changes. Under v1.1.2, the current host must report an unavailable entry, roster, required role or runtime and stop or ask; it must not automatically switch entry, host or role, or retry. A user separately requesting a new session is a distinct action.

### Observed behavior and evidence

In the user's Qoder CN environment, the user-level session had empty setting sources and only three built-ins plus itself. The plugin host loaded the `user` settings source and exposed those four types plus 14 plugin roles. UI visibility is not proof of runtime availability.

On **2026-10-30**, the user reported **18 real Agent calls and 18 child transcripts with v1.1.1**, in batches of **4/4/4/4/2**, with all tool statuses `ok` and final replies checked: **18 passed, zero failed**. This documentation update did not rerun the experiment or publish private session data. Eighteen available types is environment-specific; 10+ cumulative calls does not mean 10+ concurrent agents.

Keep at most four delegated tasks running across team and plugin calls, subject to lower runtime limits. Choose only necessary roles, allow independent instances, refill available slots, serialize shared writes, and prohibit child delegation. Use one owner per checking question and minimal targeted verification.

### Resume and recovery

The v1.1.2 instructions wait for a user's explicit request to resume after manual interruption. Reuse a valid plan, completed results, assignment states and owned paths; do not redispatch completed or still-running work. Resume only unfinished tasks whose dependencies are complete, using actual free slots. A model switch is not a permission change, and the new model should not inherit the previous model's judgment about a failure.

Before redispatching a write, inspect owned paths and actual changes: preserve completed work, finish only the remaining edits, and reconcile unknown states first. Keep shared writes serial. Explicit permission denial, explicit cancellation of the entire task, or runtime unavailability requires stopping or asking rather than automatic retry; if the state cannot be determined, ask. `interrupted`, `cancelled`, or `failed` text alone does not establish permission denial or explicit user cancellation.

The [colleague guide](Harness-Orchestration-1.1.2-同事复用指南.md) gives steps and expected outcomes for interruption, an optional model switch and “继续” (continue). Those recovery scenarios were not rerun in this documentation update; the v1.1.1 dispatch result does not prove v1.1.2 recovery behavior.

### Updating and teams

Toggling enabled reused the stale roster in the reported environment. Bumping 1.1.0 to 1.1.1 and reinstalling the local package refreshed it to include the host. After edits, update package/skill versions together, rebuild, reinstall, and verify a new host session. Platform fingerprint changes are observations, not instructions to compute checksums.

The earlier five-person core Agent Team was created and selectable, but its user-level leader's access to non-member plugin roles was not established. The 18/18 result validates the **orchestrator host session**, not that team's execution path. Prefer the verified host entry for the complete catalog. A team using the plugin host as leader requires separate validation.

Package using the command above. Models inherit the conversation; no credentials or provider configuration are included. macOS/Linux hook behavior is supported by the packaged shell command; Windows remains unverified.
