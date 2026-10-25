# 运行时来源与维护

本技能使用 [Sandyzzx/codex-zcode-bridge](https://github.com/Sandyzzx/codex-zcode-bridge) 1.2.7 的公开共享核心，具体提交及补丁记录在 runtime/UPSTREAM.json。Windows 环境白名单增加 PSModuleAnalysisCachePath，避免 PowerShell 命令发现丢失现有缓存而超时；其余核心源代码未改动。src/ 下是本项目的宿主适配层。分发时保留核心 Apache-2.0 LICENSE、NOTICE 及依赖许可证。

适配层为独立 CODEX_HOME 配置提供 MCP/worker 入口，清除继承环境里的旧桥接配置，只接受当前安装配置。配置内出现持久模型覆盖或启用浏览器时明确拒绝；持久默认模型写入接口也拒绝操作。每个 worker 再执行相同检查，沿用上游任务、会话、事件和取消机制。

1.2.7 在 Windows 很早取消时可能使用尚未写入的进程身份快照。适配层仅对该明确错误等待最多 5 秒，待同一次任务的 worker 已持久化身份后，重新调用核心取消逻辑。身份核验、进程树清理和失败状态均由核心处理，不按裸 PID 强杀。

浏览器后端没有打包。该方案不需要桌面 App 正在打开，只需要已安装 ZCode 的 app-server 及有效模型配置。观察到的本机版本为 ZCode Desktop 3.16.3.8992、内置 CLI 0.17.0；内部协议不是稳定的官方服务 API。Windows 路径和进程行为由自动化检查覆盖，未做本项目 Windows 实机模型调用验证。

普通用户使用已提交的自包含 runtime，无需 npm 安装。维护者重建：

```bash
# 将上游检出到 runtime/UPSTREAM.json 指定提交，在上游运行 npm ci。
node scripts/build_zcode_runtime.mjs /absolute/path/to/codex-zcode-bridge
```

构建脚本只读取匹配的上游提交，并把共享核心、SDK 和依赖打入两个 Node ESM 入口；Node >=22.18。不打入账号配置、个人路径、任务记录或浏览器后端。

比较参考：[coder-mcp-bridge](https://github.com/Deslord319/coder-mcp-bridge) 的任务控制与资源互斥、[zcode-open-bridge](https://github.com/tizerluo/zcode-open-bridge) 的 MCP/协议兼容、[zcode-acp](https://github.com/william0wang/zcode-acp) 的无界面 app-server 接入。此技能仅维护 Codex 到本机 ZCode 的执行通道。
