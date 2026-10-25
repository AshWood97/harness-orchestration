#!/usr/bin/env python3
"""Install Codex ZCode and its MCP configuration; dry-run unless --apply is set."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile


PACKAGE = Path(__file__).resolve().parents[1]
RETIRED_SKILLS = ("codex-harness-bridge", "codex-external-provider", "zcode-orchestrator")
PATH_KEYS = ("ZCODE_BRIDGE_NODE", "ZCODE_BRIDGE_ZCODE_CJS",
             "ZCODE_BUILTIN_PROVIDER_CONFIG_FILE", "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE", "ZCODE_HOME")
MODEL_KEYS = ("ZCODE_BRIDGE_DEFAULT_PROVIDER_ID", "ZCODE_BRIDGE_DEFAULT_MODEL_ID",
              "ZCODE_BRIDGE_DEFAULT_REASONING_LEVEL")


def readable_file(path):
    try:
        with Path(path).open("rb") as stream:
            stream.read(1)
        return Path(path).is_file()
    except (OSError, ValueError):
        return False


def read_json(path, *, required=False):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if isinstance(value, dict):
            return value
    except (OSError, ValueError, UnicodeError):
        pass
    if required:
        raise ValueError("Cannot read a JSON object from " + str(path))
    return {}


def saved_path(settings, key, *, directory=False):
    value = settings.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value.strip()).expanduser()
    if not path.is_absolute():
        return None
    if path.is_dir() if directory else readable_file(path):
        return path.resolve()
    return None


def application_candidates(platform=None, home=None, environ=None):
    """Return platform installation roots; parameters permit isolated fixtures."""
    platform = sys.platform if platform is None else platform
    home = Path.home() if home is None else Path(home)
    environ = os.environ if environ is None else environ
    if platform == "darwin":
        return [Path("/Applications/ZCode.app"), home / "Applications/ZCode.app"]
    if platform == "win32":
        env = {key.upper(): value for key, value in environ.items()}
        roots = []
        if env.get("LOCALAPPDATA"):
            roots.append(Path(env["LOCALAPPDATA"]) / "Programs/ZCode")
        if env.get("PROGRAMFILES"):
            roots.append(Path(env["PROGRAMFILES"]) / "ZCode")
        return roots
    return []


def application_files(app):
    app = Path(app).expanduser().resolve()
    if app.is_file():
        roots = [app.parent.parent]
        entry = app
    else:
        roots = [app / "Contents/Resources", app / "resources", app]
        entry = None
    for root in roots:
        candidate = entry if entry is not None else root / "glm/zcode.cjs"
        builtin = root / "config/provider/zcode-builtin.json"
        if readable_file(candidate) and readable_file(builtin):
            return candidate.resolve(), builtin.resolve()
    return None


def discover_application(explicit=None, settings=None, *, platform=None, home=None, environ=None):
    if explicit is not None:
        found = application_files(explicit)
        if found is None:
            raise ValueError("--zcode-app must contain zcode.cjs and config/provider/zcode-builtin.json")
        return found
    settings = settings or {}
    entry = saved_path(settings, "ZCODE_BRIDGE_ZCODE_CJS")
    builtin = saved_path(settings, "ZCODE_BUILTIN_PROVIDER_CONFIG_FILE")
    if entry and builtin:
        return entry, builtin
    if entry:
        found = application_files(entry)
        if found:
            return found
    for candidate in application_candidates(platform, home, environ):
        found = application_files(candidate)
        if found:
            return found
    raise ValueError("ZCode was not found; supply --zcode-app with its application directory or zcode.cjs")


def discover_node(explicit=None, settings=None, *, home=None):
    settings = settings or {}
    home = Path.home() if home is None else Path(home)
    if explicit is not None:
        node = Path(explicit).expanduser().resolve()
    else:
        node = saved_path(settings, "ZCODE_BRIDGE_NODE")
        if node is None:
            found = shutil.which("node")
            node = Path(found).resolve() if found else home / ".local/bin/node"
    if not readable_file(node):
        raise ValueError("Node.js was not found; supply --node with a Node.js >=22.18 executable")
    try:
        result = subprocess.run([str(node), "--version"], capture_output=True, text=True,
                                timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        raise ValueError("Cannot run Node.js --version: " + str(node)) from None
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)\s*", result.stdout)
    if result.returncode or not match or tuple(map(int, match.groups())) < (22, 18, 0):
        raise ValueError("Node.js >=22.18 is required: " + str(node))
    return node.resolve()


def discover_zcode_home(explicit=None, settings=None, *, home=None):
    home = Path.home() if home is None else Path(home)
    settings = settings or {}
    candidates = []
    if explicit is not None:
        candidates = [Path(explicit).expanduser().resolve()]
    else:
        configured = saved_path(settings, "ZCODE_HOME", directory=True)
        personal = saved_path(settings, "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE")
        if configured:
            candidates.append(configured)
        if personal and personal.name == "provider_config.json" and personal.parent.name == "v2":
            candidates.append(personal.parent.parent)
        desktop = read_json(home / ".zcode/v2/setting.json")
        base = desktop.get("dataBaseDir")
        if isinstance(base, str) and base.strip() and Path(base.strip()).is_absolute():
            candidates.append(Path(base.strip()) / ".zcode")
        candidates.append(home / ".zcode")
    for candidate in candidates:
        if candidate.name.lower() == ".zcode" and candidate.is_dir():
            personal = candidate / "v2/provider_config.json"
            if readable_file(personal):
                return candidate.resolve(), personal.resolve()
    raise ValueError("A readable .zcode/v2/provider_config.json is required; supply --zcode-home with the .zcode directory")


def _toml_string(text, start):
    if text[start] == '"':
        value, length = json.JSONDecoder().raw_decode(text[start:])
        if not isinstance(value, str):
            raise ValueError("Expected TOML string")
        return value, start + length
    if text[start] == "'":
        end = text.find("'", start + 1)
        if end >= 0:
            return text[start + 1:end], end + 1
    raise ValueError("Expected a single-line TOML string")


def _header(text):
    text = text.strip()
    array = text.startswith("[[")
    if not text.startswith("["):
        return None
    pos = 2 if array else 1
    keys = []
    while True:
        while pos < len(text) and text[pos].isspace():
            pos += 1
        try:
            if text[pos:pos + 1] in ('"', "'"):
                key, pos = _toml_string(text, pos)
            else:
                match = re.match(r"[A-Za-z0-9_-]+", text[pos:])
                if not match:
                    return None
                key = match.group()
                pos += len(key)
        except ValueError:
            return None
        keys.append(key)
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if text[pos:pos + 1] == ".":
            pos += 1
            continue
        closing = "]]" if array else "]"
        if not text.startswith(closing, pos):
            return None
        tail = text[pos + len(closing):].strip()
        return (tuple(keys), array) if not tail or tail.startswith("#") else None


def _scan_line(text, multiline=None, depth=0):
    """Track multiline values so headings inside strings/arrays stay untouched."""
    pos = 0
    while pos < len(text):
        if multiline:
            if text.startswith(multiline, pos):
                multiline = None
                pos += 3
            elif multiline == '"""' and text[pos] == "\\":
                pos += 2
            else:
                pos += 1
            continue
        char = text[pos]
        if char == "#":
            break
        if text.startswith('"""', pos) or text.startswith("'''", pos):
            multiline = text[pos:pos + 3]
            pos += 3
        elif char in ('"', "'"):
            quote = char
            pos += 1
            while pos < len(text):
                if text[pos] == quote:
                    pos += 1
                    break
                if text[pos] == "\\" and quote == '"':
                    pos += 1
                pos += 1
        else:
            if char in "[{":
                depth += 1
            elif char in "]}":
                depth -= 1
            pos += 1
    return multiline, depth


def _assignment_keys(text):
    pos = 0
    while pos < len(text):
        if text[pos] == "#":
            return None
        if text[pos] in ('"', "'"):
            try:
                _, pos = _toml_string(text, pos)
            except ValueError:
                return None
        elif text[pos] == "=":
            heading = _header("[" + text[:pos] + "]")
            return heading[0] if heading else None
        else:
            pos += 1
    return None


def table_sections(data):
    sections = []
    offset = 0
    multiline, depth = None, 0
    for line in data.splitlines(keepends=True):
        text = line.decode("utf-8")
        bom = 3 if offset == 0 and line.startswith(b"\xef\xbb\xbf") else 0
        heading = _header(text.lstrip("\ufeff")) if multiline is None and depth == 0 else None
        if heading:
            if sections:
                sections[-1][3] = offset + bom
            sections.append([heading[0], heading[1], offset + bom, len(data), offset + len(line)])
        else:
            if multiline is None and depth == 0:
                keys = _assignment_keys(text.lstrip("\ufeff"))
                scope = sections[-1][0] if sections else ()
                full = scope + keys if keys else ()
                if full == ("mcp_servers",) or (len(scope) < 2 and full[:2] == ("mcp_servers", "codex_zcode")):
                    raise ValueError("Unsupported inline/dotted MCP declaration; rewrite root MCP configuration using [mcp_servers.NAME] tables before running this installer")
            multiline, depth = _scan_line(text, multiline, depth)
        offset += len(line)
    return sections


def _prototype_args(body):
    statements, statement = [], ""
    multiline, depth = None, 0
    for line in body.decode("utf-8").splitlines(keepends=True):
        statement += line
        multiline, depth = _scan_line(line, multiline, depth)
        if multiline is None and depth == 0:
            statements.append(statement)
            statement = ""
    args = [re.sub(r"^\s*args\s*=\s*", "", value, count=1)
            for value in statements if re.match(r"^\s*args\s*=", value)]
    if len(args) != 1:
        return None
    value = args[0].strip()
    if not value.startswith("["):
        return None
    pos, strings = 1, []
    try:
        while pos < len(value):
            if value[pos].isspace() or value[pos] == ",":
                pos += 1
            elif value[pos] == "#":
                end = value.find("\n", pos)
                pos = len(value) if end < 0 else end + 1
            elif value[pos] == "]":
                tail = value[pos + 1:].strip()
                return strings if not tail or tail.startswith("#") else None
            else:
                item, pos = _toml_string(value, pos)
                strings.append(item)
    except ValueError:
        pass
    return None


def merge_mcp(original, node, entry, *, codex_home, inherited_home, prototype_entries):
    owned = ("mcp_servers", "codex_zcode")
    old = ("mcp_servers", "zcode_bridge")
    sections = table_sections(original)
    seen = set()
    for keys, array, *_ in sections:
        if keys[:2] in (owned, old):
            if keys in seen or array:
                raise ValueError("Duplicate or array MCP table: " + ".".join(keys))
            seen.add(keys)
    migrate = False
    for keys, _, start, end, body in sections:
        if keys == old:
            args = _prototype_args(original[body:end])
            migrate = args is not None and len(args) == 1 and args[0] in prototype_entries
    newline = "\r\n" if b"\r\n" in original else "\n"
    lines = ["[mcp_servers.codex_zcode]", "command = " + json.dumps(str(node), ensure_ascii=False),
             "args = " + json.dumps([str(entry)], ensure_ascii=False),
             "startup_timeout_sec = 20", "tool_timeout_sec = 75",
             'disabled_tools = ["zcode_set_default_model", "zcode_clear_default_model"]']
    if codex_home != inherited_home:
        lines.append("env = { CODEX_HOME = " + json.dumps(str(codex_home), ensure_ascii=False) + " }")
    block = (newline.join(lines) + newline + newline).encode("utf-8")
    replacements, inserted = [], False
    for keys, _, start, end, _ in sections:
        if keys[:2] == owned or (migrate and keys[:2] == old):
            data = b""
            if not inserted:
                data, inserted = block, True
            replacements.append((start, end, data))
    result = original
    for start, end, data in reversed(replacements):
        result = result[:start] + data + result[end:]
    if not inserted:
        separator = b"" if not result else (newline if result.endswith(b"\n") else newline * 2).encode("ascii")
        result += separator + block
    return result


def existing_file(path):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("Refusing non-regular target: " + str(path))
    return path.read_bytes() if path.exists() else None


def atomic_write(path, data, mode=0o600):
    fd, temporary = tempfile.mkstemp(prefix=".codex-zcode-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def refuse_active_workers(roots):
    for root in set(roots):
        for pattern in (".tasks/*/status.json", "tasks/*/status.json"):
            for path in root.glob(pattern):
                value = read_json(path, required=True)
                if value.get("status") in ("queued", "running", "waiting_for_master") or value.get("cleanup_unverified") is True:
                    raise ValueError("Active ZCode task; finish or cancel it before upgrading: " + str(path))


def apply_changes(changes, retirements, directories, active_roots):
    created, attempted, moved = [], [], []

    def mkdir(path):
        absent = []
        while not path.exists():
            absent.append(path)
            path = path.parent
        for directory in reversed(absent):
            directory.mkdir()
            created.append(directory)

    try:
        refuse_active_workers(active_roots)
        for path, original, data, mode in changes:
            if existing_file(path) != original:
                raise RuntimeError("Concurrent change: " + str(path))
            mkdir(path.parent)
            attempted.append((path, original, data, mode))
            atomic_write(path, data, mode)
        for directory in directories:
            mkdir(directory)
        refuse_active_workers(active_roots)
        for source, backup, original_stat in retirements:
            current = source.lstat()
            if source.is_symlink() or (current.st_dev, current.st_ino, current.st_mtime_ns) != original_stat:
                raise RuntimeError("Concurrent change: " + str(source))
            if backup.exists():
                raise RuntimeError("Retirement backup already exists: " + str(backup))
            mkdir(backup.parent)
            os.replace(source, backup)
            moved.append((source, backup))
    except BaseException:
        for source, backup in reversed(moved):
            if source.exists() or source.is_symlink():
                raise RuntimeError("Concurrent change prevents restoration: " + str(source))
            os.replace(backup, source)
        for path, original, data, mode in reversed(attempted):
            current = existing_file(path)
            if current == original:
                continue
            if current != data:
                raise RuntimeError("Concurrent change prevents restoration: " + str(path))
            if original is None:
                path.unlink()
            else:
                atomic_write(path, original, mode)
        for directory in reversed(created):
            try:
                directory.rmdir()
            except OSError:
                pass
        raise


def configure(codex_home=None, *, apply=False, node=None, zcode_app=None, zcode_home=None,
              retire_old_skills=False, source_root=None):
    user_home = Path.home().resolve()
    inherited_home = Path(os.environ.get("CODEX_HOME") or user_home / ".codex").expanduser().resolve()
    codex_home = Path(codex_home).expanduser().resolve() if codex_home is not None else inherited_home
    source = Path(source_root).resolve() if source_root is not None else PACKAGE
    target = codex_home / "skills/codex-zcode"
    settings_dir = codex_home / "codex-zcode"
    config_path = settings_dir / "runtime-config.json"
    toml_path = codex_home / "config.toml"
    if not readable_file(source / "runtime/dist/bridge.mjs"):
        raise ValueError("Packaged runtime is missing: " + str(source / "runtime/dist/bridge.mjs"))
    if target.is_symlink():
        raise ValueError("Refusing a symlinked skill directory: " + str(target))
    original_config = existing_file(config_path)
    current = read_json(config_path, required=True) if original_config is not None else {}
    configured_data = current.get("ZCODE_BRIDGE_DATA_DIR")
    data_dir = settings_dir / "state"
    if configured_data is not None and configured_data != "":
        if not isinstance(configured_data, str) or not Path(configured_data.strip()).is_absolute():
            raise ValueError("ZCODE_BRIDGE_DATA_DIR must be an absolute task-data directory; correct runtime-config.json before upgrading")
        data_dir = Path(configured_data.strip())
    old_dir = codex_home / "codex-zcode-bridge"
    old = read_json(old_dir / "runtime-config.json")
    known = {key: old[key] for key in PATH_KEYS if saved_path(old, key, directory=(key == "ZCODE_HOME"))}
    for key in PATH_KEYS:
        if saved_path(current, key, directory=(key == "ZCODE_HOME")):
            known[key] = current[key]
    resolved_node = discover_node(node, known, home=user_home)
    entry, builtin = discover_application(zcode_app, known, home=user_home)
    personal_home, personal = discover_zcode_home(zcode_home, known, home=user_home)
    updated = dict(current)
    updated.update({"ZCODE_BRIDGE_NODE": str(resolved_node), "ZCODE_BRIDGE_ZCODE_CJS": str(entry),
                    "ZCODE_BUILTIN_PROVIDER_CONFIG_FILE": str(builtin),
                    "ZCODE_PERSONAL_PROVIDER_CONFIG_FILE": str(personal), "ZCODE_HOME": str(personal_home),
                    "ZCODE_BRIDGE_DATA_DIR": str(data_dir),
                    "ZCODE_BRIDGE_MODE": "build", "ZCODE_BRIDGE_BROWSER_USE": "off"})
    for key, default, minimum, maximum in (("ZCODE_BRIDGE_MAX_CONCURRENT_WORKERS", "2", 1, 8),
                                            ("ZCODE_BRIDGE_TIMEOUT_MS", "3600000", 60000, 14400000)):
        value = current.get(key)
        updated[key] = value if isinstance(value, str) and value.isdecimal() and minimum <= int(value) <= maximum else default
    for key in MODEL_KEYS:
        updated[key] = None
    config_data = (json.dumps(updated, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    original_toml = existing_file(toml_path)
    prototype_roots = (codex_home / "skills/zcode-orchestrator", user_home / ".agents/skills/zcode-orchestrator")
    toml_data = merge_mcp(original_toml or b"", resolved_node, target / "runtime/dist/bridge.mjs",
                          codex_home=codex_home, inherited_home=inherited_home,
                          prototype_entries={str(root / "runtime/dist/bridge.mjs") for root in prototype_roots})
    changes = []
    if source != target:
        for path in sorted(source.rglob("*")):
            if any(part in (".git", "__pycache__") for part in path.relative_to(source).parts) or path.suffix in (".pyc", ".pyo"):
                continue
            if path.is_symlink():
                raise ValueError("Refusing a symlink in the packaged skill: " + str(path))
            if path.is_file():
                destination = target / path.relative_to(source)
                original = existing_file(destination)
                data = path.read_bytes()
                if data != original:
                    mode = stat.S_IMODE(destination.stat().st_mode) if original is not None else stat.S_IMODE(path.stat().st_mode)
                    changes.append((destination, original, data, mode))
    for path, original, data in ((config_path, original_config, config_data), (toml_path, original_toml, toml_data)):
        if data != original:
            mode = stat.S_IMODE(path.stat().st_mode) if original is not None else 0o600
            changes.append((path, original, data, mode))
    active_roots = [old_dir, old_dir / "state", settings_dir / "state", data_dir]
    old_data = old.get("ZCODE_BRIDGE_DATA_DIR")
    if isinstance(old_data, str) and Path(old_data).is_absolute():
        active_roots.append(Path(old_data))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    backup_changes, report_backups = [], []
    for path, original, _, _ in changes:
        if original is not None:
            backup = settings_dir / "backups" / stamp / "files" / path.relative_to(codex_home)
            if backup.exists() or backup.is_symlink():
                raise RuntimeError("Upgrade backup already exists: " + str(backup))
            backup_changes.append((backup, None, original, 0o600))
            report_backups.append({"source": str(path), "backup": str(backup)})
    retired, report_retired = [], []
    if retire_old_skills:
        for label, skills in (("codex", codex_home / "skills"), ("agents", user_home / ".agents/skills")):
            for name in RETIRED_SKILLS:
                path = skills / name
                if not path.exists() and not path.is_symlink():
                    continue
                if path.is_symlink() or not path.is_dir():
                    raise ValueError("Refusing non-directory legacy skill: " + str(path))
                for base in (path, path / "runtime"):
                    active_roots.append(base)
                    for state in (".tasks", "state", "logs"):
                        nested = base / state
                        if nested.is_dir() and any(nested.iterdir()):
                            raise ValueError("Legacy state/logs must remain in place; cannot retire " + str(path))
                backup = settings_dir / "backups" / stamp / label / name
                info = path.stat()
                retired.append((path, backup, (info.st_dev, info.st_ino, info.st_mtime_ns)))
                report_retired.append({"source": str(path), "backup": str(backup)})
    refuse_active_workers(active_roots)
    report = {"apply": apply, "changed_files": [str(item[0]) for item in changes],
              "installed_skill": str(target), "runtime_config": str(config_path), "config_toml": str(toml_path),
              "data_dir": str(data_dir), "backup_files": report_backups,
              "retired_skills": report_retired}
    if apply:
        apply_changes(backup_changes + changes, retired, [data_dir], active_roots)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Apply the planned local changes")
    parser.add_argument("--codex-home", type=Path, help="Defaults to CODEX_HOME or ~/.codex")
    parser.add_argument("--node", type=Path, help="Node.js >=22.18 executable")
    parser.add_argument("--zcode-app", type=Path, help="ZCode application directory or zcode.cjs entry")
    parser.add_argument("--zcode-home", type=Path, help="Personal .zcode directory")
    parser.add_argument("--retire-old-skills", action="store_true", help="Move the three superseded skills into recoverable backups")
    args = parser.parse_args()
    try:
        report = configure(**vars(args))
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, str(exc) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
