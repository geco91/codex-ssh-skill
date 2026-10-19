"""Local checks only: no apt, service starts, root installation or network calls."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/bootstrap-debian.sh"
BASH = shutil.which("bash")


class BootstrapTests(unittest.TestCase):
    def detect(self, os_text, *, marker=False, commands=()):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            os_file = root / "os-release"
            os_file.write_text(os_text)
            bindir = root / "bin"
            bindir.mkdir()
            for name in commands:
                executable = bindir / name
                executable.write_text("#!/bin/sh\nexit 0\n")
                executable.chmod(0o700)
            marker_path = root / "pve"
            if marker:
                marker_path.mkdir()
            # Isolated PATH: host commands cannot accidentally supply a fixture.
            return subprocess.run(
                [BASH, "-c", 'source "$1"; detect_platform "$2" "$3"',
                 "test", str(SCRIPT), str(os_file), str(marker_path)],
                env={**os.environ, "PATH": str(bindir)},
                text=True, capture_output=True, timeout=5,
            )

    def test_plain_debian_12_and_13(self):
        for version in ("12", "13"):
            with self.subTest(version=version):
                result = self.detect(f'ID=debian\nVERSION_ID="{version}"\n')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), "debian")

    def test_proxmox_on_debian_12_and_13(self):
        for version in ("12", "13"):
            with self.subTest(version=version):
                result = self.detect(
                    f'ID=debian\nVERSION_ID="{version}"\n',
                    marker=True, commands=("pveversion", "qm"),
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), "proxmox")

    def test_partial_proxmox_never_falls_back_to_plain_debian(self):
        for marker, commands in ((True, ()), (False, ("pveversion", "qm")),
                                 (True, ("pveversion",))):
            with self.subTest(marker=marker, commands=commands):
                result = self.detect('ID=debian\nVERSION_ID="13"\n',
                                     marker=marker, commands=commands)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Incomplete Proxmox", result.stderr)
                self.assertNotIn("debian", result.stdout)

    def test_unsupported_os_stops(self):
        for contents in ('ID=ubuntu\nVERSION_ID="24.04"\n',
                         'ID=debian\nVERSION_ID="11"\n'):
            result = self.detect(contents)
            self.assertNotEqual(result.returncode, 0)

    def test_cli_rejects_invalid_combinations_before_installation(self):
        for arguments in (("--help",), ("--unknown",),
                          ("--check", "--proxmox-admin"),
                          ("--install", "--unexpected")):
            result = subprocess.run([BASH, str(SCRIPT), *arguments],
                                    text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0 if arguments == ("--help",) else 2)

    @unittest.skipUnless(shutil.which("sshd") and shutil.which("ssh-keygen"),
                         "OpenSSH server/keygen required for config validation")
    def test_effective_sshd_configuration_separates_admin_key_and_user(self):
        # Validate the actual generated configuration through OpenSSH, without
        # binding a listener or starting a server. Test keys stay in a tempdir.
        script = SCRIPT.read_text()
        initial = script.split('cat > "$conf/sshd_config" <<EOF\n', 1)[1].split("\nEOF", 1)[0]
        admin = script.split('cat >> "$conf/sshd_config" <<EOF\n', 1)[1].split("\nEOF", 1)[0]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "",
                            "-f", str(root / "host_ed25519")], check=True,
                           capture_output=True, timeout=10)
            for enabled in (False, True):
                config = initial + ("\n" + admin if enabled else "")
                for key, value in {"$conf": directory, "$ssh_port": "22222",
                                   "$account_home": directory + "/user",
                                   "$account": "codex-test"}.items():
                    config = config.replace(key, value)
                config_path = root / "sshd_config"
                config_path.write_text(config + "\n")
                for user in ("root", "codex-test"):
                    with self.subTest(admin=enabled, user=user):
                        result = subprocess.run(
                            [shutil.which("sshd"), "-T", "-f", str(config_path),
                             "-C", f"user={user},host=localhost,addr=127.0.0.1"],
                            capture_output=True, text=True, timeout=10,
                        )
                        self.assertEqual(result.returncode, 0, result.stderr)
                        settings = dict(line.split(" ", 1)
                                        for line in result.stdout.splitlines() if " " in line)
                        self.assertEqual(settings["listenaddress"], "127.0.0.1:22222")
                        self.assertEqual(settings["disableforwarding"], "yes")
                        if enabled and user == "root":
                            self.assertIn(settings["permitrootlogin"], ("without-password", "prohibit-password"))
                            self.assertEqual(settings["allowusers"], "root")
                            self.assertEqual(settings["authorizedkeysfile"],
                                             directory + "/proxmox-admin-authorized_keys")
                        else:
                            self.assertEqual(settings["permitrootlogin"], "no")
                            self.assertEqual(settings["allowusers"], "codex-test")


if __name__ == "__main__":
    unittest.main()
