# Local installation and guided setup

Run the installer on your own Debian server or Proxmox host, not in an ephemeral
Codex cloud worker. The host runs the SSH-MCP server and OpenAI tunnel client.
Codex uses the offered MCP connection to reach it.

## Requirements

- Debian 12/13, or a Proxmox host based on those releases, with systemd.
- root access, amd64 or arm64, `curl`, CA certificates, Bash, tar and coreutils.
- Working signed apt sources and outbound HTTPS to the locked upstream downloads,
  Python build dependencies and OpenAI. No inbound internet listener is required.
- For tunnel setup: an existing tunnel ID and a restricted runtime key with Tunnels
  Read + Use. [Account setup](onboarding.md) explains where to get them.

The README's one-line installer downloads a versioned bundle and verifies its
embedded SHA-256 before extracting or running it. The initial launcher itself is
trusted through the versioned HTTPS URL; a hash from the same publisher is not an
independent publisher signature. For inspection before execution, download
`scripts/install.sh` from the release tag, read it, then run it as root.

`bash scripts/setup.sh --local-only` installs/checks local components without
prompting for tunnel credentials. On a fresh Proxmox installation the guide asks
whether to grant VM administration. Passing `--proxmox-admin` explicitly selects
full host-root administration; the default is the unprivileged test account.
Existing installations retain their recorded rights. The wizard does not silently
add admin rights, replace keys, upgrade upstreams or overwrite unrelated runtimes.

## What the bootstrap changes

The underlying `scripts/bootstrap-debian.sh` also supports `--dry-run` (default),
`--install`, `--check` and `--help`. `--proxmox-admin` is valid only with
`--install` on Proxmox. It:

1. Identifies Debian or Proxmox; partial PVE signals stop rather than falling back.
2. Installs missing Python-venv/OpenSSH/curl/CA/OpenSSL packages with no general
   dist-upgrade. Transitive dependencies may still be installed or updated.
3. Downloads the pinned SSH-MCP commit and tunnel-client binaries and verifies
   their expected SHA-256 values. [Dependency policy](dependencies.md) records
   exactly what is fixed and what is not reproducible.
4. Creates `codex-test` without sudo, with private local SSH keys and directories.
5. Starts a separate SSH service on `127.0.0.1:22222`, with password authentication
   and forwarding disabled. Its locally created host key is pinned directly.
6. Optionally adds the separate `codex-proxmox-host` root alias and key. This is
   full host-root access, not a VM-ID-limited permission system.
7. Writes the root-readable identity manifest and performs local SSH self-checks.

Existing host SSH configuration and root authorized_keys are preserved. If SSH
was not installed, the new distribution listener is masked so it will not become
a public service after reboot. The installer refuses existing service-policy or
reserved-path conflicts. It does not create VMs or change bridge/storage/cluster
configuration. Project packages and tests belong in guests on Proxmox.

## Files and credentials

| Path on the local host | Purpose |
| --- | --- |
| `/opt/codex-ssh/` | Pinned tunnel client and installation record |
| `/etc/codex-ssh-tunnel.json` | Root-owned 0640 service profile; only a protected runtime-key file reference |
| `/etc/systemd/system/codex-ssh-tunnel.service` | Boot-enabled foreground tunnel service |
| `/etc/codex-ssh/` | Loopback SSH configuration, host key, local identity |
| `/var/lib/codex-test/mcp/` | Isolated SSH-MCP Python environment |
| `/var/lib/codex-test/.ssh/` | Client aliases, login keys and known_hosts |
| `/var/lib/codex-test/.config/codex-ssh/guided/` | Guided setup state and protected runtime-key file; historical native profiles remain intact |
| `/opt/codex-ssh/configure-tunnel.py` | Configure/check the systemd runtime |

The wizard reads the runtime key using a hidden terminal prompt, writes it with
mode 0600, and passes only a `file:` reference to tunnel-client. It does not ask
for an admin key, emit the runtime key or commit it. State directories are 0700.
The tunnel and its stdio MCP child run as `codex-test`; the optional SSH root
alias is a separate, explicit escalation path.

Guest test credentials follow the requested Proxmox Description rule. Host-root,
private SSH keys and tunnel credentials do not belong in VM descriptions.

## Runtime lifecycle

Version 0.3.0 follows the pinned upstream client's [systemd deployment pattern](https://github.com/openai/tunnel-client/blob/v0.0.16/docs/deployment/systemd-vm.md):
**systemd directly supervises foreground `tunnel-client run`**, with the existing
stdio SSH-MCP child. It does not run `runtimes connect` inside another supervisor.

The unit runs as `codex-test`, with explicit HOME, PATH and working directory,
after `network-online.target` and the required private loopback SSH service.
`enable` adds boot activation; `Restart=always` separately handles process exits
while the machine is running. Recovery waits 5 seconds and is limited to five
starts per five minutes. The unit gives shutdown 20 seconds and kills its whole
process group. No login, terminal, interactive credential prompt or shell session
is needed at service start.

`Type=simple` means systemd's active state is **not** application readiness.
The setup checks the local `/healthz` and `/readyz` separately for up to 30 seconds
(with bounded HTTP probes); its commands also have timeouts. The 45-second
`TimeoutStartSec` bounds systemd activation, not successful OpenAI connectivity.
Local health/readiness is not proof of control-plane polling or product tool
discovery. Complete the [product connection check](onboarding.md#3-connect-and-test).

```bash
systemctl is-enabled codex-ssh-tunnel.service
systemctl status codex-ssh-tunnel.service --no-pager --lines=25
python3 /opt/codex-ssh/configure-tunnel.py --status
journalctl -u codex-ssh-tunnel.service --no-pager -n 80
# Explicit operator restart, not needed on every installer run:
systemctl restart codex-ssh-tunnel.service
# Stop now and disable future boot activation; preserves all keys and profiles:
systemctl disable --now codex-ssh-tunnel.service
# Resume after fixing key permissions, network or a rate-limited failure:
systemctl reset-failed codex-ssh-tunnel.service
systemctl enable --now codex-ssh-tunnel.service
```

The service profile is `/etc/codex-ssh-tunnel.json`, owned by root, group
`codex-test`, mode 0640. It references the existing mode-0600 runtime key with
`file:`; the unit, process arguments and repository never contain the key value.
The health URL lives only under `/run/codex-ssh-tunnel/` (0700), recreated by
systemd on start. Arbitrary native command output is not saved by the wizard;
its local log records only exit status. Inspect upstream journal diagnostics
locally; do not paste credentials or full private logs into issues.

## Existing installations and interrupted setup

Run the new versioned installer normally to upgrade the setup helpers; the
completed bootstrap checks its recorded installation and retains SSH keys, host
identity, account and pinned upstreams. With `--local-only` it updates helpers
without prompting for credentials, enabling a new tunnel service or disabling an
existing service. Run `python3 /opt/codex-ssh/configure-tunnel.py` later as root.
Running that command on an existing service re-enables boot activation but does
not restart a running process. `--status` never changes activation state.

- Guided state and its original runtime key are reused without prompts or rotation.
- Original manual setup files `~codex-test/.config/codex-ssh/tunnel-id` and
  `runtime-api-key` are also adopted without copying the key.
- Matching native aliases `codex-ssh-guided` / `codex-test-proxmox` are migrated
  only with the same tunnel, key-file reference and expected stdio MCP command.
  The native runtime must report stopped before systemd starts. Native records,
  profile files and keys remain for inspection; do not reconnect that native
  alias while the systemd unit is in use.
- Generated JSON profiles (despite their `.yaml` extension) retain custom
  control-plane URL/path and transport settings. Custom YAML, inline keys,
  different targets, unknown aliases for the same tunnel, competing processes,
  existing custom unit definitions or drop-ins stop for local review. They are
  not overwritten, killed or adopted silently. Resolve competing supervisors
  before retrying; never add a second boot mechanism.
- Empty ID skips the tunnel. Empty key, EOF or Ctrl+C stops before saving a new
  credential pair. Input uses the controlling terminal even with `curl | bash`;
  no echo fallback is allowed. If interrupted after the key was saved but before
  state was saved, enter the same tunnel ID on retry; that key is retained.
- A failure after migration/start keeps the saved state. Inspect unit and native
  status before retrying; setup does not blindly launch another process. Concurrent
  wizard invocations are rejected by a local lock.

Check local SSH independently with `bash scripts/bootstrap-debian.sh --check`.
No automatic uninstall, credential deletion or rollback is performed. A running
tunnel alone is not a successful guest test. A **real reboot of an authorized
Debian/Proxmox host**, followed by local status and a product MCP call without an
interactive login, remains the live acceptance step; container restart checks do
not substitute for that evidence. See [versioned validation](validation.md).
