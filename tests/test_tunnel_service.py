"""Regression tests for service ownership, migration and actual terminal input."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import tunnel_service as service
spec = importlib.util.spec_from_file_location('configure', ROOT / 'scripts/configure-tunnel.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)
ID = 'tunnel_' + 'a' * 32


class ServiceTests(unittest.TestCase):
    def test_profile_preserves_transport_and_uses_only_protected_reference(self):
        with tempfile.TemporaryDirectory() as d:
            key = Path(d) / 'key'; key.write_text('test-only-not-a-real-key'); key.chmod(0o600)
            source = {'control_plane': {'base_url': 'http://127.0.0.1:1111', 'url_path': '/fixture'}}
            result = service.profile_for(ID, key, source)
            self.assertEqual(result['control_plane']['api_key'], 'file:' + str(key))
            self.assertEqual(result['control_plane']['url_path'], '/fixture')
            self.assertNotIn(key.read_text(), json.dumps(result) + service.UNIT)
            self.assertEqual(source, {'control_plane': {'base_url': 'http://127.0.0.1:1111', 'url_path': '/fixture'}})
            key.chmod(0o644)
            with self.assertRaisesRegex(RuntimeError, '0600'): service.profile_for(ID, key)

    def test_conflicting_native_target_or_inline_key_not_adopted(self):
        with tempfile.TemporaryDirectory() as d:
            key = Path(d) / 'key'; key.write_text('test-only-sentinel'); key.chmod(0o600)
            for source in [{'control_plane': {'api_key': 'inline-test-key'}},
                           {'control_plane': {'tunnel_id': 'different'}},
                           {'mcp': {'server_urls': [{'url': 'http://example.invalid'}]}},
                           {'mcp': {'commands': [{'command': '/unrelated'}]}}]:
                with self.subTest(source=source), self.assertRaises(RuntimeError):
                    service.profile_for(ID, key, source)

    def test_native_migration_must_confirm_stop_before_new_supervisor(self):
        commands = []
        def call(args):
            commands.append(args)
            return {'process_running': len(commands) == 1}
        service.stop_native([('codex-ssh-guided', {})], call)
        self.assertEqual([c[1] for c in commands], ['status', 'stop', 'status'])
        with self.assertRaisesRegex(RuntimeError, 'not confirmed'):
            service.stop_native([('codex-ssh-guided', {})], lambda args: {'process_running': True})

    def test_unknown_alias_same_tunnel_is_not_stopped(self):
        with self.assertRaisesRegex(RuntimeError, 'outside this setup'):
            service.native_candidates({'aliases': [{'alias': 'somebody-else', 'tunnel_id': ID}]}, ID)
        with self.assertRaisesRegex(RuntimeError, 'another tunnel'):
            service.native_candidates({'aliases': [{'alias': 'codex-ssh-guided', 'tunnel_id': 'other'}]}, ID)

    def test_generated_json_native_profile_can_be_adopted_without_overwriting_it(self):
        with tempfile.TemporaryDirectory() as d:
            profile = Path(d) / 'old.yaml'; original = '{"config_version": 1}'
            profile.write_text(original)
            result = service.native_candidates({'aliases': [{'alias': 'codex-test-proxmox', 'tunnel_id': ID,
                                                               'config_path': str(profile)}]}, ID)
            self.assertEqual(result, [('codex-test-proxmox', {'config_version': 1})])
            self.assertEqual(profile.read_text(), original)
            profile.write_text('config_version: 1\n')
            with self.assertRaisesRegex(RuntimeError, 'manual'): service.load_profile(profile)

    def test_repeat_install_is_idempotent_and_does_not_restart(self):
        with tempfile.TemporaryDirectory() as d, patch.object(service, 'PROFILE', Path(d) / 'config'), \
             patch.object(service, 'UNIT_PATH', Path(d) / 'unit'), patch.object(service, 'systemctl') as ctl, patch.object(service.os, 'fchown'):
            config = {'control_plane': {'api_key': 'file:/private/key'}}
            service.install(config, os.getgid())
            self.assertEqual(service.PROFILE.stat().st_mode & 0o777, 0o640)
            times = [p.stat().st_mtime_ns for p in (service.PROFILE, service.UNIT_PATH)]
            service.install(config, os.getgid())
            self.assertEqual(times, [p.stat().st_mtime_ns for p in (service.PROFILE, service.UNIT_PATH)])
            self.assertEqual(ctl.call_count, 4)
            self.assertEqual(ctl.call_args.args, ('enable', '--now', service.UNIT_NAME))
            with self.assertRaisesRegex(RuntimeError, 'differs'): service.install({'other': True}, os.getgid())

    def test_nonmanaged_unit_and_dropins_are_preserved(self):
        original_exists = Path.exists
        original_is_dir = Path.is_dir
        conflict = Path('/etc/systemd/system') / service.UNIT_NAME
        with patch.object(Path, 'exists', lambda p: True if p == conflict else original_exists(p)), \
             patch.object(Path, 'read_text', return_value='# another administrator'), \
             self.assertRaisesRegex(RuntimeError, 'Conflicting'):
            service.preflight()
        drop = Path('/etc/systemd/system') / (service.UNIT_NAME + '.d')
        with patch.object(Path, 'exists', lambda p: p == drop), \
             patch.object(Path, 'iterdir', return_value=iter([drop/'custom.conf'])), \
             self.assertRaisesRegex(RuntimeError, 'drop-ins'):
            service.preflight()

    def test_status_does_not_follow_arbitrary_urls_or_claim_polling(self):
        fields = 'ActiveState=active\nMainPID=123\nUnitFileState=enabled\n'
        with tempfile.TemporaryDirectory() as d, patch.object(service, 'HEALTH_FILE', Path(d)/'url'), \
             patch.object(service, 'systemctl', return_value=fields):
            service.HEALTH_FILE.write_text('http://example.invalid:80')
            with self.assertRaisesRegex(RuntimeError, 'Unexpected'): service.status()
            service.HEALTH_FILE.unlink()
            self.assertEqual(service.status(), dict(process_running=True, enabled=True, healthy=False, ready=False))

    def test_interrupted_key_write_is_reused_without_asking_for_another_key(self):
        with tempfile.TemporaryDirectory() as d:
            key = Path(d)/'key'; key.write_text('test-sentinel'); key.chmod(0o600)
            state = Path(d)/'state'
            # Incomplete setup requires only the missing tunnel ID on the next attempt.
            with patch('builtins.open', side_effect=[io.StringIO(ID+'\n'), io.StringIO()]), \
                 patch.object(setup, 'HOME_DIR', Path(d)), patch.object(setup.getpass, 'getpass') as prompt, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(setup.read_credentials(state, key, SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid())), (ID, key))
                prompt.assert_not_called()
            self.assertEqual(key.read_text(), 'test-sentinel')

    def test_existing_setup_requires_no_terminal_or_login(self):
        with tempfile.TemporaryDirectory() as d:
            key = Path(d)/'key'; key.write_text('test-only-sentinel'); key.chmod(0o600)
            state = Path(d)/'state'; state.write_text(json.dumps({'tunnel_id': ID, 'key_file': str(key)}))
            with patch.object(setup.getpass, 'getpass') as prompt:
                self.assertEqual(setup.read_credentials(state, key, None), (ID, key))
                prompt.assert_not_called()

    def test_empty_tunnel_id_skips_without_creating_state_or_key(self):
        with tempfile.TemporaryDirectory() as d, patch.object(setup, 'HOME_DIR', Path(d)), \
             patch('builtins.open', side_effect=[io.StringIO('\n'), io.StringIO()]), \
             patch.object(setup.getpass, 'getpass') as prompt:
            self.assertIsNone(setup.read_credentials(Path(d)/'state', Path(d)/'key', None))
            self.assertEqual(list(Path(d).iterdir()), [])
            prompt.assert_not_called()

    def test_original_manual_credentials_adopted_without_copy_or_prompt(self):
        with tempfile.TemporaryDirectory() as d, patch.object(setup, 'HOME_DIR', Path(d)):
            legacy = Path(d)/'.config/codex-ssh'; legacy.mkdir(parents=True)
            (legacy/'tunnel-id').write_text(ID+'\n')
            key = legacy/'runtime-api-key'; key.write_text('test-only-sentinel'); key.chmod(0o600)
            state = Path(d)/'state'
            with patch.object(setup.getpass, 'getpass') as prompt, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(setup.read_credentials(state, Path(d)/'unused-key', SimpleNamespace(pw_uid=os.getuid(),pw_gid=os.getgid())), (ID,key))
                prompt.assert_not_called()
            self.assertEqual(json.loads(state.read_text())['key_file'], str(key))
            self.assertFalse((Path(d)/'unused-key').exists())

    def test_not_ready_timeout_remains_not_ready(self):
        with patch.object(service, 'status', return_value=dict(process_running=True, healthy=True, ready=False)):
            self.assertFalse(setup.is_ready(service.wait_ready(seconds=0)))

    def terminal_run(self, action):
        # A real controlling PTY with the Python program supplied through stdin,
        # matching curl | bash: credentials cannot be read from script stdin.
        with tempfile.TemporaryDirectory() as d:
            key, state = Path(d)/'key', Path(d)/'state'
            code = f'''import sys; sys.path.insert(0, {str(ROOT/'scripts')!r})
import importlib.util, os
from pathlib import Path
from types import SimpleNamespace
spec=importlib.util.spec_from_file_location('setup', {str(ROOT/'scripts/configure-tunnel.py')!r})
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.HOME_DIR=Path({d!r})
try:
 m.read_credentials(Path({str(state)!r}), Path({str(key)!r}), SimpleNamespace(pw_uid=os.getuid(),pw_gid=os.getgid()))
except (KeyboardInterrupt, EOFError, ValueError):
 print('CANCELLED')
'''
            pid, master = pty.fork()
            if pid == 0:
                read_fd, write_fd = os.pipe()
                os.write(write_fd, code.encode()); os.close(write_fd)
                os.dup2(read_fd, 0); os.close(read_fd)
                os.execv(sys.executable, [sys.executable, '-'])
            output = b''
            deadline = time.monotonic()+8
            stage = 0
            try:
                while time.monotonic() < deadline:
                    if select.select([master], [], [], .1)[0]:
                        try: chunk = os.read(master, 4096)
                        except OSError: break
                        if not chunk: break
                        output += chunk
                    if stage == 0 and b'Tunnel ID' in output:
                        os.write(master, (ID+'\n').encode()); stage = 1
                    if stage == 1 and b'Runtime API key (hidden)' in output:
                        os.write(master, action); stage = 2
                else:
                    os.kill(pid, signal.SIGKILL)
                    self.fail('TTY interaction timed out')
                os.waitpid(pid, 0)
            finally:
                os.close(master)
            return output, key.exists(), state.exists()

    def test_hidden_key_when_script_is_piped_through_stdin(self):
        output, key, state = self.terminal_run(b'test-pty-sentinel\n')
        self.assertNotIn(b'test-pty-sentinel', output)
        self.assertIn(b'TUNNEL_CREDENTIALS_READY', output)
        self.assertTrue(key and state)

    def test_terminal_cancellation_and_empty_key_leave_no_credentials(self):
        for action in (b'\x03', b'\n'):
            with self.subTest(action=action):
                output, key, state = self.terminal_run(action)
                self.assertIn(b'CANCELLED', output)
                self.assertFalse(key or state)


if __name__ == '__main__': unittest.main()
