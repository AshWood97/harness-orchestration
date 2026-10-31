# ZCode Turbo 2.0 同事安装和使用指南

本包适用于需要在 ZCode 中使用多角色协作的同事。默认安装 **Turbo 2.0**；主智能体按任务需要协调 10 个自定义角色和 ZCode 内置的 `Explore`、`general-purpose`。独立就绪的子任务最多 4 个并发，不含主智能体，且服从当前运行时的实际容量。

## 安装前准备

1. 准备已安装的 ZCode 和 Python 3.11 或更高版本，可在终端运行 `python3 --version` 查看。
2. 从 [GitHub Release](https://github.com/AshWood97/harness-orchestration/releases/tag/zcode-v2.0.0) 下载 `zcode-turbo-2.0.zip` 并解压。解压得到的 `zcode-turbo-2.0` 目录内应包含 `zcode/`；不需要另行下载仓库或复制账号、凭据、工作区。
3. 安装前如有需要保留的个人角色文件，请自行备份 `~/.zcode/agents/`。安装器不会自动备份：显式允许替换冲突时，原角色的正文和工具配置会被所选模板替换。

## 安装 Turbo

以下命令在终端执行。先进入解压后的目录，再预览：

```sh
cd zcode-turbo-2.0
python3 zcode/scripts/install.py
```

预览默认选择 `turbo`，不写入文件。请检查输出的 `changed_files` 和 `conflicting_roles`，确认目标是本机 `~/.zcode/` 下预期的文件。目标目录不同，可加 `--zcode-home <路径>`。

- 如果 `conflicting_roles` 为空，确认后执行：

  ```sh
  python3 zcode/scripts/install.py --apply
  ```

- 如果列出已有角色冲突，先检查并按需备份这些角色。只有确定用 Turbo 模板替换其正文和工具配置时，才执行：

  ```sh
  python3 zcode/scripts/install.py --replace-existing --apply
  ```

安装器会合并 `~/.zcode/AGENTS.md` 中的受管区块，保留区块外的个人规则；默认保留已有角色 Markdown 的 `model` 和 `thoughtLevel` 字段，不改动 ZCode 界面中的模型设置。它不统一指定角色模型，具体模型选择和优先级由 ZCode 决定。**完成后新建一个 ZCode 会话**，让新会话加载更新后的配置。

## 开始使用

在新会话中直接描述目标、范围和限制，无需逐个点名角色。例如先试一个只读任务：

```text
请检查当前项目的【具体功能】：分别定位入口、追踪主要调用链，并列出已有相关测试。
只读分析，不修改文件、不运行测试、不提交；结论附路径和行号。
如任务之间可以独立推进，请按需并行，最后汇总实际发现和未解决问题。
```

Turbo 提供分层分流和四波次协作模板，具体角色、测试与审查按任务实际需要选用；不为填满并发或波次制造任务。共享写入和未确定接口需要有序处理，用户的只读、不测试、禁止委派等要求始终优先。

Turbo 的 10 个自定义角色设置 `injectAgentsMd: false`。主智能体派单时应传递适用的用户要求、项目 `AGENTS.md` 约束、文件归属及完成条件，不要假定项目规则已自动注入子角色。

## 关闭 Turbo，切回 Classic

仍在解压后的 `zcode-turbo-2.0` 目录中，先预览，再按结果应用：

```sh
python3 zcode/scripts/install.py --profile classic
python3 zcode/scripts/install.py --profile classic --apply
```

如预览列出角色冲突，检查并按需备份后，只有确定替换时才添加 `--replace-existing`：

```sh
python3 zcode/scripts/install.py --profile classic --replace-existing --apply
```

Classic 是本包提供的另一套模板，**不是安装前个人配置的自动备份**；如需恢复原来的个人角色，请使用自己安装前保存的文件。切换完成后同样需要新建会话。

## 排查与验证边界

- **提示角色冲突**：先查看 `conflicting_roles`，确认需要替换哪些已有角色；不要直接添加 `--replace-existing` 跳过检查。
- **规则似乎没生效**：确认安装命令已带 `--apply` 且成功完成，并已在 ZCode 中新建会话。可再次运行预览检查剩余变更。
- **没有看到 4 个并发任务**：只有存在多个必要、互不冲突的就绪任务且运行时有容量时才会并发；4 是上限，不是每次必须达到的数量。
- **模型与预期不同**：检查 ZCode 界面的角色模型设置和会话模型；本包不承诺各版本的模型选择优先级相同。

提供本包的原始移交资料报告曾完成模拟安装演练；本仓库集成并未独立验证所有 ZCode 版本的界面并发、规则注入或模型选择，也不保证固定提速比例。
