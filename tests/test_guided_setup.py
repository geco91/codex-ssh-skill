"""Local setup regression tests: no services, package installation or remote calls."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import pty
import select
import signal
import sys
import time
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


setup = module('guided_setup', 'configure-tunnel.py')
upstream = module('upstream_check', 'check-upstreams.py')
TUNNEL_ID = 'tunnel_' + 'a' * 32


class GuidedSetupTests(unittest.TestCase):
    def test_invalid_tunnel_ids_do_not_become_remote_targets(self):
        self.assertEqual(setup.validate_tunnel_id(TUNNEL_ID), TUNNEL_ID)
        self.assertEqual(setup.validate_tunnel_id('tunnel_ab12_' + 'b' * 32), 'tunnel_ab12_' + 'b' * 32)
        for value in ['', 'tunnel_short', TUNNEL_ID + '\n--other', 'https://example.invalid', 'tunnel_' + 'A' * 32]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                setup.validate_tunnel_id(value)

    def test_private_key_file_permissions_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'key'
            setup.private_file(p, 'test-only-sentinel\n', os.getuid(), os.getgid())
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                setup.private_file(p, 'replacement', os.getuid(), os.getgid())
            self.assertEqual(p.read_text(), 'test-only-sentinel\n')
            link = Path(d) / 'link'
            link.symlink_to(p)
            with self.assertRaises(FileExistsError):
                setup.private_file(link, 'replacement', os.getuid(), os.getgid())

    def test_native_runtime_uses_secret_reference_and_assigned_mcp_command(self):
        args = setup.connect_args(TUNNEL_ID, Path('/private/runtime-key'))
        self.assertEqual(args[args.index('--runtime-api-key') + 1], 'file:/private/runtime-key')
        self.assertEqual(args[args.index('--mcp-command') + 1], setup.MCP)
        self.assertNotIn('--admin-key', args)

    def test_readiness_requires_all_three_real_booleans(self):
        self.assertTrue(setup.is_ready(dict(process_running=True, healthy=True, ready=True)))
        for status in [{}, {'healthy': True, 'ready': True},
                       dict(process_running=True, healthy=False, ready=True),
                       dict(process_running='true', healthy=True, ready=True)]:
            self.assertFalse(setup.is_ready(status))

    def test_existing_unrelated_alias_is_preserved(self):
        aliases = {'aliases': [{'alias': setup.ALIAS, 'tunnel_id': TUNNEL_ID}]}
        with self.assertRaises(RuntimeError): setup.check_available(aliases)
        with self.assertRaises(RuntimeError): setup.check_available(aliases, 'tunnel_' + 'b' * 32)
        setup.check_available(aliases, TUNNEL_ID)

    def test_client_failure_keeps_details_private(self):
        fake = subprocess.CompletedProcess([], 7, 'test-only-private-output', 'diagnostic')
        with tempfile.TemporaryDirectory() as d, patch.object(setup.subprocess, 'run', return_value=fake):
            with self.assertRaises(RuntimeError) as error:
                setup.client_call(['runtimes', 'status', setup.ALIAS, '--json'], Path(d))
            self.assertNotIn('test-only-private-output', str(error.exception))
            self.assertEqual((Path(d)/'last-client-output.log').stat().st_mode & 0o777, 0o600)

    def run_wizard(self, directory, *, resume=False, ready=True, hidden_failure=False):
        home = Path(directory)
        config = home / '.config/codex-ssh/guided'
        commands = []
        private_sentinel = 'test-only-key-not-a-real-credential'
        tty = io.StringIO('yes\n' if resume else TUNNEL_ID + '\n')
        original_open = open
        def tty_open(path, *a, **kw):
            if path == '/dev/tty': return tty
            return original_open(path, *a, **kw)
        # A duplex terminal has independent input/output; StringIO does not.
        tty.write = lambda value: len(value)
        def fake_client(args):
            commands.append(args)
            if args[:2] == ['runtimes', 'list']:
                return {'aliases': [{'alias': setup.ALIAS, 'tunnel_id': TUNNEL_ID}]} if resume else {'aliases': []}
            if args[:2] == ['runtimes', 'status']:
                return dict(process_running=True, healthy=True, ready=ready)
            return {}
        with patch.object(setup, 'HOME_DIR', home), patch.object(setup, 'CONFIG_DIR', config), \
             patch.object(setup.os, 'geteuid', return_value=0), \
             patch.object(setup.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid())), \
             patch.object(setup, 'client_call', side_effect=fake_client), \
             patch('builtins.open', side_effect=tty_open), \
             patch.object(setup.getpass, 'getpass', side_effect=(lambda *a, **k: setup.warnings.warn('no echo control', setup.getpass.GetPassWarning)) if hidden_failure else None, return_value=private_sentinel) as prompt, \
             patch('sys.argv', ['configure-tunnel.py']), contextlib.redirect_stdout(io.StringIO()) as output:
            setup.main()
            if resume: prompt.assert_not_called()
        self.assertIn('SUCCESS: phase 2/3 complete', output.getvalue())
        self.assertIn('product connection NOT TESTED', output.getvalue())
        self.assertIn('does not configure tunnel autostart', output.getvalue())
        self.assertIn('choose reuse', output.getvalue())
        self.assertNotIn(private_sentinel, output.getvalue())
        self.assertNotIn(private_sentinel, json.dumps(commands))
        self.assertTrue((config/'runtime-key').read_text().startswith(private_sentinel))
        self.assertEqual((config/'runtime-key').stat().st_mode & 0o777, 0o600)
        self.assertEqual([x[:2] for x in commands], [['runtimes','list'], ['runtimes','connect'], ['doctor','--profile'], ['runtimes','status']])

    def test_new_and_resumed_setup_uses_same_credentials(self):
        with tempfile.TemporaryDirectory() as d:
            self.run_wizard(d)
            self.run_wizard(d, resume=True)

    def test_not_ready_runtime_is_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError, 'not yet confirmed ready'):
                self.run_wizard(d, ready=False)
            self.run_wizard(d, resume=True)

    def test_setup_reports_phase_failure_and_local_only_without_reinstall(self):
        for bootstrap_exit, tunnel_exit, local_only in ((1, 0, False), (0, 1, False), (0, 0, True), (0, 0, False)):
            with self.subTest(bootstrap=bootstrap_exit, tunnel=tunnel_exit, local_only=local_only), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                installed = root/'installed'; installed.mkdir()
                (installed/'installed').write_text('proxmox_admin=false\n')
                (installed/'README.txt').write_text('Persistent tunnel setup:\n')
                (installed/'configure-tunnel.py').write_text('raise SystemExit(' + str(tunnel_exit) + ')\n')
                (root/'bootstrap-debian.sh').write_text(
                    'detect_platform() { echo debian; }\n'
                    'if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then return 0; fi\n'
                    'exit ' + str(bootstrap_exit) + '\n')
                bindir=root/'bin'; bindir.mkdir()
                installer=bindir/'install'; installer.write_text('#!/bin/sh\nexit 0\n'); installer.chmod(0o700)
                script=(ROOT/'scripts/setup.sh').read_text().replace('/opt/codex-ssh', str(installed))
                script=script.replace('[[ $EUID -eq 0 ]]', 'true')
                wrapper=root/'setup.sh'; wrapper.write_text(script)
                result=subprocess.run(['bash', str(wrapper), *(['--local-only'] if local_only else [])],
                                      env={**os.environ, 'PATH': str(bindir)+os.pathsep+os.environ['PATH']},
                                      capture_output=True, text=True, timeout=5)
                output=result.stdout+result.stderr
                self.assertEqual(result.returncode, 1 if bootstrap_exit or tunnel_exit else 0, output)
                self.assertNotIn('No tunnel', output)
                if bootstrap_exit:
                    self.assertNotIn('SUCCESS', output)
                else:
                    self.assertIn('SUCCESS: phase 1/3', output)
                if tunnel_exit:
                    self.assertIn('phase 1 remains complete', output)
                    self.assertIn('resume: python3', output)
                    self.assertIn('product connection NOT TESTED', output)
                if local_only:
                    self.assertIn('tunnel setup skipped', output)
                    self.assertIn('product connection NOT TESTED', output)

    def test_fail_closed_input_does_not_save_credentials(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(setup.getpass.GetPassWarning):
                self.run_wizard(d, hidden_failure=True)
            config = Path(d)/'.config/codex-ssh/guided'
            self.assertFalse((config/'runtime-key').exists())
            self.assertFalse((config/'setup-state.json').exists())

    def test_interrupted_state_save_reuses_key_without_prompt(self):
        with tempfile.TemporaryDirectory() as d:
            self.run_wizard(d)
            config = Path(d)/'.config/codex-ssh/guided'
            original = (config/'runtime-key').stat().st_mtime_ns
            (config/'setup-state.json').unlink()
            # Fail if a second key is requested. Existing fixture must be reused.
            self.run_wizard(d, hidden_failure=True)
            self.assertEqual((config/'runtime-key').stat().st_mtime_ns, original)

    def test_invalid_saved_key_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'key'; path.write_text('inert-test-fixture'); path.chmod(0o644)
            with self.assertRaisesRegex(RuntimeError, '0600'):
                setup.check_key_reference(path)
            self.assertEqual(path.read_text(), 'inert-test-fixture')

    def test_corrupt_or_substituted_archive_is_rejected(self):
        expected = hashlib.sha256(b'expected upstream bytes').hexdigest()
        upstream.verify_stream(io.BytesIO(b'expected upstream bytes'), expected)
        with self.assertRaisesRegex(ValueError, 'upstream bytes changed'):
            upstream.verify_stream(io.BytesIO(b'replaced upstream bytes'), expected)

    def test_lock_requires_full_commit_and_https(self):
        lock = json.loads((ROOT/'dependencies.lock.json').read_text())
        for field, value in [('commit','main'), ('url','http://example.invalid/archive'), ('sha256','bad')]:
            altered = json.loads(json.dumps(lock))
            altered['ssh_mcp'][field] = value
            with tempfile.TemporaryDirectory() as d:
                p = Path(d)/'lock.json'; p.write_text(json.dumps(altered))
                with self.assertRaises(ValueError): upstream.load_lock(p)



    def terminal_run(self, action):
        # A real controlling PTY with the Python program supplied through stdin,
        # matching curl | bash: credentials cannot be read from script stdin.
        with tempfile.TemporaryDirectory() as d:
            config = Path(d)/'.config/codex-ssh/guided'
            key, state = config/'runtime-key', config/'setup-state.json'
            code = f'''import importlib.util, os, sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('setup', {str(ROOT/'scripts/configure-tunnel.py')!r})
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.HOME_DIR=Path({d!r}); m.CONFIG_DIR=Path({str(config)!r})
m.client_call=lambda args: dict(process_running=True, healthy=True, ready=True)
try:
 with patch.object(m.os, 'geteuid', return_value=0), patch.object(m.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid())):
  m.main()
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
                        os.write(master, (TUNNEL_ID+'\n').encode()); stage = 1
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
        self.assertIn(b'SUCCESS: phase 2/3 complete', output)
        self.assertTrue(key and state)

    def test_terminal_cancellation_and_empty_key_leave_no_credentials(self):
        for action in (b'\x03', b'\n'):
            with self.subTest(action=action):
                output, key, state = self.terminal_run(action)
                self.assertIn(b'CANCELLED', output)
                self.assertFalse(key or state)


class ReleaseBundleTests(unittest.TestCase):
    def test_installer_bundle_and_launcher_reject_stale_source(self):
        import tarfile
        packaging = module('release_packaging', 'package-release.py')
        outputs, launcher = packaging.build('0.2.1')
        self.assertIn(hashlib.sha256(outputs['installer.tar.gz']).hexdigest().encode(), launcher)
        with tarfile.open(fileobj=io.BytesIO(outputs['installer.tar.gz']), mode='r:gz') as archive:
            for name in packaging.INSTALLER_FILES:
                self.assertEqual(archive.extractfile('codex-ssh-installer/' + name).read(), (ROOT/name).read_bytes())
            self.assertTrue(all(not x.name.startswith('/') and '..' not in Path(x.name).parts for x in archive))
        self.assertEqual(outputs, packaging.build('0.2.1')[0])

    def test_skill_bundle_includes_english_entry_and_icon(self):
        import zipfile
        packaging = module('release_packaging_icon', 'package-release.py')
        with zipfile.ZipFile(io.BytesIO(packaging.build('0.2.1')[0]['codex-ssh.zip'])) as archive:
            self.assertIn('codex-ssh/assets/icon.png', archive.namelist())
            self.assertIn(b'Use an existing SSH-MCP connection', archive.read('codex-ssh/SKILL.md'))
            self.assertIn('codex-ssh/LICENSE', archive.namelist())


if __name__ == "__main__": unittest.main()
