# 操作参考

原生 MCP 工具与脚本使用同一批任务记录。脚本命令中的路径应展开为本技能绝对路径。

## 任务书

把任务书写入工作区 work/ 下的 JSON 文件，然后提交，避免多层 shell 转义：

```json
{
  "task_id": "project-fix-001",
  "workspace": "/absolute/project",
  "objective": "一个明确目标",
  "requirements": ["相关约束", "完成后停止，不递归派发"],
  "allowed_paths": ["src/target.ts"],
  "forbidden_paths": [],
  "acceptance_criteria": ["可观察的预期结果"],
  "test_commands": [],
  "context": "仅包含执行所需的背景"
}
```

默认不包含 model，ZCode 选择当前工作区的新会话默认模型及档位。
只有用户明确指定模型时才运行 `models --workspace /absolute/project`，添加 `model: {"provider_id": "实际目录中的ID", "model_id": "实际模型ID"}`；仅用户指定档位时再加 reasoning_level。不要把目录的 current_model 固定到默认任务。
可选 worktree_path 是已存在的执行目录。timeout_ms 范围 60000–14400000，默认一小时。

```bash
python3 <skill-root>/scripts/zcode.py submit --file /absolute/project/work/task.json
python3 <skill-root>/scripts/zcode.py events project-fix-001 --after 0 --wait-ms 20000
python3 <skill-root>/scripts/zcode.py status project-fix-001
python3 <skill-root>/scripts/zcode.py result project-fix-001
```

events 下一次用返回的 next_seq。单次脚本调用退出后 worker 仍继续；脚本和 MCP 启动时会协调任务状态。使用脚本时持续跟进排队任务，不能假定无人调用时队列也有常驻调度服务。

## 续接与取消

```bash
python3 <skill-root>/scripts/zcode.py continue project-fix-001 --feedback-file /absolute/project/work/feedback.txt --operation-id project-fix-001-revision-1
python3 <skill-root>/scripts/zcode.py cancel project-fix-001
```

同一续接请求重试保留 operation_id；不同反馈用新 ID。响应丢失时先 status/result，避免重复运行。

## 交互请求

把回复写入 JSON：

```json
{
  "task_id": "project-fix-001",
  "request_id": "copy-exact-request-id",
  "decision": "allow",
  "reason": "This file write is within the user's authorized task."
}
```

```bash
python3 <skill-root>/scripts/zcode.py call zcode_interaction_reply --input /absolute/project/work/reply.json
```

decision 可为 allow / deny / accept / decline。AskUserQuestion 的 answers 对象以完整 questions[].question 文本为键，以实际回答为值。不要用 header 或选项标签替代题目文本。

## 通用工具与排错

```bash
python3 <skill-root>/scripts/zcode.py tools
python3 <skill-root>/scripts/zcode.py models --workspace /absolute/project
```

tools 返回运行中的实际输入 schema。call 只开放任务、诊断和目录工具，输入来自 JSON 文件或 `--input -` 的标准输入；不开放持久默认模型设置。MCP 配置也禁用写默认模型的工具，适配层同时拒绝其直接调用。
退出码 0 表示 MCP 调用成功，不表示任务已验收；退出码 2 表示工具或连接错误。失败时按原 task_id 查询，禁止自动换模型重跑。

任务状态：queued、running、waiting_for_master、completed、failed、cancelled。
失败结果以 error_code 为依据。invalid_agent_report 时若文件工作已完成，只要求修复报告；cleanup_failed 时先确认清理状态；额度或认证错误明确汇报，不自动换账号。

路径变动时编辑 runtime-config.json 的非秘密路径；不要改 ZCode 的 provider 文件来迁就桥接。新 MCP 配置尚未进入当前聊天时，脚本入口可直接使用，无须等待工具重新加载。
