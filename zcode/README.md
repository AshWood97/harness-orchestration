# ZCode 角色编排 v1.0.0 / ZCode orchestration

主 Agent 规划、派发并整合结果，按需选择十个自定义角色和两个内置角色。角色默认继承会话模型与思考等级。每个自定义提示词明确职责、输入、方法、结果、停止条件和执行边界；每次任务再限定一个目标与相关上下文。完整工作流见 [AGENTS.md](AGENTS.md)。

最多并发四个子代理，不含主 Agent，并服从实际运行时容量。有四项必要且独立的就绪任务就同时派发，允许同角色多个实例，空位出现后接续任务。独立文件且接口确定的实现可并行；共享写入和未完成依赖保持有序，不为凑满并发制造任务。

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


每个检查问题由一个负责人处理，主 Agent 汇总；交叉检查回答不同的具体功能问题。Review 只读，不设置自动最终审核。先读源码和已有结果，仅对重要且未解决的行为安排最小必要检查。禁止自行增加哈希、安全审查、防御包装、兼容层、未来抽象、重复 Review、额外测试或产物；超范围先询问。

## 安装

使用 Python 3.11+。默认安装无需模型参数：

```sh
# 预览
python zcode/scripts/install.py

# 安装
python zcode/scripts/install.py --apply
```

默认安装到 `~/.zcode`，可用 `--zcode-home` 指定目录。只含旧模型/思考等级字段差异、其余内容与模板完全一致的旧版角色会自动升级为继承。正文、工具等内容有个人修改时仍显示冲突；明确替换时加 `--replace-existing`。安装器不计算前后摘要，不生成备份、收据或日志文件。

`AGENTS.md` 的 `codex-zcode-orchestration:quality` 标记只包围本工作流，更新时替换该区块，标记外的个人规则保留。

如需显式固定十个自定义角色的模型，仍可使用 `--model "your-provider/your-model" --apply`。单独指定模型不会固定思考等级；可额外加 `--thought-level`，其值应由所选模型支持，并且必须同时指定 `--model`。

默认安装不会改动内置 Explore 和 general-purpose 的独立模型选择。需要恢复这两个角色的继承行为时，先预览，再应用：

```sh
python zcode/scripts/install.py --reset-builtin-models
python zcode/scripts/install.py --reset-builtin-models --apply
```

该开关仅清除 `v2/agents-state.json` 中这两个角色的旧版模型、旧版思考等级和新版模型选择覆盖，保留其他角色、插件覆盖、禁用 ID 和其他字段。文件不存在或没有相应覆盖时不写入。所有变更都先检查冲突，逐文件原子写入；中途失败会回滚已写文件，并拒绝覆盖期间发生的并发修改。更新后开始新会话，现有子智能体保留启动时的配置。

## English

Version **1.0.0** provides ten custom roles alongside built-in Explore and general-purpose. The host plans, selects roles, dispatches assignments and consolidates results. Roles inherit the session model and thought level by default. Each custom prompt defines responsibility, inputs, method, result, stopping conditions and execution boundaries; each assignment supplies one narrow objective and relevant context.

Run at most four subagents concurrently, excluding the host and subject to runtime capacity. Dispatch independent ready work together, allow multiple instances of a role, and refill freed slots. Parallel writers need separately owned files and settled interfaces; shared writes and dependencies stay ordered. Do not create filler tasks. Assign one owner per concrete checking question, keep review read-only and use independent checks only for distinct functional questions.

Install with Python 3.11+: run `python zcode/scripts/install.py` to preview, and add `--apply` to install. The default home is `~/.zcode`; select another with `--zcode-home`. Customized existing roles require explicit `--replace-existing`. The optional `--model provider-id/model-id` overrides custom-role inheritance; `--thought-level` requires `--model` and otherwise remains unset. Existing built-in choices are preserved unless `--reset-builtin-models` is explicitly requested. Marked guidance preserves surrounding personal rules. Installation creates no digest, backup receipt or log. Start a new session to load updated prompts.

Inspect source and reuse results before considering an extra test. No unsolicited security audits, defensive wrappers, compatibility layers, future abstractions, duplicate reviews or extra artifacts. Hashing requires the user's explicit request for publication, deduplication, cache-hit decisions or known-digest rejection and actual use by that operation. User prohibitions take precedence; ask before any scope expansion.
