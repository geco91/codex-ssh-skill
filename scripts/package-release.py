#!/usr/bin/env python3
"""Build deterministic versioned downloads and their standalone HTTPS launcher."""
import argparse
import gzip
import hashlib
import io
from pathlib import Path
import re
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EPOCH = 1792368000  # 2026-10-19 00:00:00 UTC; fixed archive metadata.
INSTALLER_FILES = ['dependencies.lock.json', 'scripts/bootstrap-debian.sh',
                   'scripts/setup.sh', 'scripts/configure-tunnel.py', 'scripts/tunnel_service.py', 'scripts/check-upstreams.py']
LAUNCHER = '''#!/usr/bin/env bash
# Versioned Codex SSH installer. Run on your local Debian/Proxmox host.
set -Eeuo pipefail
set +x
umask 077
if [[ ${1:-} == --help || ${1:-} == -h ]]; then
  printf 'Codex SSH @VERSION@\\nUsage: install.sh [--local-only] [--proxmox-admin]\\nRun as root on the local host. Tunnel credentials are entered in a hidden local prompt.\\n'
  exit 0
fi
[[ $EUID -eq 0 ]] || { printf 'Run as root on the intended local Debian/Proxmox host.\\n' >&2; exit 1; }
for tool in curl tar sha256sum mktemp; do
  command -v "$tool" >/dev/null || { printf 'Required tool missing: %s\\n' "$tool" >&2; exit 1; }
done
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
curl --proto '=https' --tlsv1.2 -fSL --connect-timeout 15 --max-time 120 \\
  'https://raw.githubusercontent.com/geco91/codex-ssh-skill/v@VERSION@/downloads/v@VERSION@/installer.tar.gz' \\
  -o "$stage/installer.tar.gz"
printf '%s  %s\\n' '@SHA256@' "$stage/installer.tar.gz" | sha256sum -c - \\
  || { printf 'Installer checksum mismatch; refusing execution.\\n' >&2; exit 1; }
tar -xzf "$stage/installer.tar.gz" -C "$stage" --no-same-owner --no-same-permissions
bash "$stage/codex-ssh-installer/scripts/setup.sh" "$@"
'''


def build(version):
    skill = ROOT / '.agents/skills/codex-ssh'
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, 'w', zipfile.ZIP_DEFLATED) as archive:
        files = [(str(Path('codex-ssh') / f.relative_to(skill)), f.read_bytes())
                 for f in sorted(skill.rglob('*')) if f.is_file()]
        files.append(('codex-ssh/LICENSE', (ROOT/'LICENSE').read_bytes()))
        for name, contents in files:
            info = zipfile.ZipInfo(name, (2026, 10, 19, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, contents)
    tar_bytes = io.BytesIO()
    with gzip.GzipFile(fileobj=tar_bytes, mode='wb', filename='', mtime=EPOCH) as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as archive:
            for name in INSTALLER_FILES:
                data = (ROOT/name).read_bytes()
                info = tarfile.TarInfo('codex-ssh-installer/' + name)
                info.size, info.mode, info.mtime = len(data), 0o644, EPOCH
                archive.addfile(info, io.BytesIO(data))
    outputs = {'codex-ssh.zip': zip_bytes.getvalue(), 'installer.tar.gz': tar_bytes.getvalue()}
    outputs['SHA256SUMS'] = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n'
                                    for name, data in outputs.items()).encode()
    launcher = LAUNCHER.replace('@VERSION@', version).replace('@SHA256@', hashlib.sha256(outputs['installer.tar.gz']).hexdigest()).encode()
    return outputs, launcher


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True)
    parser.add_argument('--check', action='store_true', help='Verify published files against current source without writing')
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', args.version):
        parser.error('Use a numeric semantic version, e.g. 0.2.0')
    outputs, launcher = build(args.version)
    destination = ROOT / 'downloads' / ('v' + args.version)
    expected = {destination/name: data for name, data in outputs.items()}
    expected[ROOT/'scripts/install.sh'] = launcher
    for path, data in expected.items():
        if args.check:
            if not path.is_file() or path.read_bytes() != data:
                raise SystemExit('Release/source mismatch: ' + str(path.relative_to(ROOT)))
        elif path.exists() and path.read_bytes() != data and path.parent == destination:
            raise SystemExit('Refusing to rewrite versioned download; choose a new version: ' + str(path))
    if not args.check:
        destination.mkdir(parents=True, exist_ok=True)
        for path, data in expected.items(): path.write_bytes(data)
    print(('Verified' if args.check else 'Built') + ' release ' + args.version)


if __name__ == '__main__': main()
