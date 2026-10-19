"""Local setup regression tests: no services, package installation or remote calls."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
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

    def run_wizard(self, directory, *, resume=False, ready=True):
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
             patch.object(setup.getpass, 'getpass', return_value=private_sentinel) as prompt, \
             patch('sys.argv', ['configure-tunnel.py']), contextlib.redirect_stdout(io.StringIO()) as output:
            setup.main()
            if resume: prompt.assert_not_called()
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



class ReleaseBundleTests(unittest.TestCase):
    def test_installer_bundle_and_launcher_reject_stale_source(self):
        import tarfile
        packaging = module('release_packaging', 'package-release.py')
        outputs, launcher = packaging.build('0.2.0')
        self.assertIn(hashlib.sha256(outputs['installer.tar.gz']).hexdigest().encode(), launcher)
        with tarfile.open(fileobj=io.BytesIO(outputs['installer.tar.gz']), mode='r:gz') as archive:
            for name in packaging.INSTALLER_FILES:
                self.assertEqual(archive.extractfile('codex-ssh-installer/' + name).read(), (ROOT/name).read_bytes())
            self.assertTrue(all(not x.name.startswith('/') and '..' not in Path(x.name).parts for x in archive))
        self.assertEqual(outputs, packaging.build('0.2.0')[0])

    def test_skill_bundle_includes_english_entry_and_icon(self):
        import zipfile
        packaging = module('release_packaging_icon', 'package-release.py')
        with zipfile.ZipFile(io.BytesIO(packaging.build('0.2.0')[0]['codex-ssh.zip'])) as archive:
            self.assertIn('codex-ssh/assets/icon.png', archive.namelist())
            self.assertIn(b'Use an existing SSH-MCP connection', archive.read('codex-ssh/SKILL.md'))
            self.assertIn('codex-ssh/LICENSE', archive.namelist())


if __name__ == "__main__": unittest.main()
