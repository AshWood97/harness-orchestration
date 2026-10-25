#!/usr/bin/env python3
"""Call the bundled ZCode MCP bridge without restarting the Codex chat.

Only the MCP transport is short-lived. Upstream detached workers and persisted
ZCode sessions survive each call. Model credentials are read by ZCode itself.
"""
import argparse
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import time

SKILL = Path(__file__).resolve().parents[1]
CODEX_DIR = Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex').expanduser()
CONFIG = CODEX_DIR / 'codex-zcode/runtime-config.json'
TOOLS = {
    'zcode_doctor', 'zcode_model_catalog', 'zcode_task',
    'zcode_status', 'zcode_feedback', 'zcode_events', 'zcode_interaction_reply',
    'zcode_result', 'zcode_continue', 'zcode_cancel',
}


class TransportError(Exception):
    pass


class Client:
    def __init__(self):
        config = json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
        node = config.get('ZCODE_BRIDGE_NODE') or shutil.which('node')
        if not node:
            raise TransportError('Node.js is unavailable; inspect runtime-config.json')
        entry = SKILL / 'runtime/dist/bridge.mjs'
        if not entry.is_file():
            raise TransportError('The bundled bridge is missing')
        env = dict(os.environ)
        self.proc = subprocess.Popen(
            [node, str(entry)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env, cwd=str(SKILL / 'runtime'),
        )
        self.inbox = queue.Queue()
        self.ident = 0
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._drain_stderr, daemon=True).start()

    def _read(self):
        limit = 16 * 1024 * 1024
        while True:
            line = self.proc.stdout.readline(limit + 1)
            if not line:
                self.inbox.put(TransportError('Bridge transport closed'))
                return
            if len(line) > limit or not line.endswith(b'\n'):
                self.inbox.put(TransportError('Bridge returned an invalid or oversized frame'))
                return
            try:
                message = json.loads(line)
            except (ValueError, UnicodeError):
                self.inbox.put(TransportError('Bridge returned invalid JSON'))
                return
            if not isinstance(message, dict):
                self.inbox.put(TransportError('Bridge returned a non-object frame'))
                return
            self.inbox.put(message)

    def _drain_stderr(self):
        # Keep logs out of stdout and do not echo provider/runtime diagnostics.
        while self.proc.stderr.read(4096):
            pass

    def send(self, message):
        self.proc.stdin.write((json.dumps(message, ensure_ascii=False) + '\n').encode())
        self.proc.stdin.flush()

    def request(self, method, params, timeout=70):
        self.ident += 1
        ident = self.ident
        self.send({'jsonrpc': '2.0', 'id': ident, 'method': method, 'params': params})
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TransportError('MCP response timed out; inspect the same task_id before retrying')
            try:
                item = self.inbox.get(timeout=remaining)
            except queue.Empty:
                raise TransportError('MCP response timed out; inspect the same task_id before retrying')
            if isinstance(item, Exception):
                raise item
            if 'method' in item:
                if 'id' in item:
                    self.send({'jsonrpc': '2.0', 'id': item['id'], 'error': {'code': -32601, 'message': 'Unsupported client method'}})
                continue
            if item.get('id') == ident:
                if 'error' in item:
                    error = item['error']
                    raise TransportError(f"MCP error {error.get('code')}: {error.get('message')}")
                return item.get('result', {})

    def initialize(self):
        self.request('initialize', {
            'protocolVersion': '2025-03-26', 'capabilities': {},
            'clientInfo': {'name': 'codex-zcode-skill', 'version': '5.0.0'},
        })
        self.send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()  # Upstream explicitly preserves detached workers.
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            try:
                stream.close()
            except OSError:
                pass


def read_json(filename):
    raw = sys.stdin.read() if filename == '-' else Path(filename).read_text()
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError('Tool input must be a JSON object')
    return result


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    subs.add_parser('doctor')
    subs.add_parser('tools')
    models = subs.add_parser('models')
    models.add_argument('--workspace', required=True)
    submit = subs.add_parser('submit')
    submit.add_argument('--file', required=True, help='TaskPackage JSON file, or - for stdin')
    for name in ('status', 'result', 'feedback', 'cancel'):
        subs.add_parser(name).add_argument('task_id')
    events = subs.add_parser('events')
    events.add_argument('task_id')
    events.add_argument('--after', type=int, default=0)
    events.add_argument('--wait-ms', type=int, default=20000, choices=range(0, 25001), metavar='0..25000')
    events.add_argument('--view', choices=['summary', 'raw'], default='summary')
    cont = subs.add_parser('continue')
    cont.add_argument('task_id')
    cont.add_argument('--feedback-file', required=True)
    cont.add_argument('--operation-id', required=True)
    call = subs.add_parser('call')
    call.add_argument('tool', choices=sorted(TOOLS))
    call.add_argument('--input', required=True, help='JSON file, or - for stdin')
    return parser.parse_args()


def main():
    args = parse_args()
    command = args.command
    if command == 'doctor':
        tool, payload = 'zcode_doctor', {}
    elif command == 'models':
        tool, payload = 'zcode_model_catalog', {'workspace': str(Path(args.workspace).resolve())}
    elif command == 'submit':
        tool, payload = 'zcode_task', read_json(args.file)
    elif command == 'events':
        tool, payload = 'zcode_events', {'task_id': args.task_id, 'after_seq': args.after, 'wait_ms': args.wait_ms, 'view': args.view}
    elif command == 'continue':
        tool, payload = 'zcode_continue', {'task_id': args.task_id, 'feedback': Path(args.feedback_file).read_text(), 'operation_id': args.operation_id}
    elif command == 'call':
        tool, payload = args.tool, read_json(args.input)
    elif command != 'tools':
        tool, payload = 'zcode_' + command, {'task_id': args.task_id}
    client = Client()
    try:
        client.initialize()
        if command == 'tools':
            result = client.request('tools/list', {})
        else:
            result = client.request('tools/call', {'name': tool, 'arguments': payload})
        failed = bool(result.get('isError'))
        output = result.get('structuredContent')
        if output is None:
            blocks = result.get('content', [])
            if len(blocks) == 1 and blocks[0].get('type') == 'text':
                try:
                    output = json.loads(blocks[0]['text'])
                except ValueError:
                    output = {'text': blocks[0]['text']}
            else:
                output = result
        if failed:
            output = {'isError': True, 'result': output}
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 2 if failed else 0
    finally:
        client.close()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (TransportError, OSError, ValueError) as exc:
        print(json.dumps({'isError': True, 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
