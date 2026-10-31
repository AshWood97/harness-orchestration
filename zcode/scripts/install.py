#!/usr/bin/env python3
"""Install ZCode's ten code roles and merge their host workflow; dry-run by default."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import tempfile

PACKAGE = Path(__file__).resolve().parents[1]
START = b'<!-- codex-zcode-orchestration:quality:start -->'
END = b'<!-- codex-zcode-orchestration:quality:end -->'
ROLES = ('code-reviewer', 'test-verifier', 'design-critic', 'test-author',
         'finding-validator', 'debugger', 'docs-researcher',
         'scout', 'mechanic', 'check-runner')
BUILTINS = ('Explore', 'general-purpose')
BUILTIN_OVERRIDE_FIELDS = ('builtInModelOverrides', 'builtInThoughtLevelOverrides',
                           'builtInModelSelectionOverrides')



def split_role_selection(original):
    """Separate existing model choices from the rest of a role definition."""
    lines = original.replace(b'\r\n', b'\n').splitlines(keepends=True)
    if not lines or lines[0] != b'---\n':
        return b''.join(lines), b''
    try:
        end = lines.index(b'---\n', 1)
    except ValueError:
        return b''.join(lines), b''
    selection = b''.join(line for line in lines[1:end]
                         if line.startswith((b'model:', b'thoughtLevel:')))
    content = b''.join(line for index, line in enumerate(lines)
                       if not (0 < index < end and line.startswith((b'model:', b'thoughtLevel:'))))
    return content, selection


def reset_builtin_overrides(original):
    state = json.loads(original)
    if not isinstance(state, dict):
        raise ValueError('agents-state.json must contain a JSON object')
    changed = False
    for field in BUILTIN_OVERRIDE_FIELDS:
        if field not in state:
            continue
        overrides = state[field]
        if not isinstance(overrides, dict):
            raise ValueError(field + ' must contain a JSON object')
        for role in BUILTINS:
            if role in overrides:
                del overrides[role]
                changed = True
    return (json.dumps(state, indent=2, ensure_ascii=False) + '\n').encode('utf-8') if changed else original


def read_target(path):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError('Refusing non-regular target: ' + str(path))
    return path.read_bytes() if path.exists() else None


def merge_guidance(original, template):
    block = START + b'\n' + template.strip() + b'\n' + END
    if START in original or END in original:
        if original.count(START) != 1 or original.count(END) != 1:
            raise ValueError('Incomplete or duplicate workflow markers in AGENTS.md')
        start, end = original.index(START), original.index(END)
        if end < start:
            raise ValueError('Reversed workflow markers in AGENTS.md')
        return original[:start] + block + original[end + len(END):]
    if original.strip() == template.strip():
        return block + b'\n'
    return original + (b'\n\n' if original else b'') + block + b'\n'


def atomic_write(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.role-install-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def configure(home, model=None, *, thought_level=None, apply=False,
              replace_existing=False, reset_builtin_models=False, profile='turbo'):
    if profile not in ('classic', 'turbo'):
        raise ValueError('Choose profile classic or turbo')
    if model is not None and not re.fullmatch(r'[A-Za-z0-9_.:-]+/[A-Za-z0-9_.:-]+', model):
        raise ValueError('Use the ZCode provider-id/model-id shown in your model settings')
    if thought_level is not None:
        if model is None:
            raise ValueError('--thought-level requires --model')
        if not re.fullmatch(r'[A-Za-z0-9_.:-]+', thought_level):
            raise ValueError('Use a thought level supported by the selected ZCode model')
    home = Path(home).expanduser().resolve()
    agents = home / 'agents'
    if agents.is_symlink():
        raise ValueError('Refusing a symlinked agents directory')
    profile_dir = PACKAGE if profile == 'classic' else PACKAGE / 'profiles' / profile
    plans = []
    templates = {}
    for role in ROLES:
        path = agents / (role + '.md')
        template = (profile_dir / 'agents' / (role + '.md')).read_bytes().replace(b'\r\n', b'\n')
        templates[path] = template
        selection = ''
        if model is not None:
            selection = 'model: ' + json.dumps(model) + '\n'
            if thought_level is not None:
                selection += 'thoughtLevel: ' + thought_level + '\n'
        data = template.replace(b'---\n', b'---\n' + selection.encode('utf-8'), 1)
        plans.append((path, data))
    guidance = home / 'AGENTS.md'
    original_guidance = read_target(guidance)
    originals = {guidance: original_guidance}
    plans.append((guidance, merge_guidance(original_guidance or b'', (profile_dir / 'AGENTS.md').read_bytes())))
    if reset_builtin_models:
        state = home / 'v2' / 'agents-state.json'
        if state.parent.is_symlink():
            raise ValueError('Refusing a symlinked v2 directory')
        original_state = read_target(state)
        if original_state is not None:
            originals[state] = original_state
            plans.append((state, reset_builtin_overrides(original_state)))
    changes = []
    conflicts = []
    for path, data in plans:
        original = originals[path] if path in originals else read_target(path)
        if path in templates and original is not None:
            content, existing_selection = split_role_selection(original)
            if model is None:
                if content == templates[path]:
                    continue
                data = templates[path].replace(b'---\n', b'---\n' + existing_selection, 1)
        if original == data:
            continue
        if (path in templates and original is not None and not replace_existing
                and content != templates[path]):
            conflicts.append(str(path))
        mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
        changes.append((path, original, data, mode))
    report = {'apply': apply, 'profile': profile, 'changed_files': [str(p) for p, _, _, _ in changes],
              'conflicting_roles': conflicts, 'model': model, 'thoughtLevel': thought_level,
              'reset_builtin_models': reset_builtin_models,
              'builtins': 'Reset Explore and general-purpose to inherit' if reset_builtin_models
              else 'Preserve existing built-in model choices'}
    if not apply or not changes:
        return report
    if conflicts:
        raise ValueError('Existing role content differs; inspect dry-run and use --replace-existing only to replace it')
    applied = []
    try:
        for path, original, data, mode in changes:
            if path.parent.is_symlink():
                raise RuntimeError('Concurrent change: ' + str(path.parent))
            current = path.read_bytes() if path.exists() else None
            if path.is_symlink() or current != original:
                raise RuntimeError('Concurrent change: ' + str(path))
            atomic_write(path, data, mode)
            applied.append((path, original, data, mode))
    except BaseException:
        for path, original, data, mode in reversed(applied):
            if path.parent.is_symlink() or path.is_symlink() or path.read_bytes() != data:
                raise RuntimeError('Concurrent change prevents restoration: ' + str(path))
            if original is None:
                path.unlink()
            else:
                atomic_write(path, original, mode)
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zcode-home', type=Path, default=Path.home() / '.zcode')
    parser.add_argument('--profile', choices=('classic', 'turbo'), default='turbo',
                        help='Select the packaged workflow profile (default: turbo)')
    parser.add_argument('--model', help='Optional provider-id/model-id override for the ten custom roles')
    parser.add_argument('--thought-level', help='Optional thought-level override; requires --model')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--replace-existing', action='store_true')
    parser.add_argument('--reset-builtin-models', action='store_true',
                        help='Clear Explore/general-purpose model overrides in v2/agents-state.json')
    args = parser.parse_args()
    try:
        report = configure(args.zcode_home, args.model, thought_level=args.thought_level,
                           apply=args.apply, replace_existing=args.replace_existing,
                           reset_builtin_models=args.reset_builtin_models, profile=args.profile)
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
