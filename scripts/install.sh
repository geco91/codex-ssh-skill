#!/usr/bin/env bash
# Versioned Codex SSH installer. Run on your local Debian/Proxmox host.
set -Eeuo pipefail
set +x
umask 077
if [[ ${1:-} == --help || ${1:-} == -h ]]; then
  printf 'Codex SSH 0.3.0\nUsage: install.sh [--local-only] [--proxmox-admin]\nRun as root on the local host. Tunnel credentials are entered in a hidden local prompt.\n'
  exit 0
fi
[[ $EUID -eq 0 ]] || { printf 'Run as root on the intended local Debian/Proxmox host.\n' >&2; exit 1; }
for tool in curl tar sha256sum mktemp; do
  command -v "$tool" >/dev/null || { printf 'Required tool missing: %s\n' "$tool" >&2; exit 1; }
done
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
curl --proto '=https' --tlsv1.2 -fSL --connect-timeout 15 --max-time 120 \
  'https://raw.githubusercontent.com/geco91/codex-ssh-skill/v0.3.0/downloads/v0.3.0/installer.tar.gz' \
  -o "$stage/installer.tar.gz"
printf '%s  %s\n' 'a6aef531897db0aef5b9b58097f43ced2aa344e5c4236726ede34b884e8cbda1' "$stage/installer.tar.gz" | sha256sum -c - \
  || { printf 'Installer checksum mismatch; refusing execution.\n' >&2; exit 1; }
tar -xzf "$stage/installer.tar.gz" -C "$stage" --no-same-owner --no-same-permissions
bash "$stage/codex-ssh-installer/scripts/setup.sh" "$@"
