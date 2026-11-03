# ZCode 角色编排 / ZCode orchestration

当前配置使用本仓库的源码安装。此前的 [Turbo 2.0 安装包](https://github.com/AshWood97/harness-orchestration/releases/tag/zcode-v2.0.0)和[同事指南](ZCode-Turbo-2.0-同事安装指南.md)为历史版本，其命令针对旧安装包，不适用于当前源码安装器。

当前源码版本为 3.0.0，尚未发布对应 Release。主 Agent 规划、派发并整合结果，按需选择十个自定义角色和两个内置角色。角色不指定统一模型；已有的角色模型选择保留，没有单独设置时按 ZCode 的会话配置执行。每个任务限定目标、文件归属和相关上下文。

本包提供一套积极、按需使用多智能体的规则，见 [AGENTS.md](AGENTS.md)。需求明确、影响局部且无未解决接口或高风险行为的简单任务由主 Agent 直接完成；适合分工的任务优先派发互不冲突的独立工作。分级和协作波次仅为可裁剪的示例，不为凑并发或波次增加测试、重复审查或其他未授权工作。用户的只读、不测试、禁止委派等限制优先。

最多并发四个子代理，不含主 Agent，并服从实际运行时容量。有四项必要且独立的就绪任务就同时派发，允许同角色多个实例，运行时支持时空位出现后接续任务；前台批次阻塞或后台补位能力未知时按实际能力安排。独立文件且接口确定的实现可并行；共享写入和未完成依赖保持有序，不为凑满并发制造任务。

| 工作 | 角色与结果 |
| --- | --- |
| 查清一个模块的实现和调用链 | Explore（内置）；位置、流程和具体未知项 |
| 精确查询路径、符号或清单 | scout；所需事实和实际搜索范围 |
| 按确定接口与行为实施修改 | general-purpose（内置）；仅修改分配文件 |
| 按明确步骤完成机械修改 | mechanic；指定改动和未完成步骤 |
| 解决必需的外部 API、版本或上游事实 | docs-researcher；一手来源、适用版本和答案 |
| 检查一个具体功能问题 | 主 Agent 或 code-reviewer；一个问题一个负责人 |
| 诊断已报告且原因不明的缺陷 | debugger；有依据的原因和最小修复方向 |
| 解决一个未确定的设计取舍 | design-critic；具体后果、取舍和建议 |
| 核验一条争议发现 | finding-validator；成立、不成立或尚无法确定 |
| 补已分配的具体测试缺口 | test-author；最小用例 |
| 用现有测试或最小复现回答行为疑点 | test-verifier；实际命令和观察结果 |
| 原样执行有序命令清单 | check-runner；命令和实际结果，失败即停止 |

角色目录可选，不是每次必须执行的流水线。无需用户逐个点名角色；必要性判断不能覆盖用户的明确禁止。

十个自定义角色设置 `injectAgentsMd: true`，请求 ZCode 自动注入适用的项目规则，实际生效以运行时为准；主 Agent 派单时仍须明确传递该任务的用户限制、允许路径与动作、完成条件和外层预算。内置 Explore 的规则注入不可假定，派单时应明确传递适用的项目及用户约束。公共 `status` 描述角色执行，只有裁定发现时才补 `verdict`，不把角色完成当作最终验收。

每个检查问题由一个负责人处理，主 Agent 汇总；交叉检查回答不同的具体功能问题。Review 只读，不设置自动最终审核。先读源码和已有结果，仅对重要且未解决的行为安排最小必要检查。禁止自行增加哈希、安全审查、防御包装、兼容层、未来抽象、重复 Review、额外测试或产物；超范围先询问。

## 安装

使用 Python 3.11+。在仓库根目录先预览，再根据结果应用：

```sh
# 预览和应用单套规则
python zcode/scripts/install.py
python zcode/scripts/install.py --apply
```

默认安装到 `~/.zcode`，可用 `--zcode-home` 指定目录。预览会显示待修改内容及冲突；已有角色的正文、工具等内容与模板不同时，须检查后显式添加 `--replace-existing` 才会替换：

```sh
python zcode/scripts/install.py --replace-existing --apply
```

默认保留已有自定义角色 Markdown 中的 `model` / `thoughtLevel` 字段，且不更改 ZCode 界面中的模型设置；没有单独设置时由会话配置决定，具体模型选择与优先级以 ZCode 为准。安装器不计算摘要，不生成备份、收据或日志文件。

`AGENTS.md` 的 `codex-zcode-orchestration:quality` 标记只包围本工作流，更新时替换该区块，标记外的个人规则保留。

如需显式固定十个自定义角色的模型，仍可使用 `--model "your-provider/your-model" --apply`。单独指定模型不会固定思考等级；可额外加 `--thought-level`，其值应由所选模型支持，并且必须同时指定 `--model`。

默认安装不会改动内置 Explore 和 general-purpose 的独立模型选择。需要恢复这两个角色的继承行为时，先预览，再应用：

```sh
python zcode/scripts/install.py --reset-builtin-models
python zcode/scripts/install.py --reset-builtin-models --apply
```

该开关仅清除 `v2/agents-state.json` 中这两个角色的旧版模型、旧版思考等级和新版模型选择覆盖，保留其他角色、插件覆盖、禁用 ID 和其他字段。文件不存在或没有相应覆盖时不写入。所有变更都先检查冲突，逐文件原子写入；中途失败会回滚已写文件，并拒绝覆盖期间发生的并发修改。更新后开始新会话，现有子智能体保留启动时的配置。

当前规则吸收了此前配置中积极分工的做法。本仓库尚未独立复测当前版本 ZCode 界面中的实际并发、规则注入或模型选择，实际行为以所用运行时为准。

## English

The package supplies one set of rules and ten custom roles plus the built-in Explore and general-purpose roles. The host proactively delegates independent work when division helps, while handling clear, localized, low-risk tasks directly. The tiers and collaboration waves are adaptable examples, not a requirement to add tests, repeated reviews, or other unrequested work. Explicit user restrictions take precedence. The previous [Turbo 2.0 release](https://github.com/AshWood97/harness-orchestration/releases/tag/zcode-v2.0.0) and its colleague guide are historical; their commands target the old package rather than the current source installer.

Run at most four subagents concurrently, excluding the host and subject to runtime capacity. Dispatch independent ready work together and allow multiple instances of a role; refill freed slots only if the actual runtime supports it, otherwise respect foreground batch semantics. Parallel writers need separately owned files and settled interfaces; shared writes and dependencies stay ordered. Do not create filler tasks. Assign one owner per concrete checking question, keep review read-only and use independent checks only for distinct functional questions.

The ten custom roles set `injectAgentsMd: true` so ZCode can load applicable project rules. The host still passes task-specific user limits, allowed actions, owned paths, completion conditions and outer budget. Do not assume project rules are automatically injected into the built-in Explore role: pass its applicable project and user constraints explicitly. Execution `status` is separate from an optional finding `verdict` and from host acceptance.

With Python 3.11+, run `python zcode/scripts/install.py` to preview the rules and add `--apply` to install. Inspect role conflicts before explicitly adding `--replace-existing`. The default home is `~/.zcode`, or specify `--zcode-home`.

By default the installer preserves existing custom role Markdown `model` / `thoughtLevel` fields and leaves UI model settings unchanged. `--model provider-id/model-id` explicitly overrides the custom-role model; `--thought-level` requires `--model`. Existing built-in choices are preserved unless `--reset-builtin-models` is explicitly requested. Model selection precedence is determined by ZCode. Marked guidance preserves surrounding personal rules. Start a new session to load updated prompts.

Inspect source and reuse results before considering an extra test. No unsolicited security audits, defensive wrappers, compatibility layers, future abstractions, duplicate reviews or extra artifacts. Hashing requires the user's explicit request for publication, deduplication, cache-hit decisions or known-digest rejection and actual use by that operation. User prohibitions take precedence; ask before any scope expansion.

This repository integration has not independently verified actual ZCode UI concurrency, instruction injection or model selection for the current version; behavior depends on the runtime.
