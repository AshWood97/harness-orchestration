import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('zcode_install', Path(__file__).resolve().parents[1] / 'scripts/install.py')
install = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(install)
MODEL = 'example-provider/example-model'


class InstallTests(unittest.TestCase):
    def test_dry_run_does_not_create_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve() / 'new-home'
            result = install.configure(home, reset_builtin_models=True)
            self.assertEqual(len(result['changed_files']), 8)
            self.assertFalse(home.exists())

    def test_install_preserves_guidance_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            original = b'\xef\xbb\xbfPersonal rule\r\n'
            (home / 'AGENTS.md').write_bytes(original)
            install.configure(home, apply=True)
            self.assertTrue((home / 'AGENTS.md').read_bytes().startswith(original))
            self.assertEqual(len(list((home / 'agents').glob('*.md'))), 7)
            for p in (home / 'agents').glob('*.md'):
                text = p.read_text(encoding='utf-8')
                self.assertNotIn('\nmodel:', text)
                self.assertNotIn('\nthoughtLevel:', text)
                self.assertNotIn('__ZCODE_MODEL_ID__', text)
            self.assertEqual(install.configure(home, apply=True)['changed_files'], [])

    def test_explicit_model_and_optional_thought_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            result = install.configure(home, MODEL, apply=True)
            self.assertEqual(result['model'], MODEL)
            self.assertIsNone(result['thoughtLevel'])
            for role in install.ROLES:
                text = (home / 'agents' / (role + '.md')).read_text(encoding='utf-8')
                self.assertIn('model: "' + MODEL + '"', text)
                self.assertNotIn('\nthoughtLevel:', text)
            install.configure(home, MODEL, thought_level='medium', apply=True)
            for role in install.ROLES:
                text = (home / 'agents' / (role + '.md')).read_text(encoding='utf-8')
                self.assertIn('model: "' + MODEL + '"', text)
                self.assertIn('thoughtLevel: medium', text)
            self.assertEqual(install.configure(home, MODEL, thought_level='medium', apply=True)['changed_files'], [])

    def test_crlf_templates_render_explicit_model_and_preserve_personal_guidance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            package = root / 'package'
            (package / 'agents').mkdir(parents=True)
            for role in install.ROLES:
                name = role + '.md'
                template = (install.PACKAGE / 'agents' / name).read_bytes().replace(b'\r\n', b'\n')
                (package / 'agents' / name).write_bytes(template.replace(b'\n', b'\r\n'))
            (package / 'AGENTS.md').write_bytes(b'Packaged guidance\r\n')
            home = root / 'home'
            home.mkdir()
            prefix, suffix = b'\xef\xbb\xbfPersonal rule\r\n', b'\r\nPersonal suffix\r\n'
            (home / 'AGENTS.md').write_bytes(prefix + install.START + b'\r\nold\r\n' + install.END + suffix)
            with patch.object(install, 'PACKAGE', package):
                install.configure(home, MODEL, thought_level='medium', apply=True)
                for role in install.ROLES:
                    data = (home / 'agents' / (role + '.md')).read_bytes()
                    self.assertIn(('model: "' + MODEL + '"\n').encode('utf-8'), data)
                    self.assertIn(b'thoughtLevel: medium\n', data)
                    self.assertNotIn(b'\r\n', data)
                guidance = (home / 'AGENTS.md').read_bytes()
                self.assertTrue(guidance.startswith(prefix))
                self.assertTrue(guidance.endswith(suffix))
                self.assertEqual(install.configure(home, MODEL, thought_level='medium', apply=True)['changed_files'], [])

    def test_unmodified_legacy_roles_migrate_to_inheritance(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            agents = home / 'agents'
            agents.mkdir()
            for role in install.ROLES:
                template = (install.PACKAGE / 'agents' / (role + '.md')).read_bytes().replace(b'\r\n', b'\n')
                legacy = template.replace(b'tools:', b'model: "legacy-provider/legacy-model"\nthoughtLevel: high\ntools:', 1)
                (agents / (role + '.md')).write_bytes(legacy.replace(b'\n', b'\r\n'))
            result = install.configure(home)
            self.assertEqual(result['conflicting_roles'], [])
            self.assertEqual(len(result['changed_files']), 8)
            install.configure(home, apply=True)
            for role in install.ROLES:
                name = role + '.md'
                self.assertEqual((agents / name).read_bytes(), (install.PACKAGE / 'agents' / name).read_bytes().replace(b'\r\n', b'\n'))
            self.assertEqual(install.configure(home, apply=True)['changed_files'], [])

    def test_modified_role_requires_explicit_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            install.configure(home, MODEL, apply=True)
            role = home / 'agents/code-reviewer.md'
            customized = (role.read_bytes() + b'\nMy customized reviewer\n').replace(b'\n', b'\r\n')
            role.write_bytes(customized)
            result = install.configure(home, MODEL)
            self.assertEqual(result['conflicting_roles'], [str(role)])
            with self.assertRaises(ValueError):
                install.configure(home, MODEL, apply=True)
            self.assertEqual(role.read_bytes(), customized)
            install.configure(home, MODEL, apply=True, replace_existing=True)

    def test_default_install_preserves_builtin_and_plugin_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            state = home / 'v2' / 'agents-state.json'
            state.parent.mkdir()
            original = b'{"builtInModelOverrides":{"Explore":"personal/model"},"builtInThoughtLevelOverrides":{"Explore":"low"},"builtInModelSelectionOverrides":{"general-purpose":{"model":"personal/new-model"}},"pluginAgentModelSelectionOverrides":{"plugin:reviewer":{"model":"plugin/model"}},"disabledAgentIds":["plugin:disabled"],"future":{"keep":true}}\n'
            state.write_bytes(original)
            result = install.configure(home, apply=True)
            self.assertNotIn(str(state), result['changed_files'])
            self.assertEqual(state.read_bytes(), original)

    def test_builtin_reset_dry_run_then_apply_preserves_other_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            state = home / 'v2' / 'agents-state.json'
            state.parent.mkdir()
            before = {
                'builtInModelOverrides': {'Explore': 'old/explore', 'general-purpose': 'old/general', 'other': 'keep/model'},
                'builtInThoughtLevelOverrides': {'Explore': 'high', 'general-purpose': 'low', 'other': 'medium'},
                'builtInModelSelectionOverrides': {
                    'Explore': {'provider': 'new', 'model': 'explore'},
                    'general-purpose': {'provider': 'new', 'model': 'general'},
                    'other': {'provider': 'keep', 'model': 'other'},
                },
                'pluginAgentModelSelectionOverrides': {'plugin:reviewer': {'model': 'keep/plugin'}},
                'disabledAgentIds': ['built-in:Explore', 'plugin:disabled'],
                'future': {'keep': [1, 2]},
            }
            original = json.dumps(before).encode('utf-8')
            state.write_bytes(original)
            if os.name == 'posix':
                state.chmod(0o640)
            preview = install.configure(home, reset_builtin_models=True)
            self.assertIn(str(state), preview['changed_files'])
            self.assertEqual(state.read_bytes(), original)
            self.assertFalse((home / 'agents').exists())
            install.configure(home, reset_builtin_models=True, apply=True)
            expected = json.loads(original)
            for field in ('builtInModelOverrides', 'builtInThoughtLevelOverrides', 'builtInModelSelectionOverrides'):
                for role in ('Explore', 'general-purpose'):
                    del expected[field][role]
            self.assertEqual(json.loads(state.read_bytes()), expected)
            if os.name == 'posix':
                self.assertEqual(state.stat().st_mode & 0o777, 0o640)
            self.assertEqual(install.configure(home, reset_builtin_models=True, apply=True)['changed_files'], [])

    def test_reset_without_builtin_overrides_does_not_rewrite_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            install.configure(home, reset_builtin_models=True, apply=True)
            self.assertFalse((home / 'v2').exists())
            state = home / 'v2' / 'agents-state.json'
            state.parent.mkdir()
            original = b'{ "builtInModelSelectionOverrides": {}, "builtInModelOverrides": {"other": "keep/model"}, "pluginAgentModelSelectionOverrides": {"plugin:agent": {}}, "disabledAgentIds": ["plugin:agent"] }\n'
            state.write_bytes(original)
            self.assertEqual(install.configure(home, reset_builtin_models=True, apply=True)['changed_files'], [])
            self.assertEqual(state.read_bytes(), original)

    def test_marked_update_preserves_prefix_and_suffix(self):
        old = b'prefix\r\n' + install.START + b'\nold\n' + install.END + b'\r\nsuffix'
        updated = install.merge_guidance(old, b'new guidance')
        self.assertTrue(updated.startswith(b'prefix\r\n'))
        self.assertTrue(updated.endswith(b'\r\nsuffix'))
        self.assertEqual(updated.count(install.START), 1)
        self.assertNotIn(b'\nold\n', updated)

    def test_malformed_markers_fail_before_role_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            (home / 'AGENTS.md').write_bytes(install.START)
            with self.assertRaises(ValueError):
                install.configure(home, MODEL, apply=True)
            self.assertFalse((home / 'agents').exists())

    def test_invalid_model_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve() / 'home'
            for value in ('', 'model-only', 'provider/model\ninject: true', 'provider/"model'):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    install.configure(home, value, apply=True)
            self.assertFalse(home.exists())

    def test_thought_level_requires_explicit_model_and_rejects_injection(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve() / 'home'
            with self.assertRaisesRegex(ValueError, 'requires --model'):
                install.configure(home, thought_level='medium', apply=True)
            for value in ('', 'high\ninject: true'):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    install.configure(home, MODEL, thought_level=value, apply=True)
            self.assertFalse(home.exists())

    def test_invalid_state_fails_before_role_writes(self):
        for original in (b'not json', b'[]', b'{"builtInModelOverrides": []}'):
            with self.subTest(original=original), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp).resolve()
                state = home / 'v2' / 'agents-state.json'
                state.parent.mkdir()
                state.write_bytes(original)
                with self.assertRaises(ValueError):
                    install.configure(home, reset_builtin_models=True, apply=True)
                self.assertEqual(state.read_bytes(), original)
                self.assertFalse((home / 'agents').exists())

    def test_symlinked_state_targets_are_rejected_before_role_writes(self):
        for symlink_directory in (False, True):
            with self.subTest(directory=symlink_directory), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve()
                home = root / 'home'
                home.mkdir()
                outside = root / 'outside'
                outside.mkdir()
                target = outside / 'agents-state.json'
                original = b'{"builtInModelOverrides":{"Explore":"personal/model"}}'
                target.write_bytes(original)
                if symlink_directory:
                    (home / 'v2').symlink_to(outside, target_is_directory=True)
                else:
                    (home / 'v2').mkdir()
                    (home / 'v2' / 'agents-state.json').symlink_to(target)
                with self.assertRaises(ValueError):
                    install.configure(home, reset_builtin_models=True, apply=True)
                self.assertEqual(target.read_bytes(), original)
                self.assertFalse((home / 'agents').exists())

    def test_partial_write_failure_restores_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            (home / 'agents').mkdir()
            first = home / 'agents/code-reviewer.md'
            first.write_bytes(b'original')
            real_write = install.atomic_write
            def write(path, data, mode=0o600):
                if path == home / 'agents/test-verifier.md':
                    raise OSError('simulated write failure')
                return real_write(path, data, mode)
            with patch.object(install, 'atomic_write', side_effect=write), self.assertRaises(OSError):
                install.configure(home, MODEL, apply=True, replace_existing=True)
            self.assertEqual(first.read_bytes(), b'original')
            self.assertFalse((home / 'AGENTS.md').exists())

    def test_state_write_failure_restores_legacy_role_and_guidance(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            install.configure(home, apply=True)
            first = home / 'agents/code-reviewer.md'
            legacy = first.read_bytes().replace(b'\r\n', b'\n').replace(b'tools:', b'model: "old/model"\nthoughtLevel: high\ntools:', 1).replace(b'\n', b'\r\n')
            first.write_bytes(legacy)
            guidance = home / 'AGENTS.md'
            original_guidance = b'prefix\n' + install.START + b'\nold managed guidance\n' + install.END + b'\nsuffix\n'
            guidance.write_bytes(original_guidance)
            state = home / 'v2' / 'agents-state.json'
            state.parent.mkdir()
            original_state = b'{"builtInModelSelectionOverrides":{"Explore":{"model":"old"}}}\n'
            state.write_bytes(original_state)
            real_write = install.atomic_write
            def write(path, data, mode=0o600):
                if path == state:
                    raise OSError('simulated state write failure')
                return real_write(path, data, mode)
            with patch.object(install, 'atomic_write', side_effect=write), self.assertRaises(OSError):
                install.configure(home, reset_builtin_models=True, apply=True)
            self.assertEqual(first.read_bytes(), legacy)
            self.assertEqual(guidance.read_bytes(), original_guidance)
            self.assertEqual(state.read_bytes(), original_state)

    def test_concurrent_state_change_aborts_and_restores_new_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            state = home / 'v2' / 'agents-state.json'
            state.parent.mkdir()
            state.write_bytes(b'{"builtInModelOverrides":{"Explore":"old/model"}}')
            concurrent = b'{"builtInModelOverrides":{"Explore":"personal/model"},"personal":true}'
            real_write = install.atomic_write
            def write(path, data, mode=0o600):
                if path == home / 'agents/code-reviewer.md':
                    state.write_bytes(concurrent)
                return real_write(path, data, mode)
            with patch.object(install, 'atomic_write', side_effect=write), self.assertRaisesRegex(RuntimeError, 'Concurrent change:'):
                install.configure(home, reset_builtin_models=True, apply=True)
            self.assertEqual(state.read_bytes(), concurrent)
            self.assertEqual(list((home / 'agents').glob('*.md')), [])
            self.assertFalse((home / 'AGENTS.md').exists())

    def test_concurrent_role_edit_is_preserved_during_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            (home / 'agents').mkdir()
            first = home / 'agents/code-reviewer.md'
            first.write_bytes(b'original')
            real_write = install.atomic_write
            def write(path, data, mode=0o600):
                if path == home / 'agents/test-verifier.md':
                    first.write_bytes(b'concurrent edit')
                    raise OSError('simulated write failure')
                return real_write(path, data, mode)
            with patch.object(install, 'atomic_write', side_effect=write), self.assertRaisesRegex(RuntimeError, 'prevents restoration'):
                install.configure(home, replace_existing=True, apply=True)
            self.assertEqual(first.read_bytes(), b'concurrent edit')


if __name__ == '__main__':
    unittest.main()
