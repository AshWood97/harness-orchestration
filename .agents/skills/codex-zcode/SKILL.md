---
name: codex-zcode
description: 让 Codex 指挥本机 ZCode 执行有明确范围的任务，跟进进度、续接并检查实际产物。用于选择本技能、调用 $codex-zcode，或明确要求“让 ZCode 执行”。讨论、引用或修改 ZCode/本技能，以及普通复杂任务，不因此启用。
---

# Codex ZCode

主 Codex 负责协调、派单、必要决策和最终验收；Sol 或 Astra 制定任务书，ZCode 在独立会话执行，Luna 跟踪并反馈。链路为 Codex → 本地 MCP → ZCode 自带 app-server。本次明确选择 ZCode 时优先走此入口，不同时启动另一套原生编排。受托规划和跟踪代理只执行本技能规定的职责，不再委派。

## 规划与分工

- 默认由 `gpt-6.1-sol` 制定任务书；复杂或高风险任务使用 `gpt-6-astra`。能确认主 Codex 已使用合适模型时由主 Codex 直接规划；不能确认时启动独立规划代理，提供必要上下文和当前限制，主 Codex 审核任务书并派单。不要猜测主模型。规划模型不可用时说明情况，由主 Codex 接手，不假称使用了该模型。
- 派单后启动一个明确指定 `gpt-6-luna` 的跟踪代理；其任务包与事件、交互规则见[操作参考](references/operations.md#luna-跟踪)。主 Codex 负责向用户传达关键进展、处理升级事项和验收。Luna 可在用户明确授权对应操作且调用工具规则允许时处理常规交互；其他情况立即上报主 Codex。
- 若运行环境不支持指定模型或子代理，或 Luna 中途停止，主 Codex 说明并接手跟踪，用原 task_id 和已知游标恢复；先查询状态，不重复提交。子代理不保证在主会话结束后持续运行，也不保证总成本一定更低。

## 调用入口

优先使用已加载的 `codex_zcode` MCP 工具。尚未加载时使用同一后端的脚本：

```bash
python3 <skill-root>/scripts/zcode.py doctor
python3 <skill-root>/scripts/zcode.py submit --file /absolute/project/work/task.json
```

`<skill-root>` 展开为本 SKILL.md 所在绝对目录。未配置时先运行 `scripts/install.py` 查看安装预览，按已授权安装范围使用 `--apply`。任务书、权限回复与完整命令见 [操作参考](references/operations.md)。

## 模型与任务

- 用户未指定 ZCode 的模型或档位时，任务书**省略整个 model 字段**，不读取目录的 current_model 再写回。ZCode 按工作区新会话默认值选择；从实际运行事件报告模型和档位。规划与跟踪代理的模型选择不改变 ZCode 模型。
- 仅用户明确指定模型时读取 `zcode_model_catalog` 匹配 provider/model。只有用户明确指定档位才传 reasoning_level。选择仅作用于任务，不设置桥接或 ZCode 的持久默认模型，不自动换服务商或模型重跑。
- 续接保留原会话模型。明确要求换模型时新建任务并交接必要上下文；不接管用户正在操作的 ZCode 桌面会话。
- 每个任务传必要背景、允许修改路径、禁止事项和验收条件。ZCode 不会获得 Codex 全部对话。将当前 Plan/只读/不测试等限制写入任务 requirements；明确要求 worker 只完成本任务、不再委派。
- 用户明确要求 ZCode 执行时按要求派单；否则简单工作留在 Codex。默认最多两个 worker，同一执行目录串行；并行修改使用独立目录/worktree。worker 工作时，Codex 不同时修改其负责文件。

## 跟进与验收

1. 首次派发或配置错误时运行 doctor。用稳定 task_id 提交任务；跟踪回执及 events，确认实际 session/model/turn 已开始。
2. Luna 用 next_seq 增量读事件，通常每次等待 20 秒；及时汇报启动、重要进展、请求、异常和终态，不虚构进度百分比。脚本结束只关闭 MCP 连接，已启动 worker 独立运行；脚本模式需持续跟进队列，它没有无人值守的常驻调度器。
3. 遇到 interaction_requested，读取完整请求，按用户明确授权和实际工具规则决定回复或上报；preview 不能只凭摘要批准。Luna 上报后主 Codex 负责决策和必要的用户沟通。
4. 终态后读 result，主 Codex 检查真实文件/diff 和必要的最小检查。completed 是执行结果，不代表验收通过。
5. 主 Codex 针对具体缺陷用 continue 续接；同次反馈重试复用 operation_id，跟踪沿用原 task_id。连接超时先查原 task_id，避免重复派单。取消后确认进程与清理状态，再接手相关文件。

## 运行边界

派发、权限回复、进度和续接均通过程序接口完成。**不使用 Codex 电脑控制、截图、鼠标键盘、AppleScript、扫码、Web Remote Control 或界面操作兜底。** 浏览器宿主固定关闭，包中不包含浏览器驱动。协议或图形界面能力不足时报告具体阻塞。

配置在 `${CODEX_HOME:-~/.codex}/codex-zcode/runtime-config.json`，任务在其配置的 state 目录。配置只保存路径和运行选项；密钥由 ZCode 读取，不复制到技能、任务书或日志。旧版任务记录保留原位。

文件范围属于任务约束，不是 OS 沙箱。app-server 属于随 ZCode 版本变化的内部接口；遇到不兼容先定位具体错误，不切换到 Codex CLI 或其他 API。来源、重建方式和验证边界见 [运行时来源](references/runtime.md)。
