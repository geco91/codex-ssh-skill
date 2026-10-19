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
| `/etc/codex-ssh/` | Loopback SSH configuration, host key, local identity |
| `/var/lib/codex-test/mcp/` | Isolated SSH-MCP Python environment |
| `/var/lib/codex-test/.ssh/` | Client aliases, login keys and known_hosts |
| `/var/lib/codex-test/.config/codex-ssh/guided/` | Guided setup state, profiles, protected runtime-key file and diagnostic log |
| `/opt/codex-ssh/configure-tunnel.py` | Reconfigure/check the guided runtime |

The wizard reads the runtime key using a hidden terminal prompt, writes it with
mode 0600, and passes only a `file:` reference to tunnel-client. It does not ask
for an admin key, emit the runtime key or commit it. State directories are 0700.
The tunnel and its stdio MCP child run as `codex-test`; the optional SSH root
alias is a separate, explicit escalation path.

Guest test credentials follow the requested Proxmox Description rule. Host-root,
private SSH keys and tunnel credentials do not belong in VM descriptions.

## Runtime lifecycle

The wizard uses the existing tunnel client's `runtimes connect` supervision and
then runs `doctor` and `runtimes status`. It does not build another supervisor,
SSH server implementation or tunnel transport. Running/healthy/ready is local
readiness, not proof of successful product tool discovery or control-plane polling.
Complete the [product connection check](onboarding.md#3-connect-and-test).

The native managed runtime can survive the terminal closing; this installer does
not install a tunnel startup service for reboot. After host restart, rerun
`python3 /opt/codex-ssh/configure-tunnel.py` as root to reconnect the recorded
runtime. For deployment-specific autostart follow the upstream
[systemd deployment guide](https://github.com/openai/tunnel-client/blob/v0.0.16/docs/deployment/systemd-vm.md).

## Checks and recovery

```bash
bash scripts/bootstrap-debian.sh --check
python3 /opt/codex-ssh/configure-tunnel.py --status
```

An existing completed bootstrap is checked, not reinstalled. Partial installations
stop for inspection; no automatic deletion or rollback. An existing generated
key file or unrelated runtime alias is not overwritten. Interrupted configuration
keeps its local state; inspect it before retrying. Local SSH or a running tunnel
alone is not a successful guest test.

If enterprise apt sources return 401, fix the appropriate sources deliberately.
The installer does not silently switch Proxmox subscriptions. An already approved
source file can be selected for a single run with `CODEX_SSH_APT_SOURCES` set to
its absolute path; signature verification stays enabled.

For initial root access use the local console or an already authorized terminal
connection. This project does not grant itself access to an unassigned machine.
