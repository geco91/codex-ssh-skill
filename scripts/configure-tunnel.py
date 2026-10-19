#!/usr/bin/env python3
"""Guide local tunnel setup with a persistent systemd foreground runtime."""
import argparse
import getpass
import fcntl
import json
import os
from pathlib import Path
import pwd
import re
import subprocess
import sys
import warnings
import tunnel_service as service

TUNNELS_URL = "https://platform.openai.com/settings/organization/tunnels"
KEYS_URL = "https://platform.openai.com/settings/organization/api-keys"
HOME_DIR = Path("/var/lib/codex-test")
CONFIG_DIR = HOME_DIR / ".config/codex-ssh/guided"
CLIENT = "/opt/codex-ssh/tunnel-client"
MCP = str(HOME_DIR / "mcp/bin/ssh-mcp")
ALIAS = "codex-ssh-guided"


def validate_tunnel_id(value):
    if not re.fullmatch(r"tunnel_(?:[a-z0-9]{4}_)?[a-z0-9]{32}", value):
        raise ValueError("Paste the complete tunnel ID from Platform tunnel settings")
    return value


def private_file(path, value, uid, gid):
    # Exclusive creation also rejects symlinks and preserves existing credentials.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(value)
        f.flush()
        os.fsync(f.fileno())
        os.fchown(f.fileno(), uid, gid)


def is_ready(status):
    return all(status.get(k) is True for k in ("process_running", "healthy", "ready"))


def client_call(arguments, log_dir=CONFIG_DIR):
    # runuser establishes the service account's HOME and SSH config on this host.
    result = subprocess.run(["runuser", "-u", "codex-test", "--", CLIENT, *arguments],
                            cwd=HOME_DIR, capture_output=True, text=True, timeout=60)
    # Do not echo arbitrary client output, metadata, IDs or secret-bearing diagnostics.
    log = log_dir / "last-client-output.log"
    fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(f"Client command completed with exit code {result.returncode}. Raw output is intentionally not stored.\n")
    if result.returncode:
        raise RuntimeError(f"tunnel-client exited {result.returncode}; inspect the private local log at {log}")
    return json.loads(result.stdout) if "--json" in arguments else {}


def read_credentials(state_file, key_file, account):
    if state_file.exists():
        state = json.loads(state_file.read_text())
        tunnel_id = validate_tunnel_id(state["tunnel_id"])
        key_file = Path(state.get("key_file", key_file))
        service.private_reference(key_file)
        return tunnel_id, key_file
    # Adopt the original manual installation's files without copying or rotating keys.
    legacy = HOME_DIR / ".config/codex-ssh"
    if (legacy / "tunnel-id").is_file() and (legacy / "runtime-api-key").is_file():
        tunnel_id = validate_tunnel_id((legacy / "tunnel-id").read_text().strip())
        key_file = legacy / "runtime-api-key"
        service.private_reference(key_file)
    else:
        # Separate streams: a buffered r+ terminal can fail with Illegal seek.
        with open("/dev/tty", "r", encoding="utf-8") as reader, open("/dev/tty", "w", encoding="utf-8") as writer:
            writer.write("Tunnel ID (Enter to finish setup later): "); writer.flush()
            entered = reader.readline()
            if not entered or not entered.strip():
                return None
            tunnel_id = validate_tunnel_id(entered.strip())
            if not key_file.exists():
                with warnings.catch_warnings():
                    warnings.simplefilter("error", getpass.GetPassWarning)
                    key = getpass.getpass("Runtime API key (hidden): ", stream=writer).strip()
                if not key or any(c.isspace() for c in key):
                    raise ValueError("The runtime key must be nonempty and contain no whitespace")
                private_file(key_file, key + "\n", account.pw_uid, account.pw_gid)
                del key
            # If interrupted after writing the key, preserve and reuse that file.
            service.private_reference(key_file)
    private_file(state_file, json.dumps({"tunnel_id": tunnel_id, "alias": ALIAS,
                                        "key_file": str(key_file)}) + "\n",
                 account.pw_uid, account.pw_gid)
    print("TUNNEL_CREDENTIALS_READY (existing credentials preserved)")
    return tunnel_id, key_file


def configure(account):
    service.preflight()
    credential_paths = [CONFIG_DIR / "setup-state.json", CONFIG_DIR / "runtime-key"]
    if any(p.is_symlink() for p in credential_paths):
        raise RuntimeError("Refusing symlinked setup state or credentials")
    credentials = read_credentials(*credential_paths, account)
    if credentials is None:
        print("Local SSH setup is ready; tunnel configuration skipped.")
        return None
    tunnel_id, key_file = credentials
    candidates = service.native_candidates(client_call(["runtimes", "list", "--json"]), tunnel_id)
    for _, native_profile in candidates:
        service.profile_for(tunnel_id, key_file, native_profile)
    existing = service.load_profile(service.PROFILE) if service.PROFILE.exists() else (candidates[0][1] if candidates else None)
    config = service.profile_for(tunnel_id, key_file, existing)
    # Validate profile conflicts before stopping the previous native supervisor.
    if service.PROFILE.exists() and config != existing:
        raise RuntimeError("Existing service profile differs; preserve and resolve locally")
    service.stop_native(candidates, client_call)
    own_pid = int(service.systemctl("show", service.UNIT_NAME, "--property=MainPID", "--value", check=False) or '0')
    service.check_processes(account.pw_uid, own_pid)
    service.install(config, account.pw_gid)
    return service.wait_ready()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true", help="Noninteractive service readiness check")
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Run on the local Debian/Proxmox host as root")
    if args.status:
        status = service.status()
    else:
        # One setup process at a time, including across curl-to-shell invocations.
        fd = os.open("/run/lock/codex-ssh-setup.lock", os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError("Another tunnel setup is running; wait for it to finish") from None
            account = pwd.getpwnam("codex-test")
            for parent in [HOME_DIR / ".config", HOME_DIR / ".config/codex-ssh", CONFIG_DIR]:
                if parent.is_symlink():
                    raise RuntimeError("Refusing a symlinked configuration directory")
                parent.mkdir(mode=0o700, exist_ok=True)
                os.chown(parent, account.pw_uid, account.pw_gid)
                os.chmod(parent, 0o700)
            print("Tunnel setup: attach an existing tunnel and enable startup after boot.")
            print("Tunnel settings: " + TUNNELS_URL)
            print("Restricted runtime key (Tunnels Read + Use): " + KEYS_URL)
            status = configure(account)
            if status is None:
                return
    print("Runtime status: " + json.dumps(status))
    if not is_ready(status):
        raise RuntimeError("Runtime not yet confirmed ready; inspect systemctl status and journalctl locally")
    print("Local runtime is running, healthy and ready. Product discovery is still a separate check.")
    print("systemd starts it after boot and supervises recovery; no interactive login is required.")
    print("Next: select this tunnel in your product's MCP connection and enable $codex-ssh.")
    print("Verify the assigned host identity before making changes.")


if __name__ == "__main__":
    os.umask(0o077)
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        print("Setup stopped: " + (str(error) or "interrupted") + ". Existing state is preserved.", file=sys.stderr)
        sys.exit(1)
