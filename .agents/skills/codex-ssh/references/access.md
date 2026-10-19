# Find and verify the existing connection

## Read the project context first

Read the available README, bootstrap documentation, live records and local target
mapping. An empty cloud workspace does not mean that the private MCP host has no
SSH configuration. If the assigned repository is reachable through an available
connection, read it there. Do not switch projects or execution runners.

The bootstrap defines these roles. Use them only when the selected connection is
known to belong to this installation; they are not defaults for arbitrary servers.

| Purpose | SSH target | Account and authentication |
| --- | --- | --- |
| Unprivileged host self-test | `codex-test-local` | `codex-test`, existing loopback key |
| Authorized VM administration with `--proxmox-admin` installed | `codex-proxmox-host` | root, separate existing admin key |
| Work inside a guest | Task-specific guest alias | Guest account, identity and host-key binding |

Both host aliases use `127.0.0.1:22222` on the **MCP host**. The tunnel/MCP process
runs as `codex-test`, which differs from the administrative SSH target account.
Client configuration and keys live under `/var/lib/codex-test/.ssh/` there.
The root-readable identity manifest is `/etc/codex-ssh/identity.txt`; the local
setup note is `/opt/codex-ssh/README.txt`. Do not assume those paths exist in the
cloud workspace. Limit the first remote call to identity. Read additional local
metadata only through an assigned connection; self-reported metadata does not
replace missing independent first-contact verification.

## Three separate credentials and identities

- **Tunnel authentication** connects the private MCP process to the product.
  Its runtime API key is neither an SSH password nor an SSH private key.
- **SSH user authentication** identifies the account to the server. Private keys
  or an SSH agent belong on the MCP host; the target has the public login key.
  The bootstrap already sets these up. Do not request new keys or a root password
  before checking the existing configuration.
- **SSH host keys** identify the server to the client. SSH has host keys even
  when users log in with passwords. These differ from user login keys.

`slepp/ssh-mcp` uses OpenSSH and its existing configuration. The inspected tool
schemas have no password argument. That does not establish a general ban on
password authentication. The separate bootstrap listener actually allows only
keys; the host's original SSH service can have a different configuration.

`Permission denied` without a supplied password does not prove that the user's
password is wrong. An MCP session also does not guarantee an accessible SSH login
prompt. Inspect the documented alias, account, key/agent setup and actual schema.
A remote command's `env` and `cwd` are not password inputs for the local SSH
client. If no supported method exists, report that exact gap. Never place secrets
in command arguments, logs or Git, or build replacement SSH servers or tunnels.

## Trust on first use

1. Prefer a verified known_hosts entry or server pin with `yes`. The bootstrap
   already pins its locally generated loopback host key; no TOFU is needed there.
2. If an assigned target has no host key yet, the user may explicitly authorize
   TOFU for it. If not already authorized, explain briefly and ask once.
3. For that first identity call use `strict_host_key_checking: "accept-new"`.
   Use persistent known_hosts storage on the MCP host, either its configuration
   or `known_hosts_file`. This stores the first observed key; it does not verify
   it independently. The key may be saved even if user authentication fails.
4. Continue with `strict_host_key_checking: "yes"`. Compare machine ID, account
   and working directory with available expected values. Without an expected
   machine ID under authorized TOFU, record a first enrollment locally and
   continue the task. Report “TOFU; identity first enrolled”, not “independently
   verified”. Known identity mismatches are not first enrollment.
5. A changed key is not another first contact. Stop and investigate independently.
   Never automatically remove old entries, use `no`/`off` or silently re-pin.

For a new guest, prefer obtaining its public host key and machine ID through a
verified host's QEMU Guest Agent or guest console. A network keyscan alone is not
independent verification. Authorization for host TOFU does not automatically
apply to every new guest.
