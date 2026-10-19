#!/usr/bin/env python3
"""Destructive disposable-container lifecycle exercise, never an existing host test.

Run after setup.sh --local-only in a fresh systemd Debian container. Uses an
in-process loopback control-plane fixture and a non-secret sentinel, not OpenAI.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import pwd
import queue
import signal
import subprocess
import sys
import threading
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disposable-container', action='store_true', required=True)
    parser.parse_args()
    if os.geteuid() != 0 or not Path('/.dockerenv').exists():
        raise RuntimeError('Only run as root inside a newly created disposable Docker container')
    os.umask(0o077)  # Match the actual wizard entry point and piped installer.
    sys.path.insert(0, '/opt/codex-ssh')
    import tunnel_service as service
    if service.UNIT_PATH.exists() or service.PROFILE.exists():
        raise RuntimeError('Fresh test installation required; refusing existing tunnel configuration')
    import importlib.util
    spec = importlib.util.spec_from_file_location('wizard', '/opt/codex-ssh/configure-tunnel.py')
    wizard = importlib.util.module_from_spec(spec); spec.loader.exec_module(wizard)
    user = pwd.getpwnam('codex-test')
    home = Path(user.pw_dir)
    config = home / '.config/codex-ssh/guided'
    for p in [home/'.config', home/'.config/codex-ssh', config]:
        p.mkdir(mode=0o700, exist_ok=True); os.chown(p, user.pw_uid, user.pw_gid)
    tunnel_id = 'tunnel_' + 'a'*32
    sentinel = 'test-only-disposable-runtime-sentinel'
    key = config/'runtime-key'
    wizard.private_file(key, sentinel+'\n', user.pw_uid, user.pw_gid)
    wizard.private_file(config/'setup-state.json', json.dumps({'tunnel_id': tunnel_id, 'alias': wizard.ALIAS}), user.pw_uid, user.pw_gid)
    commands, responses = queue.Queue(), queue.Queue()
    poll_count = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def send(self, value=None, code=200):
            data = json.dumps(value).encode() if value is not None else b''
            self.send_response(code); self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data))); self.end_headers()
            try: self.wfile.write(data)
            except BrokenPipeError: pass
        def do_GET(self):
            if self.path.split('?')[0].endswith('/poll'):
                if self.headers.get('Authorization') != 'Bearer '+sentinel:
                    self.send(code=401); return
                poll_count.append(1)
                try: command = commands.get(timeout=.2)
                except queue.Empty: self.send(code=204); return
                self.send({'commands': [command]})
            else:
                self.send({'id': tunnel_id, 'name': 'disposable fixture', 'description': 'not a real tunnel'})
        def do_POST(self):
            responses.put(json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0')))))
            self.send({})

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    # Reproduce the old native supervisor, then migrate using the real wizard.
    args = ['runtimes', 'connect', '--alias', wizard.ALIAS, '--tunnel-id', tunnel_id,
            '--profile', wizard.ALIAS, '--profile-dir', str(config/'profiles'),
            '--mcp-command', service.MCP, '--runtime-api-key', 'file:'+str(key),
            '--control-plane-base-url', base, '--json']
    wizard.client_call(args)
    assert wizard.client_call(['runtimes', 'status', wizard.ALIAS, '--json'])['process_running'] is True
    result = wizard.configure(user)
    assert wizard.is_ready(result) and result['enabled'], result
    assert wizard.client_call(['runtimes', 'status', wizard.ALIAS, '--json'])['process_running'] is False
    pid = int(service.systemctl('show', service.UNIT_NAME, '--property=MainPID', '--value'))
    before = {p: p.read_bytes() for p in [key, home/'.ssh/loopback', home/'.ssh/known_hosts', service.PROFILE]}
    wizard.configure(user)
    assert pid == int(service.systemctl('show', service.UNIT_NAME, '--property=MainPID', '--value'))
    assert all(p.read_bytes() == data for p, data in before.items())
    print('PASS native migration, readiness, repeat setup preserves PID/keys/identity')

    session = {}
    def rpc(n, method, params):
        commands.put({'command_type': 'jsonrpc', 'request_id': 'fixture-'+str(n),
                      'shard_token': 'fixture-shard', 'channel': 'main', 'created_at': '2026-10-19T00:00:00Z',
                      'headers': session, 'jsonrpc': dict({'jsonrpc':'2.0', 'method':method, 'params':params},
                                                       **({} if method.startswith('notifications/') else {'id':n}))})
        deadline = time.monotonic()+20
        while time.monotonic() < deadline:
            response = responses.get(timeout=max(.01, deadline-time.monotonic()))
            if response.get('request_id') == 'fixture-'+str(n):
                for k,v in response.get('resp_headers', {}).items():
                    if k.lower() == 'mcp-session-id': session[k] = v
                result = response.get('resp_json', {})
                assert 'error' not in result, result
                return result
        raise RuntimeError('Fixture RPC response timed out')

    rpc(1, 'initialize', {'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name':'disposable-test','version':'1'}})
    rpc(4, 'notifications/initialized', {})
    tools = rpc(2, 'tools/list', {})
    assert any(t['name']=='ssh_exec' for t in tools['result']['tools'])
    result = rpc(3, 'tools/call', {'name':'ssh_exec','arguments': {'target':'codex-test-local', 'command':"printf 'service-mcp-ok\\n'; id -un",'timeout':10}})
    assert 'service-mcp-ok' in json.dumps(result) and 'codex-test' in json.dumps(result), result
    print('PASS fixture poll -> real tunnel-client -> stdio SSH-MCP -> pinned loopback SSH -> response')

    os.kill(pid, signal.SIGKILL)
    deadline = time.monotonic()+15
    while time.monotonic() < deadline:
        now = int(service.systemctl('show', service.UNIT_NAME, '--property=MainPID', '--value') or '0')
        if now and now != pid and wizard.is_ready(service.status()): break
        time.sleep(.2)
    else: raise RuntimeError('Service did not recover from process failure')
    service.systemctl('disable', '--now', service.UNIT_NAME)
    assert not service.status()['process_running'] and not service.status()['enabled']
    service.systemctl('enable', '--now', service.UNIT_NAME)
    assert wizard.is_ready(service.wait_ready())
    # No terminal/login environment was used by any service start.
    cmdline = Path('/proc/'+service.systemctl('show', service.UNIT_NAME, '--property=MainPID', '--value')+'/cmdline').read_bytes()
    journal = subprocess.check_output(['journalctl','-u',service.UNIT_NAME,'--no-pager','-n','300'])
    assert sentinel.encode() not in cmdline + journal + service.UNIT_PATH.read_bytes() + service.PROFILE.read_bytes()
    assert key.read_text().strip() == sentinel and poll_count
    service.systemctl('disable', '--now', service.UNIT_NAME)
    server.shutdown()
    print('PASS crash recovery, disable/enable without login, sentinel absent from unit/argv/journal/profile')
    print('NOT TESTED: real host reboot, real Proxmox kernel, OpenAI or product connection')


if __name__ == '__main__': main()
