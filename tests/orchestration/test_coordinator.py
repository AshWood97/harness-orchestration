import os
import tempfile
import unittest

from adapters.zcode_desktop.hook import observe
from shared.orchestration import BUDGETS, CoordinationError, Coordinator


class CoordinatorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, "state.sqlite")
        self.c = Coordinator(self.db)
        caps = {key: 2 for key in BUDGETS}
        caps["model_calls"] = 3
        self.c.create_run("run", caps, retry_limit=3)
        self.control = self.c.claim_control("run", "host")

    def task(self, task_id, **overrides):
        args = dict(task_id=task_id, objective="deliver", plan_revision="p1",
                    verification_owner="reviewer", effective_constraints={}, provider="zcode_desktop", entrypoint="desktop",
                    owned_paths=[os.path.join(self.tmp.name, task_id)],
                    child_budget={"external_sessions": 1, "writers": 1, "model_calls": 1})
        args.update(overrides)
        self.c.create_task("run", self.control, **args)

    def deliver(self, task_id, attempt, delivery="d1", interface="i1"):
        self.c.record_result(task_id, attempt, self.control, status="completed", summary="done",
                             delivery_revision=delivery, interface_revision=interface)
        self.c.confirm_stopped(task_id, attempt, self.control)
        self.c.accept(task_id, attempt, self.control, delivery_revision=delivery,
                      verification_owner="reviewer")

    def test_unknown_or_cancelled_execution_keeps_resource_until_confirmed_stopped(self):
        path = os.path.join(self.tmp.name, "shared")
        self.task("a", owned_paths=[path])
        self.task("b", owned_paths=[os.path.join(path, "nested")])
        a = self.c.prepare_dispatch("a", self.control)["attempt"]
        self.c.mark_unknown("a", a, self.control)
        with self.assertRaises(CoordinationError):
            self.c.prepare_dispatch("a", self.control)
        with self.assertRaises(CoordinationError):
            self.c.prepare_dispatch("b", self.control)
        self.c.request_cancel("a", a, self.control)
        with self.assertRaises(CoordinationError):
            self.c.prepare_dispatch("b", self.control)
        self.c.confirm_stopped("a", a, self.control)
        self.assertEqual(self.c.task("a")["state"], "cancelled")
        self.assertEqual(self.c.prepare_dispatch("b", self.control)["attempt"], 1)

    def test_result_acceptance_and_dependencies_bind_to_delivery(self):
        self.task("producer")
        self.task("consumer", dependencies=[dict(task_id="producer", interface_revision="i1", delivery_revision="d1")])
        a = self.c.prepare_dispatch("producer", self.control)["attempt"]
        self.c.record_result("producer", a, self.control, status="completed", summary="done", delivery_revision="d1", interface_revision="i1")
        with self.assertRaises(CoordinationError):
            self.c.accept("producer", a, self.control, delivery_revision="d1", verification_owner="reviewer")
        with self.assertRaises(CoordinationError):
            self.c.prepare_dispatch("consumer", self.control)
        self.c.confirm_stopped("producer", a, self.control)
        self.c.accept("producer", a, self.control, delivery_revision="d1", verification_owner="reviewer")
        b = self.c.prepare_dispatch("consumer", self.control)["attempt"]
        self.deliver("consumer", b)
        self.c.revise_plan("producer", self.control, "p2")
        self.assertEqual(self.c.task("consumer")["state"], "stale")
        self.assertFalse(self.c.task("consumer")["dependencies_ready"])
        with self.assertRaises(CoordinationError):
            self.c.record_result("producer", a, self.control, status="completed", summary="old", delivery_revision="d1", interface_revision="i1")

    def test_budget_and_controller_handoff_keep_reservations(self):
        self.task("a", child_budget={"internal_agents": 2, "external_sessions": 1, "writers": 1, "model_calls": 3})
        self.task("b", child_budget={"internal_agents": 1, "external_sessions": 1, "writers": 1, "model_calls": 2})
        a = self.c.prepare_dispatch("a", self.control)["attempt"]
        with self.assertRaises(CoordinationError):
            self.c.prepare_dispatch("b", self.control)
        next_control = self.c.claim_control("run", "replacement")
        with self.assertRaises(CoordinationError):
            self.c.confirm_stopped("a", a, self.control)
        with self.assertRaises(CoordinationError):
            self.c.prepare_dispatch("b", next_control)
        self.c.confirm_stopped("a", a, next_control)
        self.assertEqual(self.c.prepare_dispatch("b", next_control)["attempt"], 1)

    def test_desktop_model_calls_cover_session_and_internal_agents(self):
        with self.assertRaises(CoordinationError):
            self.task("missing", child_budget={"external_sessions": 1, "writers": 1, "internal_agents": 1})
        with self.assertRaises(CoordinationError):
            self.task("under", child_budget={"external_sessions": 1, "writers": 1, "internal_agents": 1, "model_calls": 1})
        self.task("sufficient", child_budget={"external_sessions": 1, "writers": 1, "internal_agents": 1, "model_calls": 2})
        self.assertEqual(self.c.prepare_dispatch("sufficient", self.control)["child_budget"]["model_calls"], 2)

    def test_zero_model_call_run_cannot_dispatch_desktop(self):
        caps = {key: 2 for key in BUDGETS}
        caps["model_calls"] = 0
        self.c.create_run("zero", caps)
        token = self.c.claim_control("zero", "host")
        with self.assertRaises(CoordinationError):
            self.c.create_task("zero", token, task_id="no-capacity", objective="deliver",
                               plan_revision="p1", verification_owner="reviewer", effective_constraints={},
                               provider="qoder_cn_desktop", entrypoint="desktop",
                               child_budget={"external_sessions": 1, "model_calls": 1})

    def test_active_desktop_reservations_obey_total_model_call_budget(self):
        self.task("a", child_budget={"external_sessions": 1, "writers": 1, "internal_agents": 1, "model_calls": 2})
        self.task("b", child_budget={"external_sessions": 1, "writers": 1, "internal_agents": 1, "model_calls": 2})
        self.c.prepare_dispatch("a", self.control)
        with self.assertRaises(CoordinationError):
            self.c.prepare_dispatch("b", self.control)

    def test_ui_control_survives_handoff_until_released(self):
        self.c.acquire_ui("run", self.control, "zcode_desktop")
        next_control = self.c.claim_control("run", "replacement")
        with self.assertRaises(CoordinationError):
            self.c.acquire_ui("run", next_control, "zcode_desktop")
        with self.assertRaises(CoordinationError):
            self.c.release_ui("run", next_control, "zcode_desktop")
        self.c.release_ui("run", next_control, "zcode_desktop", previous_controller_stopped=True)
        self.c.acquire_ui("run", next_control, "zcode_desktop")

    def test_cancel_unknown_then_stopped_rejects_late_completion(self):
        self.task("a")
        attempt = self.c.prepare_dispatch("a", self.control)["attempt"]
        self.c.mark_submitted("a", attempt, self.control)
        self.c.request_cancel("a", attempt, self.control)
        self.c.mark_unknown("a", attempt, self.control)
        self.assertEqual(self.c.task("a")["state"], "cancel_pending")
        with self.assertRaises(CoordinationError):
            self.c.record_result("a", attempt, self.control, status="completed", summary="late",
                                 delivery_revision="d1", interface_revision="i1")
        self.c.confirm_stopped("a", attempt, self.control)
        self.assertEqual(self.c.task("a")["state"], "cancelled")
        self.assertEqual(self.c.reconcile("a")["attempts"][0]["status"], "cancelled")
        with self.assertRaises(CoordinationError):
            self.c.record_result("a", attempt, self.control, status="completed", summary="late",
                                 delivery_revision="d1", interface_revision="i1")
        with self.assertRaises(CoordinationError):
            self.c.accept("a", attempt, self.control, delivery_revision="d1", verification_owner="reviewer")

    def test_ui_input_is_shared_across_platforms_and_runs(self):
        self.c.create_run("other", {key: 2 for key in BUDGETS}, retry_limit=0)
        other_control = self.c.claim_control("other", "other-host")
        self.c.acquire_ui("run", self.control, "zcode_desktop")
        with self.assertRaises(CoordinationError):
            self.c.acquire_ui("other", other_control, "qoder_cn_desktop")
        with self.assertRaises(CoordinationError):
            self.c.release_ui("other", other_control, "zcode_desktop")
        self.c.release_ui("run", self.control, "zcode_desktop")
        self.c.acquire_ui("other", other_control, "qoder_cn_desktop")

    def test_event_dedup_and_hook_stop_never_accepts(self):
        self.task("a")
        a = self.c.prepare_dispatch("a", self.control)["attempt"]
        self.c.mark_submitted("a", a, self.control, native_session="session")
        self.assertTrue(self.c.record_event("a", a, "host", "event-1", "progress", {}))
        self.assertFalse(self.c.record_event("a", a, "host", "event-1", "progress", {}))
        self.assertTrue(observe(self.db, {"session_id": "session", "hook_event_name": "Stop", "last_assistant_message": "private"}))
        events = self.c.events("a")
        self.assertEqual(len(events), 2)
        self.assertNotIn("last_assistant_message", events[-1]["payload"])
        self.assertEqual(self.c.task("a")["state"], "submitted")
        self.assertFalse(observe(self.db, {"session_id": "other", "hook_event_name": "Stop"}))

    def test_same_native_session_can_resume_same_task(self):
        self.task("a")
        first = self.c.prepare_dispatch("a", self.control)["attempt"]
        self.c.mark_submitted("a", first, self.control, native_session="session")
        self.c.record_result("a", first, self.control, status="partial", summary="remaining")
        self.c.confirm_stopped("a", first, self.control)
        second = self.c.prepare_dispatch("a", self.control)["attempt"]
        self.c.mark_submitted("a", second, self.control, native_session="session")
        self.assertEqual(self.c.task_for_session("session", "zcode_desktop"), {"task_id": "a", "attempt": second})


if __name__ == "__main__":
    unittest.main()
