#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Run on the intended Debian test machine or test Proxmox, not the cloud worker.
set -Eeuo pipefail
umask 077

usage() {
  cat <<'EOF'
Usage: bash bootstrap-debian.sh [--dry-run | --install | --check | --help] [--proxmox-admin]
Default: --dry-run (no changes, no downloads).
--install: root, Debian 12/13, systemd; installs packages and pinned upstreams,
creates codex-test without sudo, starts a separate loopback-only OpenSSH service.
Automatically detects plain Debian or Proxmox. Existing Proxmox SSH stays intact.
--proxmox-admin: only with --install on Proxmox; grants the MCP account FULL HOST
ROOT via a separate loopback SSH key/alias for qm/pvesm/VM provisioning.
Without this opt-in, Proxmox VM administration needs separately supplied rights.
Does not create/start a tunnel, request credentials, or expose public ports.
Reserved paths: /opt/codex-ssh, /etc/codex-ssh, /var/lib/codex-test,
/etc/systemd/system/codex-ssh-loopback.service. No VMs are created by bootstrap.
EOF
}
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

detect_platform() {
  local os_file=${1:-/etc/os-release} pve_dir=${2:-/etc/pve}
  local ID='' VERSION_ID=''
  [[ -r "$os_file" ]] || die 'Missing OS information.'
  # shellcheck source=/dev/null
  . "$os_file"
  [[ "$ID" == debian && "$VERSION_ID" =~ ^(12|13)$ ]] || die 'Only Debian 12/13 supported.'
  if [[ -d "$pve_dir" ]] || command -v pveversion >/dev/null; then
    if [[ ! -d "$pve_dir" ]] || ! command -v pveversion >/dev/null || ! command -v qm >/dev/null; then
      die 'Incomplete Proxmox environment; no plain Debian fallback.'
    fi
    printf 'proxmox\n'
  else
    printf 'debian\n'
  fi
}

base=/opt/codex-ssh
conf=/etc/codex-ssh
account=codex-test
account_home=/var/lib/codex-test
unit=/etc/systemd/system/codex-ssh-loopback.service
ssh_port=22222

check_local() {
  [[ -f "$base/installed" ]] || die 'Installation incomplete or missing; inspect reserved paths before retrying.'
  systemctl is-active --quiet codex-ssh-loopback.service || die 'Loopback SSH service is not active.'
  # Expansion is intentionally performed by the remote shell, not this shell.
  # shellcheck disable=SC2016
  runuser -u "$account" -- ssh -F "$account_home/.ssh/config" codex-test-local \
    'test "$(id -un)" = codex-test && printf "loopback-ssh-ok\n"' || die 'Local SSH self-check failed.'
  runuser -u "$account" -- "$base/tunnel-client" --version
  if grep -qx 'proxmox_admin=true' "$base/installed"; then
    # shellcheck disable=SC2016
    runuser -u "$account" -- ssh -F "$account_home/.ssh/config" codex-proxmox-host \
      'test "$(id -u)" = 0 && pveversion' || die 'Proxmox admin self-check failed.'
  fi
  printf 'Local SSH self-check passed. Tunnel and Codex connection remain UNTESTED.\n'
}

# Allow local tests to source detection without executing installation logic.
if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then return 0; fi
mode=${1:---dry-run}
proxmox_admin=false
[[ $# -le 2 ]] || { usage >&2; exit 2; }
if [[ $# -eq 2 ]]; then
  [[ "$mode" == --install && "$2" == --proxmox-admin ]] || { usage >&2; exit 2; }
  proxmox_admin=true
fi
case "$mode" in
  --help|-h) usage; exit 0 ;;
  --dry-run|--install|--check) ;;
  *) usage >&2; exit 2 ;;
esac
platform=$(detect_platform)
if [[ "$proxmox_admin" == true && "$platform" != proxmox ]]; then
  die '--proxmox-admin requires a verified Proxmox environment.'
fi
if [[ "$mode" == --dry-run ]]; then
  usage
  printf '\nDetected: %s. Plan: preflight -> missing apt packages -> pinned MCP/client -> private account/key -> loopback SSH -> local self-check.\n' "$platform"
  exit 0
fi
[[ $EUID -eq 0 ]] || die 'Run --install/--check as root on the intended machine console.'
[[ -d /run/systemd/system ]] || die 'A running systemd system is required.'
if [[ "$mode" == --check ]]; then check_local; exit 0; fi
if [[ -f "$base/installed" ]]; then
  grep -qx "platform=$platform" "$base/installed" || die 'Installation predates platform detection or platform changed; inspect manually.'
  grep -qx "proxmox_admin=$proxmox_admin" "$base/installed" || die 'Requested rights differ from installation; no silent rights changes.'
  check_local; exit 0
fi
if [[ "$platform" == proxmox ]]; then
  [[ "$proxmox_admin" == false ]] || printf 'Requested: FULL HOST ROOT via private codex-proxmox-host alias; tests must run in guests.\n'
  dpkg-query -W -f='${Status}' openssh-server 2>/dev/null | grep -qx 'install ok installed' || die 'Proxmox OpenSSH server missing; inspect host manually.'
  systemctl is-active --quiet ssh.service || die 'Existing Proxmox SSH service not active; inspect manually.'
fi
for path in "$base" "$conf" "$account_home" "$unit"; do
  [[ ! -e "$path" && ! -L "$path" ]] || die "Reserved path already exists: $path; no overwrite."
done
! getent passwd "$account" >/dev/null || die 'codex-test account already exists; no changes.'
! getent group "$account" >/dev/null || die 'codex-test group already exists; no changes.'
command -v ss >/dev/null || die 'ss (iproute2) required for the port preflight.'
[[ -z $(ss -H -ltn "sport = :$ssh_port") ]] || die 'Loopback port 22222 is already occupied.'
case "$(dpkg --print-architecture)" in
  amd64) arch=amd64; client_sha=d60cdba019bce451bcc3a15478cc5b9cb11270b049f5b56ea39a80b517f8b117 ;;
  arm64) arch=arm64; client_sha=963d0384aaa7c798778479c45673f9051a4039dd891aef8f8978d2a1a628b74f ;;
  *) die 'Only amd64 and arm64 release binaries supported.' ;;
esac

# Avoid Debian starting/enabling a public default SSH listener on fresh install.
# Never replace an existing service policy or change an existing SSH installation.
new_sshd=false
policy_created=false
stage=''
cleanup() {
  if [[ "$policy_created" == true ]]; then rm -f /usr/sbin/policy-rc.d; fi
  if [[ -n "$stage" ]]; then rm -rf -- "$stage"; fi
}
trap cleanup EXIT
trap 'printf "Bootstrap failed at line %s. No tunnel was started. Inspect partial installation; no automatic rollback.\n" "$LINENO" >&2' ERR
if ! dpkg-query -W -f='${Status}' openssh-server 2>/dev/null | grep -qx 'install ok installed'; then
  new_sshd=true
  [[ ! -e /usr/sbin/policy-rc.d && ! -L /usr/sbin/policy-rc.d ]] || die 'Existing service policy: install OpenSSH under your policy first, then retry.'
  for path in /etc/systemd/system/ssh.service /etc/systemd/system/ssh.socket /etc/systemd/system/sshd.service; do
    [[ ! -e "$path" && ! -L "$path" ]] || die "Existing SSH service customization: $path; inspect manually."
  done
  # Persistently prevent the new default listener, also after a failed install
  # or reboot. Existing OpenSSH installations never take this branch.
  systemctl mask ssh.service ssh.socket
  printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
  chmod 755 /usr/sbin/policy-rc.d
  policy_created=true
fi
export DEBIAN_FRONTEND=noninteractive
apt_options=()
if [[ -n ${CODEX_SSH_APT_SOURCES:-} ]]; then
  [[ "$CODEX_SSH_APT_SOURCES" == /* && -f "$CODEX_SSH_APT_SOURCES" && -r "$CODEX_SSH_APT_SOURCES" ]] || die 'CODEX_SSH_APT_SOURCES must name an existing readable absolute sources file.'
  apt_options=(-o "Dir::Etc::sourcelist=$CODEX_SSH_APT_SOURCES" -o 'Dir::Etc::sourceparts=-')
fi
packages=()
for package in ca-certificates curl openssl python3-venv openssh-client openssh-server; do
  if ! dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -qx 'install ok installed'; then
    packages+=("$package")
  fi
done
if [[ ${#packages[@]} -gt 0 ]]; then
  apt-get "${apt_options[@]}" update
  apt-get "${apt_options[@]}" install -y --no-upgrade --no-install-recommends "${packages[@]}"
fi
if [[ "$new_sshd" == true ]]; then
  # New units only: keep the distribution listener off, including after reboot.
  systemctl disable --now ssh.service
  if systemctl list-unit-files ssh.socket --no-legend | grep -q '^ssh.socket'; then
    systemctl disable --now ssh.socket
  fi
  rm -f /usr/sbin/policy-rc.d
  policy_created=false
fi

stage=$(mktemp -d)
curl --proto '=https' --tlsv1.2 -fSL --connect-timeout 15 --max-time 300 \
  "https://github.com/openai/tunnel-client/releases/download/v0.0.16/tunnel-client-v0.0.16-linux-$arch.zip" -o "$stage/client.zip"
printf '%s  %s\n' "$client_sha" "$stage/client.zip" | sha256sum -c -
curl --proto '=https' --tlsv1.2 -fSL --connect-timeout 15 --max-time 120 \
  'https://codeload.github.com/slepp/ssh-mcp/tar.gz/37381ddc68a941b62ed8557dcbb5644dc3b6c5fd' -o "$stage/mcp.tar.gz"
printf '%s  %s\n' a4792f1271dc332c283054e92e8819ee15225c10bf20a5347f07acdad68b92a3 "$stage/mcp.tar.gz" | sha256sum -c -

install -d -m 755 "$base"
python3 - "$stage/client.zip" "$base" <<'PY'
import pathlib, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    for name in ('tunnel-client', 'cloudflared', 'cloudflared-manifest.json', 'LICENSE', 'NOTICE'):
        path = pathlib.Path(sys.argv[2]) / name
        path.write_bytes(archive.read(name))
        path.chmod(0o755 if name in ('tunnel-client', 'cloudflared') else 0o644)
PY
useradd --create-home --home-dir "$account_home" --shell /bin/bash --user-group "$account"
chmod 700 "$account_home"
# Random, discarded password hash avoids a locked-account rejection by sshd.
# Password authentication is disabled below; no reusable password is emitted.
python3 - <<'PY' | chpasswd -e
import secrets, subprocess
hashed = subprocess.check_output(['openssl', 'passwd', '-6', '-stdin'], input=secrets.token_bytes(48).hex().encode()).decode().strip()
print('codex-test:' + hashed)
PY
install -o "$account" -g "$account" -m 600 "$stage/mcp.tar.gz" "$account_home/mcp-source.tar.gz"
runuser -u "$account" -- python3 -m venv "$account_home/mcp"
runuser -u "$account" -- "$account_home/mcp/bin/pip" install --no-deps "$account_home/mcp-source.tar.gz"
# pip's isolated build may fetch setuptools; Debian/PyPI build dependencies are not fully pinned.
install -d -o "$account" -g "$account" -m 700 "$account_home/.ssh" "$account_home/work" "$account_home/results"
runuser -u "$account" -- ssh-keygen -q -t ed25519 -N '' -C codex-test-loopback -f "$account_home/.ssh/loopback"
{ printf 'from="127.0.0.1",no-agent-forwarding,no-port-forwarding,no-X11-forwarding '; cat "$account_home/.ssh/loopback.pub"; } > "$account_home/.ssh/authorized_keys"
chown "$account:$account" "$account_home/.ssh/authorized_keys"
chmod 600 "$account_home/.ssh/authorized_keys"
install -d -m 700 "$conf"
ssh-keygen -q -t ed25519 -N '' -C codex-loopback-host -f "$conf/host_ed25519"
{ printf '[127.0.0.1]:%s ' "$ssh_port"; cut -d ' ' -f 1,2 "$conf/host_ed25519.pub"; } > "$account_home/.ssh/known_hosts"
cat > "$account_home/.ssh/config" <<EOF
Host codex-test-local
    HostName 127.0.0.1
    Port $ssh_port
    User $account
    IdentityFile $account_home/.ssh/loopback
    IdentitiesOnly yes
    UserKnownHostsFile $account_home/.ssh/known_hosts
    StrictHostKeyChecking yes
    BatchMode yes
    ConnectTimeout 5
    ForwardAgent no
EOF
chown "$account:$account" "$account_home/.ssh/config" "$account_home/.ssh/known_hosts"
chmod 600 "$account_home/.ssh/config" "$account_home/.ssh/known_hosts"
cat > "$conf/sshd_config" <<EOF
ListenAddress 127.0.0.1
Port $ssh_port
HostKey $conf/host_ed25519
PidFile /run/codex-ssh-loopback.pid
AuthorizedKeysFile .ssh/authorized_keys
AllowUsers $account
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
UsePAM no
DisableForwarding yes
PermitTunnel no
X11Forwarding no
EOF
if [[ "$proxmox_admin" == true ]]; then
  runuser -u "$account" -- ssh-keygen -q -t ed25519 -N '' -C codex-proxmox-admin -f "$account_home/.ssh/proxmox_admin"
  { printf 'from="127.0.0.1",no-agent-forwarding,no-port-forwarding,no-X11-forwarding '; cat "$account_home/.ssh/proxmox_admin.pub"; } > "$conf/proxmox-admin-authorized_keys"
  # Root's existing authorized_keys and the system SSH configuration are untouched.
  cat >> "$conf/sshd_config" <<EOF
Match User root
    AllowUsers root
    PermitRootLogin prohibit-password
    AuthorizedKeysFile $conf/proxmox-admin-authorized_keys
EOF
  cat >> "$account_home/.ssh/config" <<EOF

Host codex-proxmox-host
    HostName 127.0.0.1
    Port $ssh_port
    User root
    IdentityFile $account_home/.ssh/proxmox_admin
    IdentitiesOnly yes
    UserKnownHostsFile $account_home/.ssh/known_hosts
    StrictHostKeyChecking yes
    BatchMode yes
    ConnectTimeout 5
    ForwardAgent no
EOF
fi
install -d -m 755 /run/sshd
/usr/sbin/sshd -t -f "$conf/sshd_config"
cat > "$unit" <<EOF
[Unit]
Description=Codex Debian or Proxmox loopback-only OpenSSH
After=network.target
[Service]
ExecStartPre=/usr/bin/install -d -m 755 /run/sshd
ExecStartPre=/usr/sbin/sshd -t -f $conf/sshd_config
ExecStart=/usr/sbin/sshd -D -e -f $conf/sshd_config
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF
# Identity manifest is local only; never printed or uploaded by bootstrap.
{ printf 'Platform: %s\nProxmox admin enabled: %s\nSSH alias: codex-test-local\nAccount: %s\nWork: %s/work\nLogs: %s/results\nMachine ID: ' "$platform" "$proxmox_admin" "$account" "$account_home" "$account_home"; cat /etc/machine-id; ssh-keygen -lf "$conf/host_ed25519.pub"; } > "$conf/identity.txt"
systemctl daemon-reload
systemctl enable --now codex-ssh-loopback.service
printf 'platform=%s\nproxmox_admin=%s\nslepp=37381ddc68a941b62ed8557dcbb5644dc3b6c5fd\ntunnel-client=v0.0.16\n' "$platform" "$proxmox_admin" > "$base/installed"
cat > "$base/README.txt" <<EOF
Codex SSH local installation
Platform: $platform
Proxmox admin enabled: $proxmox_admin
MCP/tunnel account: $account (no sudo)
MCP stdio command: $account_home/mcp/bin/ssh-mcp
Tunnel client: $base/tunnel-client
Local test alias: codex-test-local
Optional Proxmox root alias: codex-proxmox-host (only when admin enabled)
SSH config/keys: $account_home/.ssh
Local identity: $conf/identity.txt (root-readable)
Loopback service: codex-ssh-loopback.service
Bootstrap did not create or start a tunnel or any VMs.
As codex-test: tunnel client help quickstart, runtimes list, profiles list.
Use the client's installed help for actual runtime/profile commands.
On Proxmox: find task-owned VMs and read their Description first.
Guest test usernames/passwords and run state belong in those descriptions.
Run project tests in the verified guest; preserve unrelated VMs and host config.
EOF
chmod 644 "$base/README.txt"
check_local
printf '\nNext: runuser -l codex-test\nThen: /opt/codex-ssh/tunnel-client help quickstart\nMCP stdio command: /var/lib/codex-test/mcp/bin/ssh-mcp\nNo tunnel or Codex connection has been configured.\n'
if [[ "$platform" == proxmox ]]; then
  printf 'Proxmox detected: provision approved guests through existing qm/API tools; run tests in verified guests, not on this host. No VMs created.\n'
fi
