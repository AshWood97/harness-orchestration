import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/install.py"
SPEC = importlib.util.spec_from_file_location("codex_zcode_install", SCRIPT)
install = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(install)


def write(path, data=b"fixture\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def app_files(root, mac=True):
    resources = root / ("Contents/Resources" if mac else "resources")
    return (write(resources / "glm/zcode.cjs"),
            write(resources / "config/provider/zcode-builtin.json", b'{"private":"do-not-copy"}'))


def personal_home(root):
    write(root / "v2/provider_config.json", b'{"apiKey":"do-not-copy"}')
    return root


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="codex install ")
        self.addCleanup(self.temporary.cleanup)
        self.user = Path(self.temporary.name).resolve()
        self.home = self.user / ".codex"
        self.package = self.user / "source/codex-zcode"
        write(self.package / "runtime/dist/bridge.mjs", b"// bundled runtime\n")
        write(self.package / "scripts/install.py", b"# installer fixture\n")
        write(self.package / "SKILL.md", b"# Codex ZCode\n")
        self.node = write(self.user / "Node With Spaces/node")
        self.app = self.user / "Applications/ZCode.app"
        self.entry, self.builtin = app_files(self.app)
        self.personal = personal_home(self.user / ".zcode")
        self.addCleanup(patch.stopall)
        patch.object(install.Path, "home", return_value=self.user).start()
        patch.dict(os.environ, {"CODEX_HOME": str(self.home)}, clear=True).start()
        self.version = patch.object(install.subprocess, "run", return_value=subprocess.CompletedProcess(
            [str(self.node), "--version"], 0, stdout="v22.18.0\n", stderr="")).start()

    def configure(self, **kwargs):
        options = {"source_root": self.package, "node": self.node, "zcode_app": self.app}
        options.update(kwargs)
        return install.configure(self.home, **options)

    def settings(self):
        return json.loads((self.home / "codex-zcode/runtime-config.json").read_bytes())

    def test_dry_run_creates_nothing_and_only_probes_node_version(self):
        report = self.configure()
        self.assertFalse(report["apply"])
        self.assertFalse(self.home.exists())
        self.assertEqual(len(report["changed_files"]), 5)
        self.version.assert_called_once_with([str(self.node), "--version"], capture_output=True,
                                             text=True, timeout=10, check=False)
        self.assertNotIn("do-not-copy", json.dumps(report))

    def test_install_preserves_unrelated_toml_bytes_and_is_idempotent(self):
        original = (b'\xef\xbb\xbf# My settings\r\nmodel = "personal-model"\r\n'
                    b'description = """\r\n[mcp_servers.codex_zcode]\r\ntext\r\n"""\r\n'
                    b'[mcp_servers.other]\r\ncommand = "keep-exactly" # comment\r\n')
        write(self.home / "config.toml", original)
        self.configure(apply=True)
        toml = (self.home / "config.toml").read_bytes()
        self.assertTrue(toml.startswith(original))
        self.assertIn(b'startup_timeout_sec = 20\r\ntool_timeout_sec = 75', toml)
        self.assertIn(b'disabled_tools = ["zcode_set_default_model", "zcode_clear_default_model"]', toml)
        self.assertNotIn(b"env =", toml)
        settings = self.settings()
        self.assertEqual(settings["ZCODE_BRIDGE_DATA_DIR"], str(self.home / "codex-zcode/state"))
        self.assertEqual(settings["ZCODE_BRIDGE_MAX_CONCURRENT_WORKERS"], "2")
        self.assertEqual(settings["ZCODE_BRIDGE_TIMEOUT_MS"], "3600000")
        self.assertTrue((self.home / "codex-zcode/state").is_dir())
        self.assertEqual((self.home / "skills/codex-zcode/runtime/dist/bridge.mjs").read_bytes(),
                         (self.package / "runtime/dist/bridge.mjs").read_bytes())
        self.assertFalse(list((self.home / "skills/codex-zcode").rglob("provider_config.json")))
        self.assertEqual(self.configure(apply=True)["changed_files"], [])
        self.assertEqual(self.configure(apply=True, source_root=self.home / "skills/codex-zcode")["changed_files"], [])

    def test_custom_codex_home_is_passed_to_mcp(self):
        custom = self.user / "Other Codex Home"
        install.configure(custom, apply=True, source_root=self.package, node=self.node, zcode_app=self.app)
        toml = (custom / "config.toml").read_text()
        self.assertIn("env = { CODEX_HOME = " + json.dumps(str(custom)) + " }", toml)
        self.assertIn("command = " + json.dumps(str(self.node)), toml)
        self.assertIn(json.dumps(str(custom / "skills/codex-zcode/runtime/dist/bridge.mjs")), toml)

    def test_nested_codex_home_keeps_user_discovery_and_agents_retirement(self):
        custom = self.user / "Other Volume/nested/Codex Home"
        fallback = write(self.user / ".local/bin/node")
        legacy = write(self.user / ".agents/skills/zcode-orchestrator/SKILL.md", b"real user skill").parent
        unrelated = write(custom.parent / ".agents/skills/zcode-orchestrator/SKILL.md", b"unrelated").parent
        with patch.object(install.shutil, "which", return_value=None):
            report = install.configure(custom, apply=True, source_root=self.package,
                                       zcode_app=self.app, retire_old_skills=True)
        settings = json.loads((custom / "codex-zcode/runtime-config.json").read_bytes())
        self.assertEqual(settings["ZCODE_HOME"], str(self.personal))
        self.assertEqual(settings["ZCODE_BRIDGE_NODE"], str(fallback))
        self.assertEqual(report["retired_skills"][0]["source"], str(legacy))
        self.assertFalse(legacy.exists())
        self.assertEqual((Path(report["retired_skills"][0]["backup"]) / "SKILL.md").read_bytes(), b"real user skill")
        self.assertEqual((unrelated / "SKILL.md").read_bytes(), b"unrelated")

    def test_replaced_files_have_private_recoverable_backups_only_once(self):
        originals = {self.home / "config.toml": b'# original\nmodel = "mine"\n',
                     self.home / "codex-zcode/runtime-config.json": b'{"extension": "preserve"}\n',
                     self.home / "skills/codex-zcode/SKILL.md": b"old package"}
        for path, data in originals.items():
            write(path, data).chmod(0o644)
        preview = self.configure()
        self.assertEqual(len(preview["backup_files"]), 3)
        self.assertFalse((self.home / "codex-zcode/backups").exists())
        report = self.configure(apply=True)
        self.assertEqual({Path(item["source"]) for item in report["backup_files"]}, set(originals))
        for item in report["backup_files"]:
            source, backup = Path(item["source"]), Path(item["backup"])
            self.assertEqual(backup.read_bytes(), originals[source])
            self.assertEqual(backup.relative_to(self.home / "codex-zcode/backups").parts[1:],
                             ("files",) + source.relative_to(self.home).parts)
            if os.name != "nt":  # Windows chmod does not implement POSIX permission bits.
                self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
        backups = sorted((self.home / "codex-zcode/backups").rglob("*"))
        repeat = self.configure(apply=True)
        self.assertEqual(repeat["changed_files"], [])
        self.assertEqual(repeat["backup_files"], [])
        self.assertEqual(sorted((self.home / "codex-zcode/backups").rglob("*")), backups)

    def test_mac_windows_and_explicit_entry_discovery_with_spaces(self):
        self.assertEqual(install.application_candidates("darwin", self.user, {}),
                         [Path("/Applications/ZCode.app"), self.app])
        with patch.object(install, "application_candidates", return_value=[self.app]):
            self.assertEqual(install.discover_application(platform="darwin", home=self.user, environ={}),
                             (self.entry, self.builtin))
        local = self.user / "Local App Data"
        program_files = self.user / "Program Files"
        windows_root = local / "Programs/ZCode"
        windows_entry, windows_builtin = app_files(windows_root, mac=False)
        env = {"LocalAppData": str(local), "ProgramFiles": str(program_files)}
        self.assertEqual(install.application_candidates("win32", self.user, env),
                         [windows_root, program_files / "ZCode"])
        self.assertEqual(install.discover_application(platform="win32", home=self.user, environ=env),
                         (windows_entry, windows_builtin))
        self.assertEqual(install.discover_application(self.entry), (self.entry, self.builtin))
        self.assertEqual(install.discover_application(windows_entry), (windows_entry, windows_builtin))

    def test_node_fallback_and_minimum_version_use_argv(self):
        fallback = write(self.user / ".local/bin/node")
        with patch.object(install.shutil, "which", return_value=None):
            self.assertEqual(install.discover_node(home=self.user), fallback)
        self.assertEqual(self.version.call_args[0][0], [str(fallback), "--version"])
        self.version.return_value = subprocess.CompletedProcess([], 0, stdout="v22.17.9\n", stderr="private output")
        with self.assertRaisesRegex(ValueError, r"Node.js >=22.18") as error:
            self.configure(apply=True)
        self.assertNotIn("private output", str(error.exception))
        self.assertFalse(self.home.exists())

    def test_desktop_data_base_dir_and_explicit_home_precedence(self):
        base = self.user / "ZCode Data With Spaces"
        moved = personal_home(base / ".zcode")
        write(self.personal / "v2/setting.json", json.dumps({"dataBaseDir": str(base)}).encode())
        self.assertEqual(install.discover_zcode_home(home=self.user)[0], moved)
        self.assertEqual(install.discover_zcode_home(self.personal, home=self.user)[0], self.personal)
        self.configure(apply=True)
        self.assertEqual(self.settings()["ZCODE_HOME"], str(moved))
        self.configure(apply=True, zcode_home=self.personal)
        self.assertEqual(self.settings()["ZCODE_PERSONAL_PROVIDER_CONFIG_FILE"],
                         str(self.personal / "v2/provider_config.json"))

    def test_legacy_reuses_only_readable_known_paths(self):
        old_personal = personal_home(self.user / "Old Data/.zcode")
        old_data = self.user / "Old Tasks"
        log = write(old_data / "preserved.log", b"old logs\n")
        legacy = {"ZCODE_BRIDGE_NODE": str(self.node), "ZCODE_BRIDGE_ZCODE_CJS": str(self.entry),
                  "ZCODE_BUILTIN_PROVIDER_CONFIG_FILE": str(self.builtin),
                  "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE": str(old_personal / "v2/provider_config.json"),
                  "ZCODE_HOME": str(old_personal), "ZCODE_BRIDGE_DATA_DIR": str(old_data),
                  "ZCODE_BRIDGE_DEFAULT_PROVIDER_ID": "stale-provider", "ZCODE_BRIDGE_DEFAULT_MODEL_ID": "stale-model",
                  "ZCODE_BRIDGE_DEFAULT_REASONING_LEVEL": "high", "ZCODE_BRIDGE_MAX_CONCURRENT_WORKERS": "8",
                  "apiKey": "do-not-copy"}
        write(self.home / "codex-zcode-bridge/runtime-config.json", json.dumps(legacy).encode())
        self.configure(apply=True, node=None, zcode_app=None)
        settings = self.settings()
        self.assertEqual(settings["ZCODE_HOME"], str(old_personal))
        self.assertEqual(settings["ZCODE_BRIDGE_MAX_CONCURRENT_WORKERS"], "2")
        self.assertNotIn("apiKey", settings)
        self.assertTrue(all(settings[key] is None for key in install.MODEL_KEYS))
        self.assertEqual(log.read_bytes(), b"old logs\n")
        self.assertEqual(json.loads((self.home / "codex-zcode-bridge/runtime-config.json").read_bytes()), legacy)

    def test_new_settings_keep_custom_paths_unknown_values_and_valid_concurrency(self):
        custom = personal_home(self.user / "Current Data/.zcode")
        current = {"extension": {"keep": True}, "ZCODE_HOME": str(custom),
                   "ZCODE_BRIDGE_MAX_CONCURRENT_WORKERS": "5", "ZCODE_BRIDGE_TIMEOUT_MS": "60000",
                   "ZCODE_BRIDGE_MODE": "yolo", "ZCODE_BRIDGE_BROWSER_USE": "headless",
                   "ZCODE_BRIDGE_DEFAULT_PROVIDER_ID": "stale", "ZCODE_BRIDGE_DEFAULT_MODEL_ID": "stale",
                   "ZCODE_BRIDGE_DEFAULT_REASONING_LEVEL": "max"}
        write(self.home / "codex-zcode/runtime-config.json", json.dumps(current).encode())
        self.configure(apply=True)
        settings = self.settings()
        self.assertEqual(settings["extension"], {"keep": True})
        self.assertEqual(settings["ZCODE_HOME"], str(custom))
        self.assertEqual(settings["ZCODE_BRIDGE_MAX_CONCURRENT_WORKERS"], "5")
        self.assertEqual(settings["ZCODE_BRIDGE_TIMEOUT_MS"], "60000")
        self.assertEqual(settings["ZCODE_BRIDGE_MODE"], "build")
        self.assertEqual(settings["ZCODE_BRIDGE_BROWSER_USE"], "off")
        self.assertTrue(all(settings[key] is None for key in install.MODEL_KEYS))

    def test_active_current_custom_data_root_refuses_upgrade_without_writes(self):
        custom = self.user / "Custom Active Tasks"
        status = write(custom / ".tasks/active/status.json", b'{"status":"running"}')
        original = json.dumps({"ZCODE_BRIDGE_DATA_DIR": str(custom)}).encode()
        config = write(self.home / "codex-zcode/runtime-config.json", original)
        with self.assertRaisesRegex(ValueError, "Active ZCode task"):
            self.configure(apply=True)
        self.assertEqual(config.read_bytes(), original)
        self.assertEqual(status.read_bytes(), b'{"status":"running"}')
        self.assertFalse((self.home / "skills/codex-zcode").exists())
        self.assertFalse((self.home / "config.toml").exists())
        self.assertFalse((self.home / "codex-zcode/backups").exists())

    def test_completed_current_custom_data_root_remains_addressable(self):
        custom = self.user / "Historical Tasks"
        status = write(custom / ".tasks/history/status.json", b'{"status":"completed"}')
        log = write(status.parent / "stdout.log", b"historical output")
        write(self.home / "codex-zcode/runtime-config.json",
              json.dumps({"ZCODE_BRIDGE_DATA_DIR": str(custom)}).encode())
        report = self.configure(apply=True)
        self.assertEqual(report["data_dir"], str(custom))
        self.assertEqual(self.settings()["ZCODE_BRIDGE_DATA_DIR"], str(custom))
        self.assertEqual(status.read_bytes(), b'{"status":"completed"}')
        self.assertEqual(log.read_bytes(), b"historical output")
        self.assertFalse((self.home / "codex-zcode/state").exists())
        self.assertEqual(self.configure(apply=True)["changed_files"], [])

    def test_current_custom_data_root_may_be_new_but_must_be_absolute(self):
        custom = self.user / "New Task Data"
        config = write(self.home / "codex-zcode/runtime-config.json",
                       json.dumps({"ZCODE_BRIDGE_DATA_DIR": str(custom)}).encode())
        self.assertEqual(self.configure()["data_dir"], str(custom))
        self.assertFalse(custom.exists())
        self.configure(apply=True)
        self.assertTrue(custom.is_dir())
        self.assertFalse((self.home / "codex-zcode/state").exists())
        original = b'{"ZCODE_BRIDGE_DATA_DIR":"relative/tasks"}'
        config.write_bytes(original)
        backups = sorted((self.home / "codex-zcode/backups").rglob("*"))
        with self.assertRaisesRegex(ValueError, "must be an absolute task-data directory"):
            self.configure(apply=True)
        self.assertEqual(config.read_bytes(), original)
        self.assertEqual(sorted((self.home / "codex-zcode/backups").rglob("*")), backups)

    def test_only_exact_owned_prototype_is_migrated(self):
        prefix = b'# prefix\n[other]\nkeep = "value"\n\n'
        suffix = b'[mcp_servers.unrelated]\ncommand = "unchanged" # exact\n'
        for root in (self.home / "skills/zcode-orchestrator", self.user / ".agents/skills/zcode-orchestrator"):
            with self.subTest(root=root):
                prototype = root / "runtime/dist/bridge.mjs"
                old = ('[mcp_servers.zcode_bridge]\ncommand = "node"\nargs = [\n  ' +
                       json.dumps(str(prototype)) + ', # path\n]\n\n' +
                       '[mcp_servers.zcode_bridge.env]\nOLD = "remove"\n\n').encode()
                write(self.home / "config.toml", prefix + old + suffix)
                self.configure(apply=True)
                result = (self.home / "config.toml").read_bytes()
                self.assertTrue(result.startswith(prefix))
                self.assertTrue(result.endswith(suffix))
                self.assertNotIn(b"mcp_servers.zcode_bridge", result)
                self.assertEqual(result.count(b"[mcp_servers.codex_zcode]"), 1)
        third_party = (b'[mcp_servers.zcode_bridge]\ncommand = "node"\n'
                       b'args = ["/third party/codex-zcode-bridge/dist/bridge.mjs"]\n\n')
        write(self.home / "config.toml", prefix + third_party + suffix)
        self.configure(apply=True)
        self.assertTrue((self.home / "config.toml").read_bytes().startswith(prefix + third_party + suffix))

    def test_duplicate_owned_sections_fail_before_any_writes(self):
        original = b'[mcp_servers.codex_zcode]\ncommand = "a"\n[mcp_servers."codex_zcode"]\ncommand = "b"\n'
        write(self.home / "config.toml", original)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.configure(apply=True)
        self.assertEqual((self.home / "config.toml").read_bytes(), original)
        self.assertFalse((self.home / "skills").exists())
        self.assertFalse((self.home / "codex-zcode").exists())

    def test_inline_and_dotted_root_mcp_declarations_refuse_without_writes(self):
        cases = (b'mcp_servers = { other = { command = "keep" } }\n',
                 b'mcp_servers.codex_zcode.command = "node"\n',
                 b'[mcp_servers]\ncodex_zcode = { command = "node" }\n',
                 b'\xef\xbb\xbf"mcp_servers" . "codex_zcode" . command = "node"\n',
                 b"[mcp_servers]\n'codex_zcode'.command = 'node'\n")
        for original in cases:
            with self.subTest(original=original):
                config = write(self.home / "config.toml", original)
                with self.assertRaisesRegex(ValueError, r"Unsupported inline/dotted MCP.*\[mcp_servers.NAME\]"):
                    self.configure(apply=True)
                self.assertEqual(config.read_bytes(), original)
                self.assertFalse((self.home / "skills").exists())
                self.assertFalse((self.home / "codex-zcode").exists())

    def test_mcp_text_and_other_profile_declarations_remain_untouched(self):
        original = (b'# mcp_servers = { comment = "text" }\n'
                    b'"mcp_servers.codex_zcode.command" = "literal dotted key"\n'
                    b"snippet = '''\nmcp_servers.codex_zcode.command = 'text'\n"
                    b"[mcp_servers]\ncodex_zcode = { command = 'text' }\n'''\n"
                    b'[profiles.demo]\nmcp_servers = { codex_zcode = { command = "profile" } }\n'
                    b'[profiles.other.mcp_servers]\ncodex_zcode = { command = "another profile" }\n'
                    b'[mcp_servers]\nother = { command = "keep" }\n')
        write(self.home / "config.toml", original)
        self.configure(apply=True)
        result = (self.home / "config.toml").read_bytes()
        self.assertTrue(result.startswith(original))
        self.assertIn(b'\n[mcp_servers.codex_zcode]\ncommand = ', result)

    def test_retirement_is_opt_in_recoverable_and_keeps_external_state(self):
        paths = []
        for skills in (self.home / "skills", self.user / ".agents/skills"):
            for name in install.RETIRED_SKILLS:
                paths.append(write(skills / name / "SKILL.md", name.encode()).parent)
        logs = write(self.home / "codex-zcode-bridge/state/.tasks/old/stdout.log", b"preserve logs")
        write(logs.parent / "status.json", b'{"status":"completed"}')
        self.configure(apply=True)
        self.assertTrue(all(path.exists() for path in paths))
        preview = self.configure(retire_old_skills=True)
        self.assertEqual(len(preview["retired_skills"]), 6)
        self.assertTrue(all(path.exists() for path in paths))
        report = self.configure(apply=True, retire_old_skills=True)
        self.assertFalse(any(path.exists() for path in paths))
        for item in report["retired_skills"]:
            backup = Path(item["backup"])
            self.assertEqual((backup / "SKILL.md").read_bytes(), backup.name.encode())
            self.assertTrue(backup.is_relative_to(self.home / "codex-zcode/backups"))
        self.assertEqual(logs.read_bytes(), b"preserve logs")
        self.assertEqual(self.configure(apply=True, retire_old_skills=True)["retired_skills"], [])

    def test_active_old_worker_refuses_upgrade_without_modification(self):
        status = write(self.home / "codex-zcode-bridge/state/.tasks/active/status.json", b'{"status":"running"}')
        old_skill = write(self.home / "skills/zcode-orchestrator/SKILL.md").parent
        with self.assertRaisesRegex(ValueError, "Active ZCode task"):
            self.configure(apply=True, retire_old_skills=True)
        self.assertEqual(status.read_bytes(), b'{"status":"running"}')
        self.assertTrue(old_skill.exists())
        self.assertFalse((self.home / "config.toml").exists())

    def test_nested_legacy_logs_are_never_relocated(self):
        old_skill = write(self.home / "skills/zcode-orchestrator/SKILL.md").parent
        logs = write(old_skill / "runtime/.tasks/old/stdout.log", b"keep path")
        with self.assertRaisesRegex(ValueError, "state/logs must remain in place"):
            self.configure(apply=True, retire_old_skills=True)
        self.assertEqual(logs.read_bytes(), b"keep path")
        self.assertFalse((self.home / "codex-zcode/backups").exists())

    def test_partial_write_restores_previous_package_and_configs(self):
        original_toml = b'# original\nmodel = "mine"\n'
        original_config = b'{"extension": "preserve"}\n'
        write(self.home / "config.toml", original_toml)
        write(self.home / "codex-zcode/runtime-config.json", original_config)
        skill = write(self.home / "skills/codex-zcode/SKILL.md", b"old package")
        real_write = install.atomic_write

        def fail_toml(path, data, mode=0o600):
            if path == self.home / "config.toml":
                raise OSError("simulated disk error")
            return real_write(path, data, mode)

        with patch.object(install, "atomic_write", side_effect=fail_toml), self.assertRaisesRegex(OSError, "disk error"):
            self.configure(apply=True)
        self.assertEqual(skill.read_bytes(), b"old package")
        self.assertEqual((self.home / "config.toml").read_bytes(), original_toml)
        self.assertEqual((self.home / "codex-zcode/runtime-config.json").read_bytes(), original_config)
        self.assertFalse((skill.parent / "runtime").exists())
        self.assertFalse((self.home / "codex-zcode/backups").exists())
        self.assertFalse(list(self.home.rglob(".codex-zcode-*")))

    def test_failed_retirement_restores_prior_moves_and_writes(self):
        first = write(self.home / "skills/codex-harness-bridge/SKILL.md", b"first").parent
        second = write(self.home / "skills/codex-external-provider/SKILL.md", b"second").parent
        real_replace = install.os.replace

        def fail_second(source, destination):
            if Path(source) == second:
                raise OSError("simulated retirement failure")
            return real_replace(source, destination)

        with patch.object(install.os, "replace", side_effect=fail_second), self.assertRaisesRegex(OSError, "retirement failure"):
            self.configure(apply=True, retire_old_skills=True)
        self.assertEqual((first / "SKILL.md").read_bytes(), b"first")
        self.assertEqual((second / "SKILL.md").read_bytes(), b"second")
        self.assertFalse((self.home / "skills/codex-zcode").exists())
        self.assertFalse((self.home / "config.toml").exists())
        self.assertFalse((self.home / "codex-zcode").exists())

    def test_concurrent_config_change_is_preserved(self):
        path = write(self.home / "config.toml", b"# original\n")
        real_write = install.atomic_write

        def concurrent_write(target, data, mode=0o600):
            result = real_write(target, data, mode)
            if target == self.home / "codex-zcode/runtime-config.json":
                path.write_bytes(b"# edited concurrently\n")
            return result

        with patch.object(install, "atomic_write", side_effect=concurrent_write), self.assertRaisesRegex(RuntimeError, "Concurrent change"):
            self.configure(apply=True)
        self.assertEqual(path.read_bytes(), b"# edited concurrently\n")
        self.assertFalse((self.home / "skills/codex-zcode").exists())
        self.assertFalse((self.home / "codex-zcode").exists())


if __name__ == "__main__":
    unittest.main()
