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
printf '\nPhase 1/3: local SSH/MCP installation and SSH check\n'
if ! bash "$script_dir/bootstrap-debian.sh" "${bootstrap_args[@]}"; then
  printf 'Local setup stopped. Existing files and identities are preserved. Resolve the reported error and rerun this setup with the same options; do not reset or delete keys.\n' >&2
  exit 1
fi
printf 'SUCCESS: phase 1/3 complete — local SSH/MCP installed; local SSH check passed.\n'
install -m 644 "$script_dir/configure-tunnel.py" /opt/codex-ssh/configure-tunnel.py
if [[ "$local_only" == true ]]; then
  printf 'Phase 2/3: tunnel setup skipped (--local-only); existing tunnel state unchanged.\nPhase 3/3: product connection NOT TESTED.\nNext: python3 /opt/codex-ssh/configure-tunnel.py\n'
else
  printf '\nPhase 2/3: configure/check tunnel process, health and readiness\n'
  if ! python3 /opt/codex-ssh/configure-tunnel.py; then
    printf 'Phase 2/3 stopped; phase 1 remains complete. Saved tunnel state and keys are preserved.\nNext: inspect python3 /opt/codex-ssh/configure-tunnel.py --status and the private native-runtime diagnostic log locally.\nAfter resolving the reported error, resume: python3 /opt/codex-ssh/configure-tunnel.py\nPhase 3/3: product connection NOT TESTED.\n' >&2
    exit 1
  fi
fi
