# 跨应用任务交接与最小协调器

本协议供 Codex 通过桌面操作协同 Qoder CN、ZCode 时使用。`shared.orchestration.Coordinator` 是可选的 Python 状态库；普通 Native 任务继续使用宿主会话，不需要数据库。库不创建或操纵桌面会话、不自动执行任务或唤醒 Codex，也不安装产品 CLI。`adapter_action()` 对没有附着桌面宿主的动作返回 `unsupported`。桌面发送、取消和实际验收仍由宿主完成并如实登记。

## 任务与结果

一个 `task_id` 在返修和重试时保持不变，每次派发产生独立的 `attempt`。任务提供 `plan_revision`、目标、`verification_owner`、平台与入口、`effective_constraints`、绝对 `owned_paths`、`shared_resources`、`child_budget` 和依赖生产者的接口与交付版本。宿主应在约束中携带适用用户/项目规则、允许操作和完成标准。只使用实际存在的原生会话标识。

执行结果的 `status` 为 `completed`、`partial`、`blocked`、`failed` 或 `cancelled`；`completed` 仅表示已交付。只有指定验收人针对确切 `delivery_revision` 调用 `accept` 才是验收通过，且必须确认执行者已停止。需要裁定具体发现时，角色可在结果载荷中附加 `verdict`。可用提交、构建或可定位的差异标识交付，不要求另算摘要。

宿主处理任务的一般顺序：

1. 在仓库外的路径创建数据库和 run；预算分别规定外部会话、模型调用预留、内部代理、写入者、UI 输入，另设累计重试上限和可选时限。桌面任务必须显式预留 `model_calls`，其值至少为 `external_sessions + internal_agents`；每个任务及同一 run 的活动预留总和不得超过 run 的模型调用预算。无法观察的内部调用按分配的上限预留，配额是协作约定，不是强制平台停止的硬隔离。
2. `claim_control` 获取控制代次，`create_task` 登记任务。控制权交接时重新 claim，旧代次不能再更改任务；旧执行者与 UI 锁并不会因此停止或释放。新的控制者须核实旧控制者确已停止输入，再显式调用 `release_ui(..., previous_controller_stopped=True)` 释放遗留锁。
3. `prepare_dispatch` 在发送前登记意图并预留资源。需要输入桌面时先 `acquire_ui`，实际操作完成后 `release_ui`；同一状态库内 Qoder、ZCode 和其他 run 共用一个桌面输入锁。确认提交或原生会话后调用 `mark_submitted`；发送结果不明调用 `mark_unknown` 并检查同一桌面会话，不能再次盲发。
4. 用 `mark_active` 记录真实运行或等待输入，用 `record_event` 保存可关联的观察。使用原生事件 ID 的重复事件会去重；没有原生 ID 的观察不假装可精确去重。事件本身不会改变任务状态或证明验收。
5. 提交取消时先 `request_cancel` 并通过原通道发出，等待确认；期间状态不明仍保留取消待确认，迟到完成结果不能通过验收。仅在真实执行者停止后调用 `confirm_stopped` 释放资源；断联、待确认和新控制代次均不代表停止。无冲突的其他任务可继续。
6. 执行者交付后用 `record_result` 记录，然后由验收人 `accept` 或 `reject`。`reconcile` 返回登记的任务、attempt、原生会话和观察，恢复时仍需对照真实会话和产物。`revise_plan` 标记当前任务及依赖其交付的任务过期；新 attempt 前检查上游交付及依赖版本，旧 attempt 的结果不得推进当前任务。

每个绝对路径及嵌套路径、命名的共享资源（如锁文件、端口、数据库、生成目录）只能由一个活动 attempt 持有，冲突跨本数据库各 run 检查。独立资源可并行。worktree、这些记录和 UI 锁都不是进程级强制隔离；未确认旧执行者停止时，不可把同一路径交给新写入者。跨工作区共享的外部数据还须使用同一个 `shared_resources` 名称。

## 从任意工作目录调用

`shared` 位于本仓库，已安装的 Codex skill 不自带这份库。宿主在需要跨应用协调的任务中，须显式把**包含 `shared/` 的本仓库绝对路径**加入 Python 搜索路径并调用下述 API；仅安装 skill、启用 hook 或打开桌面不会自动启动协调器。只要使用同一个有效的仓库绝对路径，调用时的当前工作目录可以是任何位置。仓库移动或删除后，宿主需更新源码路径；不要以为已安装的 skill 内还存在该库。

SQLite 状态路径也须为绝对路径，位于仓库外且其父目录已存在；任务续接与 hook 使用同一个状态文件。文件由调用者保存和管理，只登记任务所需的最少内容；不要写入凭据、完整对话或完整源文件。以下示例将 `REPO` 和 `STATE` 替换为本机真实路径；示例里的任务 ID、目标、路径、约束和预算也应按实际任务替换。

```python
import sys
from pathlib import Path

REPO = Path('/absolute/path/to/harness-orchestration')  # 本仓库的实际绝对路径
STATE = Path('/absolute/path/outside/repo/orchestration.sqlite')
sys.path.insert(0, str(REPO))
from shared.orchestration import Coordinator

c = Coordinator(STATE)
run_id, task_id, verifier = 'run-1', 'task-1', 'codex-host'
c.create_run(run_id, {
    'external_sessions': 2, 'model_calls': 4, 'internal_agents': 2,
    'writers': 2, 'ui_inputs': 1,
}, retry_limit=2)
control = c.claim_control(run_id, verifier)
c.create_task(
    run_id, control, task_id=task_id, objective='完成约定范围',
    provider='zcode_desktop', entrypoint='desktop', plan_revision='plan-1',
    verification_owner=verifier,
    effective_constraints={'allowed_actions': ['edit'], 'completion_conditions': ['完成指定修改']},
    owned_paths=['/absolute/worktree/file.py'], shared_resources=[],
    child_budget={'external_sessions': 1, 'writers': 1, 'internal_agents': 1, 'model_calls': 2},
)
packet = c.prepare_dispatch(task_id, control)
attempt = packet['attempt']
c.acquire_ui(run_id, control, 'zcode_desktop')
```

`packet` 是宿主通过实际桌面发送的任务书；上面的代码没有发送消息。实际发送、结果核验和停止确认必须由宿主完成，以下函数只登记宿主已经观察到的事实。函数和上例运行在同一 Python 上下文中；在不同进程继续时重新加载库及数据库、`claim_control`，并通过 `c.reconcile(task_id)` 取得实际 attempt、会话、锁和已记录结果，不能重复创建已有 run 或重新派发未知任务。

```python
def submission_confirmed(native_session):
    # 真实发送已确认；native_session 取平台实际 ID，未提供时传 None。
    c.mark_submitted(task_id, attempt, control, native_session=native_session)
    c.release_ui(run_id, control, 'zcode_desktop')


def submission_unknown_after_input_stops():
    # 发送结果无法确定时检查原会话，不重复发送；仅在输入确已结束时释放 UI。
    c.mark_unknown(task_id, attempt, control)
    c.release_ui(run_id, control, 'zcode_desktop')


def delivery_observed(summary, changed_paths, checks, delivery_revision, interface_revision):
    # 所有参数来自真实交付；版本可使用实际提交、构建或可定位的差异版本。
    c.record_result(
        task_id, attempt, control, status='completed', summary=summary,
        changed_paths=changed_paths, checks=checks,
        delivery_revision=delivery_revision, interface_revision=interface_revision,
    )


def executor_confirmed_stopped():
    # 真实执行者已停止后才可调用，释放该 attempt 的写入及预算预留。
    c.confirm_stopped(task_id, attempt, control)


def delivery_accepted(delivery_revision):
    # 指定验收人核验同一交付版本后调用；此前必须确认执行者已停止。
    c.accept(task_id, attempt, control, delivery_revision=delivery_revision,
             verification_owner=verifier)
```

完成一次真实执行时，依次传入实际会话 ID 调用 `submission_confirmed`，传入实际摘要、修改路径、检查结果及两种版本调用 `delivery_observed`，确认执行停止后调用 `executor_confirmed_stopped`，由指定验收人核验后用相同交付版本调用 `delivery_accepted`。若执行只部分完成、阻塞或失败，以相应 `status` 调用 `record_result`，不调用 `accept`。取消已请求时，先等待真实停止，再调用 `confirm_stopped` 登记取消并释放预留；发送或停止不明时先核对原会话。`mark_submitted` 不发送消息；`request_cancel` 不取消进程。使用 Qoder CN 时，`provider` 和 UI 平台均填 `qoder_cn_desktop`，并继续使用现有可见桌面入口。

## 可选 ZCode 用户级 Hook

`adapters/zcode_desktop/hook.py` 可接收 ZCode 的一行 JSON 事件，将已绑定、活动的 `zcode_desktop` 原生 session 的最少元信息追加到数据库；它不保存提示词、工具参数、转录或最后一条回复。`Stop` 只是一条观察，不更新任务状态。未绑定 session、回调缺失或无法读写数据库都不代表成功或失败。重用 session 的旧回调不能按 attempt 精确区分时，仍只作观察；仍需核对原生会话。若没有真实 session ID，此回报不可用。

按需在 ZCode 的 **Settings → Hooks → user** 中添加 process 类型 hook，将 Python 可执行文件作为 command，args 依次填写本仓库中 `adapters/zcode_desktop/hook.py` 的绝对路径和仓库外 SQLite 文件的绝对路径；为需要的事件分别启用。也可按 [ZCode 官方 Hooks 文档](https://www.zcode.network/en/docs/hooks/)合并用户级 `~/.zcode/cli/config.json` 的 `hooks.events`，保留已有配置。不要写入项目级 hooks，也不要自动修改用户设置。配置在新 session 启动时读取；绑定发生前的事件不能回填。若无事件，继续使用桌面会话核对，不依赖 hook 存活或自动唤醒。

页面中的能力与事件名称来自官方文档；具体已安装 ZCode 版本、实际发送/恢复、后台补位以及 hook 加载需单独实机验证。
