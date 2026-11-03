"""Check that Qoder can discover the roles and files named by the package."""
import json
import re
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1] / "harness-orchestration"
EXPECTED_ROLES = {
    "check-runner", "conductor", "debugger", "design-critic", "explorer",
    "finding-validator", "guardian", "mechanic", "orchestrator", "researcher",
    "reviewer", "scout", "test-author", "tester", "worker",
}


def frontmatter_field(path, field):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
    if not match:
        raise AssertionError(f"Missing frontmatter: {path}")
    field_match = re.search(rf"^{re.escape(field)}:\s*(.+?)\s*$", match.group(1), re.MULTILINE)
    if not field_match:
        raise AssertionError(f"Missing {field}: {path}")
    return field_match.group(1).strip('"\'')


class PluginStructureTest(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((PACKAGE / ".qoder-plugin/plugin.json").read_text(encoding="utf-8"))

    def test_registered_agents_match_existing_role_files_and_names(self):
        entries = self.manifest["agents"]
        self.assertEqual(len(entries), len(set(entries)))
        paths = [(PACKAGE / entry).resolve() for entry in entries]
        self.assertEqual(set(paths), {p.resolve() for p in (PACKAGE / "agents").glob("*.md")})
        self.assertEqual({path.stem for path in paths}, EXPECTED_ROLES)
        for path in paths:
            self.assertTrue(path.is_file(), path)
            self.assertEqual(frontmatter_field(path, "name"), path.stem)

    def test_skill_version_and_hook_paths_match_manifest(self):
        skill = PACKAGE / self.manifest["skills"] / "harness-orchestration/SKILL.md"
        self.assertEqual(frontmatter_field(skill, "name"), "harness-orchestration")
        self.assertEqual(frontmatter_field(skill, "version"), self.manifest["version"])
        hooks = json.loads((PACKAGE / self.manifest["hooks"]).read_text(encoding="utf-8"))
        submit = hooks["hooks"]["UserPromptSubmit"]
        commands = [h["command"] for entry in submit for h in entry["hooks"]]
        self.assertTrue(any("${QODER_PLUGIN_ROOT}/hooks/default-agent-instructions.txt" in command for command in commands))
        self.assertTrue((PACKAGE / "hooks/default-agent-instructions.txt").is_file())


if __name__ == "__main__":
    unittest.main()
