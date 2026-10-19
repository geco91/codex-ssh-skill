# Design choices and compatibility research

Initial review: 2026-10-19. Current account setup follows the official documentation
linked below; product surfaces and access can change. Read actual tool schemas
and installed client help rather than assuming a README guarantees availability.

## Why this architecture

The skill is a small instruction package, not a connection manager. Existing
OpenSSH handles machine access; the private MCP host runs the existing SSH-MCP
server as a stdio child of OpenAI's tunnel client. Only outbound HTTPS is needed
for the product path. No new HTTP adapter, SSH server implementation, tunnel
transport or job platform is introduced.

The bootstrap configures a separate instance of existing OpenSSH on loopback;
it does not replace system SSH. Proxmox administration has an explicit separate
root key; project tests run in assigned guests. The generic upstream MCP tools
can reach any SSH target available to their account. The skill is not a security
boundary, VM-ID policy engine or replacement for network/account restrictions.

## Upstream comparison at the original review

| Criterion | tufantunc/ssh-mcp | slepp/ssh-mcp (selected) |
| --- | --- | --- |
| Reviewed commit | `58b03f10b0d184fa31573b2ea79f378aa8285ff2` | `37381ddc68a941b62ed8557dcbb5644dc3b6c5fd` |
| License | MIT | MIT |
| Runtime | TypeScript, ssh2 | Python 3.10+, existing OpenSSH |
| Transport | stdio/HTTP | stdio |
| Capabilities | Role/policy/approval, command/session/SFTP tools | Commands, file tools, sessions, transfer, forwarding |
| Host trust | `trustedHostKey`, strict host-key mode | Existing SSH config; known_hosts and strict checking per call |
| Fit | Alternative when server-side policy is needed | Small setup without another adapter or Python runtime dependencies |

Both projects' CI/source tests were inspected. Selected slepp fake-SSH tests were
run locally; that alone did not establish live verification. The later real smoke
test is documented in the [live record](live-testproxmox.md).

Primary sources at the reviewed revisions:

- [slepp implementation](https://github.com/slepp/ssh-mcp/blob/37381ddc68a941b62ed8557dcbb5644dc3b6c5fd/src/ssh_mcp/ssh.py)
  and [tests](https://github.com/slepp/ssh-mcp/tree/37381ddc68a941b62ed8557dcbb5644dc3b6c5fd/tests).
- [tufantunc host-key implementation](https://github.com/tufantunc/ssh-mcp/blob/58b03f10b0d184fa31573b2ea79f378aa8285ff2/src/ssh/host-key.ts)
  and [tools](https://github.com/tufantunc/ssh-mcp/tree/58b03f10b0d184fa31573b2ea79f378aa8285ff2/src/tools).
- [OpenAI tunnel-client onboarding](https://github.com/openai/tunnel-client/blob/v0.0.16/docs/onboarding.md),
  [configuration](https://github.com/openai/tunnel-client/blob/v0.0.16/docs/configuration.md)
  and [native runtime command source](https://github.com/openai/tunnel-client/blob/v0.0.16/cmd/client/runtimes_command.go).

## Product and permissions references

- [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels):
  tunnel identity, organization/workspace associations, runtime-key permissions,
  outbound networking and product connection path.
- [Codex skills](https://developers.openai.com/codex/skills): instruction discovery
  and installation. A local CLI example is not proof of cloud-session discovery.
- [Codex MCP](https://developers.openai.com/codex/mcp): MCP extension mechanisms;
  availability must be tested in the intended surface.
- [Proxmox Cloud-Init documentation](https://github.com/proxmox/pve-docs/blob/2e161a79bbcce5e8d99816564ac54c7438abcdaf/qm-cloud-init.adoc):
  templates, clone workflow and guest configuration. Installed help remains the
  source for flags on the actual host.

The official tunnel guide separates Platform tunnel permissions from workspace
custom-MCP permissions and documents a personal-account organization path. This
repository therefore does not claim a blanket Business-only prerequisite. Nor
does it promise that all plans include every surface or that paid API agent calls
are covered by an existing Codex subscription.

## Trust policy after practical use

The first draft prohibited all TOFU. User feedback after the successful test led
to target-specific explicitly authorized TOFU, persistent first-key storage and
strict checking afterward. Changed keys still stop. Expected identity matches,
first enrollment and actual tool/test success remain separate evidence. See
[access and trust](../.agents/skills/codex-ssh/references/access.md).

Pinning is intentional: [the lock file](../dependencies.lock.json) and
[dependency policy](dependencies.md) explain archive verification, scheduled drift
checks and the limits of apt/pip reproducibility. Upstream updates are reviewed,
not automatically adopted.
