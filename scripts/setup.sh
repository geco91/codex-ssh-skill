#!/usr/bin/env bash
# Run from the verified installer bundle on the local Debian/Proxmox host.
set -Eeuo pipefail
set +x
umask 077
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
local_only=false
admin_requested=false
for option in "$@"; do
  case "$option" in
    --help|-h)
      printf 'Usage: setup.sh [--local-only] [--proxmox-admin]\nGuided local bootstrap and optional native tunnel runtime setup. Run as root.\n'
      exit 0 ;;
    --local-only) local_only=true ;;
    --proxmox-admin) admin_requested=true ;;
    *) printf 'Unknown option: %s\n' "$option" >&2; exit 2 ;;
  esac
done
[[ $EUID -eq 0 ]] || { printf 'Run this installer as root on your local Debian/Proxmox host.\n' >&2; exit 1; }
# Source only detection and constants; the bootstrap main block is guarded.
# shellcheck source=scripts/bootstrap-debian.sh
source "$script_dir/bootstrap-debian.sh"
platform=$(detect_platform)
printf '\nCodex SSH — local host setup\nDetected: %s\n' "$platform"
if [[ -f /opt/codex-ssh/installed ]]; then
  if grep -qx 'proxmox_admin=true' /opt/codex-ssh/installed; then admin_requested=true; fi
elif [[ "$platform" == proxmox && "$admin_requested" == false ]]; then
  printf 'Enable VM administration? This grants FULL host root via a separate SSH key. [y/N] ' > /dev/tty
  IFS= read -r answer < /dev/tty
  case "$answer" in y|Y|yes|YES) admin_requested=true ;; esac
fi
bootstrap_args=(--install)
if [[ "$admin_requested" == true ]]; then bootstrap_args+=(--proxmox-admin); fi
bash "$script_dir/bootstrap-debian.sh" "${bootstrap_args[@]}"
install -m 644 "$script_dir/configure-tunnel.py" /opt/codex-ssh/configure-tunnel.py
if [[ "$local_only" == true ]]; then
  printf 'Local setup finished. Later: python3 /opt/codex-ssh/configure-tunnel.py\n'
else
  python3 /opt/codex-ssh/configure-tunnel.py
fi
