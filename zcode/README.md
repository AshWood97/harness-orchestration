# ZCode 角色编排 / ZCode orchestration

默认流程：**充分考虑的计划 → 执行 → 检查 → 有问题修改、没问题放行**。主 Agent 评估任务、从全部角色中选取需要的角色，并保持一份计划；检查由主 Agent 或一个 code-reviewer 完成，不重复。Review 只读，修复只处理实现任务内的具体缺陷。完整边界见 [AGENTS.md](AGENTS.md)。

七个自定义角色默认省略模型和思考等级，继承主会话的选择。两个内置角色沿用 ZCode 的继承机制；已有个人覆盖默认保留：

| 角色 | 使用范围 |
| --- | --- |
| Explore（内置） | 查清当前任务相关源码和调用链 |
| general-purpose（内置） | 在分配路径内实现最小改动 |
| docs-researcher | 解决必要外部 API/版本事实 |
| code-reviewer | 一次针对请求的只读检查 |
| debugger | 诊断当前任务的具体不明缺陷，无自动轮数触发 |
| design-critic | 规划者判断存在重要且未解决的设计取舍时使用 |
| finding-validator | 规划者判断争议发现会影响结果时使用 |
| test-author | 重要行为需要检查且现有用例缺失时，补最小测试 |
| test-verifier | 重要行为无法通过源码和已有结果判断时，做最小针对性测试 |

规划者可按需选择所有角色，不要求用户逐个点名，也不把全部角色依次跑一遍。尽量少做额外测试，先阅读源码和结果，优先复用现有用例；重要问题仍无法判断才做最小测试，确有缺口才写新用例。不默认添加 hash、审核层、日志、证据包或未来抽象。默认一个写入者，最多四个子智能体；用户明确的不测试、只读等限制仍须遵守。只有超出用户任务范围才先征求同意。

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

如需显式固定七个自定义角色的模型，仍可使用 `--model "your-provider/your-model" --apply`。单独指定模型不会固定思考等级；可额外加 `--thought-level`，其值应由所选模型支持，并且必须同时指定 `--model`。

默认安装不会改动内置 Explore 和 general-purpose 的独立模型选择。需要恢复这两个角色的继承行为时，先预览，再应用：

```sh
python zcode/scripts/install.py --reset-builtin-models
python zcode/scripts/install.py --reset-builtin-models --apply
```

该开关仅清除 `v2/agents-state.json` 中这两个角色的旧版模型、旧版思考等级和新版模型选择覆盖，保留其他角色、插件覆盖、禁用 ID 和其他字段。文件不存在或没有相应覆盖时不写入。所有变更都先检查冲突，逐文件原子写入；中途失败会回滚已写文件，并拒绝覆盖期间发生的并发修改。更新后开始新会话，现有子智能体保留启动时的配置。

## English

The host plans the requested work, implements the smallest change and chooses one checking owner. Inspect requirements, the actual result and directly affected callers. Fix concrete in-scope issues in implementation tasks; review-only tasks stay read-only. Deliver as soon as the request is satisfied.

Custom roles inherit the host session's model and thought level by default. Existing built-in choices are preserved. The host planner may select any role for a concrete in-scope need without the user naming it. Minimize extra testing: inspect first, reuse existing results and prefer the smallest existing check; write new cases only for important gaps. Do not run every role, repeat reviews or add routine matrices, hash/evidence layers or extra artifacts. Explicit user prohibitions remain binding; scope expansions require a question before acting.

Run the installer without model arguments to inherit. `--model provider-id/model-id` remains available for an explicit custom-role override; optional `--thought-level` requires `--model` and otherwise stays unset. `--apply` installs; unchanged legacy templates migrate automatically, while customized roles require `--replace-existing`. Marked guidance preserves surrounding personal rules. Installation produces no digest, backup receipt or log.

Use `--reset-builtin-models` to preview clearing only Explore/general-purpose entries from legacy model/thought maps and the current model-selection map in `v2/agents-state.json`; add `--apply` to write. Other state, plugin overrides and disabled IDs are preserved. The default run leaves built-in choices untouched. Writes are atomic and roll back on failure without overwriting concurrent edits. Start a new session after updating.
