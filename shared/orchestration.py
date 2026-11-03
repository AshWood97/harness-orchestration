"""Small, host-driven state store for cross-application orchestration.

This module records intent and observations; it does not control desktop apps.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

STATUSES = frozenset({"completed", "partial", "blocked", "failed", "cancelled"})
BUDGETS = ("external_sessions", "model_calls", "internal_agents", "writers", "ui_inputs")


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _now():
    return datetime.now(timezone.utc).isoformat()


class CoordinationError(ValueError):
    """An action would violate the current task or resource state."""


class Coordinator:
    """A durable store. The caller remains responsible for all desktop actions.

    Supply a database path outside the source tree. Methods that change task state
    require the token returned by ``claim_control``. A new claim fences old hosts,
    but never implies that their previously dispatched executors have stopped.
    """

    def __init__(self, database):
        self.database = os.fspath(database)
        with self._connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY, budget TEXT NOT NULL,
                    retry_limit INTEGER NOT NULL, deadline TEXT,
                    controller TEXT, generation INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(run_id),
                    objective TEXT NOT NULL, verification_owner TEXT NOT NULL,
                    provider TEXT NOT NULL, entrypoint TEXT NOT NULL,
                    plan_revision TEXT NOT NULL, current_attempt INTEGER NOT NULL DEFAULT 0,
                    state TEXT NOT NULL DEFAULT 'pending', spec TEXT NOT NULL,
                    delivery_revision TEXT, interface_revision TEXT, result TEXT,
                    accepted_revision TEXT
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    task_id TEXT NOT NULL REFERENCES tasks(task_id), attempt INTEGER NOT NULL,
                    plan_revision TEXT NOT NULL, state TEXT NOT NULL, status TEXT,
                    reservation TEXT NOT NULL, resources TEXT NOT NULL,
                    native_session TEXT, stopped INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(task_id, attempt)
                );
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL, attempt INTEGER NOT NULL,
                    source TEXT NOT NULL, event_id TEXT, event_type TEXT NOT NULL,
                    observed_at TEXT NOT NULL, payload TEXT NOT NULL,
                    FOREIGN KEY(task_id, attempt) REFERENCES attempts(task_id, attempt),
                    UNIQUE(task_id, attempt, source, event_id)
                );
                CREATE TABLE IF NOT EXISTS ui_locks (
                    platform TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(run_id),
                    controller TEXT NOT NULL, generation INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS session_binding
                    ON attempts(native_session) WHERE native_session IS NOT NULL;
            """)

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(self.database, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @contextmanager
    def _write(self):
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            yield db

    @staticmethod
    def _row(db, table, key, value):
        row = db.execute(f"SELECT * FROM {table} WHERE {key} = ?", (value,)).fetchone()
        if row is None:
            raise CoordinationError(f"Unknown {table}: {value}")
        return row

    @staticmethod
    def _authorize(db, run_id, control):
        run = Coordinator._row(db, "runs", "run_id", run_id)
        if not control or tuple(control) != (run["controller"], run["generation"]):
            raise CoordinationError("Controller is not current")
        return run

    @staticmethod
    def _task(db, task_id, control):
        task = Coordinator._row(db, "tasks", "task_id", task_id)
        Coordinator._authorize(db, task["run_id"], control)
        return task

    @staticmethod
    def _attempt(db, task_id, attempt):
        row = db.execute("SELECT * FROM attempts WHERE task_id=? AND attempt=?",
                         (task_id, attempt)).fetchone()
        if row is None:
            raise CoordinationError("Unknown attempt")
        return row

    def create_run(self, run_id, budget, retry_limit=0, deadline=None):
        if not run_id or set(budget) != set(BUDGETS):
            raise CoordinationError("Provide a run ID and all budget dimensions")
        if any(type(value) is not int or value < 0 for value in budget.values()):
            raise CoordinationError("Budgets must be nonnegative integers")
        if type(retry_limit) is not int or retry_limit < 0:
            raise CoordinationError("Retry limit must be a nonnegative integer")
        if deadline is not None:
            parsed = datetime.fromisoformat(deadline)
            if parsed.tzinfo is None:
                raise CoordinationError("Deadline must include its timezone")
        with self._write() as db:
            db.execute("INSERT INTO runs(run_id,budget,retry_limit,deadline) VALUES(?,?,?,?)",
                       (run_id, _json(budget), retry_limit, deadline))

    def claim_control(self, run_id, controller):
        """Explicitly transfer control; existing resource reservations remain held."""
        if not controller:
            raise CoordinationError("Controller ID is required")
        with self._write() as db:
            run = self._row(db, "runs", "run_id", run_id)
            generation = run["generation"] + 1
            db.execute("UPDATE runs SET controller=?, generation=? WHERE run_id=?",
                       (controller, generation, run_id))
            return (controller, generation)

    def acquire_ui(self, run_id, control, platform):
        """Reserve the shared desktop input across runs using this database."""
        if not platform:
            raise CoordinationError("UI platform is required")
        with self._write() as db:
            run = self._authorize(db, run_id, control)
            count = db.execute("SELECT COUNT(*) FROM ui_locks WHERE run_id=?", (run_id,)).fetchone()[0]
            if count >= json.loads(run["budget"])["ui_inputs"]:
                raise CoordinationError("UI input budget exceeded")
            if db.execute("SELECT 1 FROM ui_locks LIMIT 1").fetchone():
                raise CoordinationError("UI input is already reserved")
            db.execute("INSERT INTO ui_locks(platform,run_id,controller,generation) VALUES(?,?,?,?)",
                       (platform, run_id, control[0], control[1]))

    def release_ui(self, run_id, control, platform, *, previous_controller_stopped=False):
        """Release after input stops; handoff requires explicit confirmation."""
        with self._write() as db:
            self._authorize(db, run_id, control)
            lock = db.execute("SELECT * FROM ui_locks WHERE platform=? AND run_id=?", (platform, run_id)).fetchone()
            if lock is None:
                raise CoordinationError("UI input is not held by this run")
            if (lock["controller"], lock["generation"]) != tuple(control) and previous_controller_stopped is not True:
                raise CoordinationError("Confirm the previous controller has stopped input")
            db.execute("DELETE FROM ui_locks WHERE platform=? AND run_id=?", (platform, run_id))

    @staticmethod
    def _validate_desktop_budget(provider, entrypoint, budget):
        if entrypoint == "desktop" or provider in ("zcode_desktop", "qoder_cn_desktop"):
            if budget["external_sessions"] < 1:
                raise CoordinationError("Desktop attempts require a session reservation")
            if budget["model_calls"] < budget["external_sessions"] + budget["internal_agents"]:
                raise CoordinationError("Desktop model-call reservation must cover sessions and internal agents")

    def create_task(self, run_id, control, *, task_id, objective, plan_revision,
                    verification_owner, effective_constraints, provider, entrypoint, owned_paths=(),
                    shared_resources=(), child_budget=None, dependencies=()):
        if not all((task_id, objective, plan_revision, verification_owner, provider, entrypoint)):
            raise CoordinationError("Task identity, objective, plan and verifier are required")
        budget = dict(child_budget or {})
        if set(budget) - set(BUDGETS) or any(type(v) is not int or v < 0 for v in budget.values()):
            raise CoordinationError("Invalid child budget")
        budget = {name: budget.get(name, 0) for name in BUDGETS}
        if owned_paths and budget["writers"] < 1:
            raise CoordinationError("Owned write paths require a writer reservation")
        self._validate_desktop_budget(provider, entrypoint, budget)
        paths = []
        for path in owned_paths:
            if not os.path.isabs(path):
                raise CoordinationError("Owned paths must be absolute")
            paths.append(os.path.normpath(path))
        for dep in dependencies:
            if set(dep) != {"task_id", "interface_revision", "delivery_revision"}:
                raise CoordinationError("Dependency needs task and both input revisions")
            if not all(dep.values()) or dep["task_id"] == task_id:
                raise CoordinationError("Invalid dependency")
        spec = dict(effective_constraints=effective_constraints, owned_paths=paths,
                    shared_resources=list(shared_resources), child_budget=budget,
                    dependencies=list(dependencies))
        with self._write() as db:
            run = self._authorize(db, run_id, control)
            if budget["model_calls"] > json.loads(run["budget"])["model_calls"]:
                raise CoordinationError("Model-call reservation exceeds run budget")
            db.execute("INSERT INTO tasks(task_id,run_id,objective,verification_owner,provider,entrypoint,plan_revision,spec) VALUES(?,?,?,?,?,?,?,?)",
                       (task_id, run_id, objective, verification_owner, provider, entrypoint, plan_revision, _json(spec)))

    @staticmethod
    def _dependencies_ready(db, task):
        for dep in json.loads(task["spec"])["dependencies"]:
            producer = db.execute("SELECT * FROM tasks WHERE task_id=? AND run_id=?",
                                  (dep["task_id"], task["run_id"])).fetchone()
            if (producer is None or producer["state"] != "accepted" or
                    producer["accepted_revision"] != dep["delivery_revision"] or
                    producer["interface_revision"] != dep["interface_revision"]):
                return False
        return True

    @staticmethod
    def _resources_overlap(left, right):
        if set(left["shared_resources"]) & set(right["shared_resources"]):
            return True
        for a in left["owned_paths"]:
            for b in right["owned_paths"]:
                if os.path.commonpath((a, b)) in (a, b):
                    return True
        return False

    def prepare_dispatch(self, task_id, control):
        """Reserve resources and persist intent *before* a host sends a task."""
        with self._write() as db:
            task = self._task(db, task_id, control)
            run = self._authorize(db, task["run_id"], control)
            if run["deadline"] and datetime.now(timezone.utc) >= datetime.fromisoformat(run["deadline"]):
                raise CoordinationError("Run deadline reached")
            if task["state"] == "accepted":
                raise CoordinationError("Accepted task must first be revised")
            if not self._dependencies_ready(db, task):
                raise CoordinationError("Dependencies are not accepted at required revisions")
            active = db.execute("SELECT a.*, t.run_id FROM attempts a JOIN tasks t ON t.task_id=a.task_id WHERE a.stopped=0").fetchall()
            if any(a["task_id"] == task_id for a in active):
                raise CoordinationError("Prior execution is not confirmed stopped")
            if task["current_attempt"]:
                retries = db.execute("SELECT COUNT(*) FROM attempts a JOIN tasks t ON t.task_id=a.task_id WHERE t.run_id=? AND a.attempt>1", (task["run_id"],)).fetchone()[0]
                if retries >= run["retry_limit"]:
                    raise CoordinationError("Retry budget exhausted")
            spec = json.loads(task["spec"])
            self._validate_desktop_budget(task["provider"], task["entrypoint"], spec["child_budget"])
            if any(self._resources_overlap(spec, json.loads(a["resources"])) for a in active):
                raise CoordinationError("Resource already reserved")
            caps = json.loads(run["budget"])
            used = {k: sum(json.loads(a["reservation"])[k] for a in active if a["run_id"] == task["run_id"]) for k in BUDGETS}
            if (any(used[k] + spec["child_budget"][k] > caps[k] for k in BUDGETS if k != "ui_inputs") or
                    spec["child_budget"]["ui_inputs"] > caps["ui_inputs"]):
                raise CoordinationError("Run budget exceeded")
            attempt = task["current_attempt"] + 1
            resources = {"owned_paths": spec["owned_paths"], "shared_resources": spec["shared_resources"]}
            db.execute("INSERT INTO attempts(task_id,attempt,plan_revision,state,reservation,resources) VALUES(?,?,?,?,?,?)",
                       (task_id, attempt, task["plan_revision"], "dispatch_intent", _json(spec["child_budget"]), _json(resources)))
            db.execute("UPDATE tasks SET current_attempt=?, state='dispatch_intent', result=NULL, delivery_revision=NULL, interface_revision=NULL, accepted_revision=NULL WHERE task_id=?", (attempt, task_id))
            return {"task_id": task_id, "attempt": attempt, "plan_revision": task["plan_revision"], "objective": task["objective"], "verification_owner": task["verification_owner"], "provider": task["provider"], "entrypoint": task["entrypoint"], **spec}

    def mark_submitted(self, task_id, attempt, control, native_session=None):
        with self._write() as db:
            task = self._task(db, task_id, control)
            row = self._attempt(db, task_id, attempt)
            if attempt != task["current_attempt"] or row["state"] not in ("dispatch_intent", "unknown"):
                raise CoordinationError("Attempt cannot be submitted from its current state")
            if native_session and db.execute("SELECT 1 FROM attempts a JOIN tasks t ON t.task_id=a.task_id WHERE a.native_session=? AND t.provider=? AND a.task_id<>?", (native_session, task["provider"], task_id)).fetchone():
                raise CoordinationError("Native session is already bound to another task")
            db.execute("UPDATE attempts SET state='submitted',native_session=? WHERE task_id=? AND attempt=?", (native_session, task_id, attempt))
            if row["plan_revision"] == task["plan_revision"]:
                db.execute("UPDATE tasks SET state='submitted' WHERE task_id=?", (task_id,))

    def mark_active(self, task_id, attempt, control, state):
        if state not in ("running", "waiting_input"):
            raise CoordinationError("Invalid active state")
        with self._write() as db:
            task = self._task(db, task_id, control)
            row = self._attempt(db, task_id, attempt)
            if attempt != task["current_attempt"] or row["stopped"] or row["state"] not in ("submitted", "running", "waiting_input", "unknown"):
                raise CoordinationError("Attempt is not active")
            db.execute("UPDATE attempts SET state=? WHERE task_id=? AND attempt=?", (state, task_id, attempt))
            if row["plan_revision"] == task["plan_revision"]:
                db.execute("UPDATE tasks SET state=? WHERE task_id=?", (state, task_id))

    def mark_unknown(self, task_id, attempt, control):
        with self._write() as db:
            task = self._task(db, task_id, control)
            row = self._attempt(db, task_id, attempt)
            if attempt != task["current_attempt"] or row["stopped"] or row["state"] not in ("dispatch_intent", "submitted", "running", "waiting_input", "unknown", "cancel_pending"):
                raise CoordinationError("Attempt is no longer active")
            state = "cancel_pending" if row["state"] == "cancel_pending" else "unknown"
            db.execute("UPDATE attempts SET state=? WHERE task_id=? AND attempt=?", (state, task_id, attempt))
            if row["plan_revision"] == task["plan_revision"]:
                db.execute("UPDATE tasks SET state=? WHERE task_id=?", (state, task_id))

    def request_cancel(self, task_id, attempt, control):
        """Record a request only; it does not send a cancellation to the app."""
        with self._write() as db:
            task = self._task(db, task_id, control)
            row = self._attempt(db, task_id, attempt)
            if attempt != task["current_attempt"] or row["stopped"]:
                raise CoordinationError("Attempt is no longer active")
            db.execute("UPDATE attempts SET state='cancel_pending' WHERE task_id=? AND attempt=?", (task_id, attempt))
            if row["plan_revision"] == task["plan_revision"]:
                db.execute("UPDATE tasks SET state='cancel_pending' WHERE task_id=?", (task_id,))

    def confirm_stopped(self, task_id, attempt, control):
        """Release reservation only after the caller confirms the executor stopped."""
        with self._write() as db:
            task = self._task(db, task_id, control)
            row = self._attempt(db, task_id, attempt)
            if row["stopped"]:
                return
            db.execute("UPDATE attempts SET stopped=1 WHERE task_id=? AND attempt=?", (task_id, attempt))
            if attempt == task["current_attempt"] and row["state"] == "cancel_pending":
                db.execute("UPDATE attempts SET state='cancelled',status='cancelled' WHERE task_id=? AND attempt=?", (task_id, attempt))
                if row["plan_revision"] == task["plan_revision"]:
                    db.execute("UPDATE tasks SET state='cancelled' WHERE task_id=?", (task_id,))
            elif attempt == task["current_attempt"] and row["state"] in ("unknown", "submitted", "running", "waiting_input", "dispatch_intent"):
                db.execute("UPDATE attempts SET state='stopped' WHERE task_id=? AND attempt=?", (task_id, attempt))
                if row["plan_revision"] == task["plan_revision"]:
                    db.execute("UPDATE tasks SET state='stopped' WHERE task_id=?", (task_id,))

    def record_event(self, task_id, attempt, source, event_id, event_type, payload):
        """Record an observation; it never changes task state or implies success.

        A stable source event_id makes retries idempotent. Pass None if the source
        has no unique ID; such observations cannot safely be deduplicated.
        """
        with self._write() as db:
            self._attempt(db, task_id, attempt)
            cur = db.execute("INSERT OR IGNORE INTO events(task_id,attempt,source,event_id,event_type,observed_at,payload) VALUES(?,?,?,?,?,?,?)",
                             (task_id, attempt, source, event_id, event_type, _now(), _json(payload)))
            return cur.rowcount == 1

    def record_result(self, task_id, attempt, control, *, status, summary,
                      delivery_revision=None, interface_revision=None, **result):
        if status not in STATUSES:
            raise CoordinationError("Invalid result status")
        if status == "completed" and (not delivery_revision or not interface_revision):
            raise CoordinationError("Completed delivery needs delivery and interface revisions")
        with self._write() as db:
            task = self._task(db, task_id, control)
            row = self._attempt(db, task_id, attempt)
            if attempt != task["current_attempt"] or row["plan_revision"] != task["plan_revision"]:
                raise CoordinationError("Stale attempt cannot update current delivery")
            if row["state"] not in ("dispatch_intent", "submitted", "running", "waiting_input", "unknown", "stopped"):
                raise CoordinationError("Attempt is not awaiting a result")
            if not self._dependencies_ready(db, task):
                raise CoordinationError("Input delivery is no longer valid")
            state = "delivered" if status == "completed" else status
            payload = {"status": status, "summary": summary, **result}
            db.execute("UPDATE attempts SET state=?,status=? WHERE task_id=? AND attempt=?", (state, status, task_id, attempt))
            db.execute("UPDATE tasks SET state=?,delivery_revision=?,interface_revision=?,result=?,accepted_revision=NULL WHERE task_id=?", (state, delivery_revision, interface_revision, _json(payload), task_id))

    def accept(self, task_id, attempt, control, *, delivery_revision, verification_owner):
        with self._write() as db:
            task = self._task(db, task_id, control)
            row = self._attempt(db, task_id, attempt)
            if (attempt != task["current_attempt"] or task["state"] != "delivered" or
                    task["delivery_revision"] != delivery_revision or
                    task["verification_owner"] != verification_owner or not row["stopped"] or
                    not self._dependencies_ready(db, task)):
                raise CoordinationError("Delivery is not eligible for this acceptance")
            db.execute("UPDATE tasks SET state='accepted',accepted_revision=? WHERE task_id=?", (delivery_revision, task_id))

    def reject(self, task_id, attempt, control, *, delivery_revision, verification_owner):
        with self._write() as db:
            task = self._task(db, task_id, control)
            row = self._attempt(db, task_id, attempt)
            if (attempt != task["current_attempt"] or task["state"] != "delivered" or
                    task["delivery_revision"] != delivery_revision or
                    task["verification_owner"] != verification_owner or not row["stopped"]):
                raise CoordinationError("Delivery is not eligible for this rejection")
            db.execute("UPDATE tasks SET state='rework' WHERE task_id=?", (task_id,))

    def revise_plan(self, task_id, control, plan_revision, dependencies=None):
        """Invalidate this delivery and only its dependent deliveries transitively."""
        with self._write() as db:
            task = self._task(db, task_id, control)
            if not plan_revision or plan_revision == task["plan_revision"]:
                raise CoordinationError("A distinct plan revision is required")
            spec = json.loads(task["spec"])
            if dependencies is not None:
                for dep in dependencies:
                    if set(dep) != {"task_id", "interface_revision", "delivery_revision"} or not all(dep.values()) or dep["task_id"] == task_id:
                        raise CoordinationError("Invalid dependency")
                spec["dependencies"] = list(dependencies)
            db.execute("UPDATE tasks SET plan_revision=?,spec=?,state='stale',accepted_revision=NULL WHERE task_id=?", (plan_revision, _json(spec), task_id))
            affected = [task_id]
            all_tasks = db.execute("SELECT * FROM tasks WHERE run_id=?", (task["run_id"],)).fetchall()
            seen = {task_id}
            while affected:
                changed = affected.pop()
                for item in all_tasks:
                    if item["task_id"] not in seen and any(d["task_id"] == changed for d in json.loads(item["spec"])["dependencies"]):
                        seen.add(item["task_id"])
                        affected.append(item["task_id"])
                        db.execute("UPDATE tasks SET state='stale',accepted_revision=NULL WHERE task_id=?", (item["task_id"],))

    def task(self, task_id):
        with self._connection() as db:
            row = dict(self._row(db, "tasks", "task_id", task_id))
            row["dependencies_ready"] = self._dependencies_ready(db, row)
            row["spec"] = json.loads(row["spec"])
            row["result"] = json.loads(row["result"]) if row["result"] else None
            return row

    def events(self, task_id, after_sequence=0):
        with self._connection() as db:
            rows = db.execute("SELECT * FROM events WHERE task_id=? AND sequence>? ORDER BY sequence", (task_id, after_sequence)).fetchall()
            return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]

    def reconcile(self, task_id):
        """Return stored facts; the host must verify the actual desktop session."""
        with self._connection() as db:
            task = self._row(db, "tasks", "task_id", task_id)
            run = dict(self._row(db, "runs", "run_id", task["run_id"]))
            run["budget"] = json.loads(run["budget"])
            rows = db.execute("SELECT * FROM attempts WHERE task_id=? ORDER BY attempt", (task_id,)).fetchall()
            attempts = [{**dict(row), "reservation": json.loads(row["reservation"]),
                         "resources": json.loads(row["resources"])} for row in rows]
            locks = [dict(row) for row in db.execute("SELECT * FROM ui_locks WHERE run_id=?", (task["run_id"],))]
        return {"run": run, "task": self.task(task_id), "attempts": attempts,
                "ui_locks": locks, "events": self.events(task_id)}

    def task_for_session(self, native_session, provider):
        with self._connection() as db:
            row = db.execute("SELECT a.task_id,a.attempt FROM attempts a JOIN tasks t ON t.task_id=a.task_id WHERE a.native_session=? AND t.provider=? AND a.stopped=0 ORDER BY a.attempt DESC LIMIT 1", (native_session, provider)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def adapter_action(action):
        """Desktop actions require an actual host; no hidden fallback is attempted."""
        if action not in {"discover", "dispatch", "observe", "send_update", "cancel", "collect", "reconcile"}:
            raise CoordinationError("Unknown adapter action")
        return {"action": action, "status": "unsupported", "reason": "No desktop host is attached"}
