"""Small systemd integration for the pinned upstream foreground tunnel client."""
import copy
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

UNIT_NAME = 'codex-ssh-tunnel.service'
UNIT_PATH = Path('/etc/systemd/system') / UNIT_NAME
PROFILE = Path('/etc/codex-ssh-tunnel.json')
HEALTH_FILE = Path('/run/codex-ssh-tunnel/health-url')
HOME = Path('/var/lib/codex-test')
CLIENT = '/opt/codex-ssh/tunnel-client'
MCP = str(HOME / 'mcp/bin/ssh-mcp')
ALIASES = {'codex-ssh-guided', 'codex-test-proxmox'}
UNIT = '''# Managed by codex-ssh-skill v0.3; edit via the installer, not in place.
[Unit]
Description=Codex SSH Secure MCP Tunnel
Wants=network-online.target
After=network-online.target codex-ssh-loopback.service
Requires=codex-ssh-loopback.service
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User=codex-test
Group=codex-test
WorkingDirectory=/var/lib/codex-test
Environment=HOME=/var/lib/codex-test
Environment=PATH=/opt/codex-ssh:/usr/local/bin:/usr/bin:/bin
UMask=0077
RuntimeDirectory=codex-ssh-tunnel
RuntimeDirectoryMode=0700
ExecStart=/opt/codex-ssh/tunnel-client run --config /etc/codex-ssh-tunnel.json
Restart=always
RestartSec=5
TimeoutStartSec=45
TimeoutStopSec=20
KillMode=control-group
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
'''


def systemctl(*args, check=True):
    result = subprocess.run(['systemctl', *args], capture_output=True, text=True, timeout=50)
    if check and result.returncode:
        raise RuntimeError('systemctl ' + args[0] + ' failed; inspect the unit locally with journalctl')
    return result.stdout.strip()


def preflight():
    # Never replace an administrator's unit, vendor unit, or drop-ins.
    for directory in ('/etc/systemd/system', '/run/systemd/system', '/usr/lib/systemd/system', '/lib/systemd/system', '/run/systemd/transient'):
        p = Path(directory) / UNIT_NAME
        if p.exists() or p.is_symlink():
            if p != UNIT_PATH or p.is_symlink() or p.read_text() != UNIT:
                raise RuntimeError('Conflicting tunnel service definition; preserve it and resolve locally first')
        dropins = Path(directory) / (UNIT_NAME + '.d')
        if dropins.exists() and any(dropins.iterdir()):
            raise RuntimeError('Tunnel service drop-ins exist; preserve them and resolve locally first')
    if not Path('/run/systemd/system').is_dir():
        raise RuntimeError('A running systemd host is required; local-only setup remains available')


def private_reference(path):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise RuntimeError('Runtime key must reference an existing regular protected file')
    if path.stat().st_mode & 0o077:
        raise RuntimeError('Runtime key file must have mode 0600 or stricter')
    content = path.read_bytes().strip()
    if not content or any(c in b' \t\r\n\v\f' for c in content):
        raise RuntimeError('Runtime key file is empty or contains whitespace; preserve and repair locally')
    return 'file:' + str(path)


def profile_for(tunnel_id, key_file, existing=None):
    config = copy.deepcopy(existing) if existing is not None else {'config_version': 1}
    control = config.setdefault('control_plane', {})
    if control.get('tunnel_id', tunnel_id) != tunnel_id:
        raise RuntimeError('Existing profile belongs to another tunnel')
    control.setdefault('base_url', 'https://api.openai.com')
    reference = private_reference(key_file)
    if control.get('api_key', reference) != reference:
        raise RuntimeError('Existing profile key reference differs; resolve locally without replacing credentials')
    control.update(tunnel_id=tunnel_id, api_key=reference)
    expected = [{'channel': 'main', 'command': MCP}]
    if config.get('mcp', {'commands': expected}) != {'commands': expected}:
        raise RuntimeError('Existing profile has a different MCP command; manual migration required')
    config['mcp'] = {'commands': expected}
    config['health'] = {'listen_addr': '127.0.0.1:0', 'url_file': str(HEALTH_FILE)}
    config['log'] = {'level': 'info', 'format': 'json'}
    config['admin_ui'] = {'open_browser': False}
    # Do not inherit native supervisor PID/log files into systemd supervision.
    config.pop('pid', None)
    return config


def load_profile(path):
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError('Refusing symlinked tunnel profile')
    try:
        value = json.loads(path.read_text())
    except (ValueError, OSError):
        raise RuntimeError('Profile is not readable JSON; preserve it and migrate manually') from None
    if not isinstance(value, dict):
        raise RuntimeError('Invalid existing profile; manual migration required')
    return value


def native_candidates(aliases, tunnel_id):
    candidates = []
    for alias in aliases.get('aliases', []):
        # Same tunnel under another name is a conflict, not permission to stop it.
        if alias.get('tunnel_id') != tunnel_id:
            if alias.get('alias') in ALIASES:
                raise RuntimeError('Known runtime alias belongs to another tunnel; resolve locally first')
            continue
        if alias.get('alias') not in ALIASES:
            raise RuntimeError('This tunnel has a runtime outside this setup; stop/migrate it explicitly first')
        profile_path = alias.get('config_path') or alias.get('profile_path')
        if not profile_path:
            raise RuntimeError('Native runtime profile path is missing; manual migration required')
        config = load_profile(profile_path)
        candidates.append((alias['alias'], config))
    if len(candidates) > 1:
        raise RuntimeError('Multiple native runtimes reference this tunnel; resolve locally before migrating')
    return candidates


def stop_native(candidates, client_call):
    for alias, _ in candidates:
        status = client_call(['runtimes', 'status', alias, '--json'])
        if status.get('process_running') is True:
            client_call(['runtimes', 'stop', alias, '--json'])
        status = client_call(['runtimes', 'status', alias, '--json'])
        if status.get('process_running') is not False:
            raise RuntimeError('Native runtime stop is not confirmed; refusing a second supervisor')


def check_processes(uid, own_pid=0):
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name) == own_pid:
            continue
        try:
            if process.stat().st_uid != uid:
                continue
            args = (process / 'cmdline').read_bytes().split(b'\0')
            if args and Path(os.fsdecode(args[0])).name == 'tunnel-client' and b'run' in args[1:]:
                raise RuntimeError('Another tunnel client is running; inspect locally before starting a service')
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue


def install(config, gid):
    data = json.dumps(config, indent=2) + '\n'
    PROFILE.parent.mkdir(mode=0o750, exist_ok=True)
    if PROFILE.exists() or PROFILE.is_symlink():
        if PROFILE.is_symlink() or load_profile(PROFILE) != config:
            raise RuntimeError('Existing service profile differs; preserved for manual review')
    else:
        fd = os.open(PROFILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
        with os.fdopen(fd, 'w') as f:
            f.write(data)
            os.fchown(f.fileno(), 0, gid)
            os.fchmod(f.fileno(), 0o640)
    if not UNIT_PATH.exists():
        fd = os.open(UNIT_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, 'w') as f:
            f.write(UNIT)
            os.fchmod(f.fileno(), 0o644)
    systemctl('daemon-reload')
    # start is idempotent and does not restart a healthy existing process.
    systemctl('enable', '--now', UNIT_NAME)


def status():
    fields = systemctl('show', UNIT_NAME, '--property=ActiveState,SubState,MainPID,UnitFileState', check=False)
    values = dict(line.split('=', 1) for line in fields.splitlines() if '=' in line)
    result = dict(process_running=values.get('ActiveState') == 'active' and int(values.get('MainPID', '0')) > 0,
                  healthy=False, ready=False, enabled=values.get('UnitFileState') == 'enabled')
    if result['process_running'] and HEALTH_FILE.is_file():
        base = HEALTH_FILE.read_text().strip()
        parsed = urlsplit(base)
        if parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port or parsed.path not in ('', '/') or parsed.query or parsed.fragment or parsed.username:
            raise RuntimeError('Unexpected health URL; refusing to query it')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for flag, endpoint in [('healthy', '/healthz'), ('ready', '/readyz')]:
            try:
                with opener.open(base.rstrip('/') + endpoint, timeout=2) as response:
                    result[flag] = response.status == 200
            except (OSError, urllib.error.URLError):
                pass
    return result


def wait_ready(seconds=30):
    deadline = time.monotonic() + seconds
    while True:
        value = status()
        if all(value.get(k) is True for k in ('process_running', 'healthy', 'ready')) or time.monotonic() >= deadline:
            return value
        time.sleep(1)
