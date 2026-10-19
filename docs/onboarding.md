# Connect your local server to Codex

You configure two things: a private **MCP connection** that provides tools, and a
**skill** that tells Codex how to use them. Installing either one does not install
the other. No separate API schema needs to be pasted: the SSH-MCP server provides
its tool schemas during MCP discovery.

## 1. Prepare your OpenAI account

Open the [official Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
and select the intended Platform organization and ChatGPT workspace.

1. In [Platform tunnel settings](https://platform.openai.com/settings/organization/tunnels),
   create or reuse a tunnel and copy its complete tunnel ID. Creating/editing
   tunnels needs Tunnels **Read + Manage**.
2. Associate the tunnel with the target ChatGPT workspace and the Platform
   organization used by Codex. A tunnel existing in one organization does not
   automatically make it visible in another workspace.
3. In [Runtime API keys](https://platform.openai.com/settings/organization/api-keys),
   create a **Restricted** runtime key with Tunnels **Read + Use** for its principal.
   Save it for the local hidden prompt. Do not use an admin API key for the daemon.
4. Workspace policy must allow adding and using custom MCP servers. Your admin
   may need to grant the necessary access.

Availability depends on the account, product surface and organization/workspace
permissions. A managed Business/Enterprise/Edu workspace may require administrator
approval; **Business is not documented as a universal prerequisite**. Personal
accounts also have an organization-association path in the official guide. If the
Tunnels page or custom-MCP controls are unavailable, verify eligibility with your
admin or OpenAI before installing. This project makes no claim that every plan
includes tunnel usage or that unrelated API use is covered by a Codex subscription.

The [upstream onboarding guide](https://github.com/openai/tunnel-client/blob/v0.0.16/docs/onboarding.md)
has the exact setup URLs and separates runtime keys from administrative keys.

## 2. Run the installer on the local host

Use the versioned one-liner in the [README](../README.md#install-on-your-local-host).
Run it on Debian/Proxmox as root, not in a disposable cloud worker. Keep the local
terminal available: the wizard uses `/dev/tty`, including when downloaded through
a pipe. There is no unattended key input or password printed to the screen.

The wizard detects the platform, offers optional full-root VM administration on
Proxmox, installs verified upstreams, checks local SSH and asks for:

- The tunnel ID you created in step 1.
- The runtime API key, entered without echo.

Press Enter at the tunnel-ID prompt to finish only the local installation. Resume
later as root with `python3 /opt/codex-ssh/configure-tunnel.py`.

The runtime uses the SSH-MCP **stdio** command directly. You do not supply a public
MCP URL, expose host SSH to the internet or copy a private key into Codex.

## 3. Connect and test

The installer enables `codex-ssh-tunnel.service` for unattended startup and
recovery. Check it with `python3 /opt/codex-ssh/configure-tunnel.py --status`.
Follow the current
[official product connection instructions](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels#connect-from-chatgpt).
The documented ChatGPT path is [Plugins](https://chatgpt.com/plugins) → add custom
MCP server → **Tunnel**. Select your existing tunnel, set the requested product
authentication options and create the plugin. If it is missing, check workspace
association and Tunnels Read + Use. UI names can change; follow the current UI.

In the supported Codex surface, select/enable that connection and inspect the
available tools. Do not assume that a successful ChatGPT call proves availability
inside a separate Codex Cloud task. The CLI/IDE alternative, if MCP runs on the
same machine as that client, is documented by
[slepp/ssh-mcp](https://github.com/slepp/ssh-mcp#codex-cli); it is a different local
stdio setup and does not need a Secure MCP Tunnel for that local client.

## 4. Install the skill

Download the current `codex-ssh.zip` and `SHA256SUMS` linked in the README.

- In a product surface that supports skill ZIP import, import the ZIP and enable
  the skill. Check your workspace's skill/plugin controls if import is unavailable.
- For Codex CLI/IDE, extract its `codex-ssh` directory into your project's
  `.agents/skills/` and confirm skill discovery. See the
  [official skills guide](https://developers.openai.com/codex/skills).

Use `assets/icon.png` as the skill/plugin image when the UI offers an icon field.
Importing a new release does not automatically update an older installed skill.
The ZIP contains English instructions, references and a license, not credentials
or an MCP connection.

## 5. Give Codex a first task

For an installation known to belong to this connection:

> Use $codex-ssh with the selected local-server MCP connection. Read the project
> setup and verify the assigned host identity using codex-test-local. Report the
> account, trust mode and result without changing the server.

For an explicitly enabled Proxmox admin setup:

> Use $codex-ssh with the selected Proxmox connection and documented
> codex-proxmox-host alias. Verify identity, inspect existing VMs, then create a
> Debian test VM within these limits: 1 vCPU, 1 GiB RAM, 8 GiB disk. Serve a Hello
> World page on port 80. Inspect storage and network first; ask only for missing
> IP/prefix, gateway, DNS, VLAN attachment or image choices. Record the generated
> guest login in its Description and verify guest login and HTTP content.

The existing local aliases already use keys and a pinned host key. You do not
need the host's ordinary root password for them. For another new target, provide
its assigned alias and trust setup; explicitly authorize target-specific TOFU if
that is your intended first-contact policy.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| No Tunnels settings | Platform organization, tunnel permissions and account availability |
| Tunnel absent from the product | Correct workspace/organization association and operator Read + Use |
| Runtime exits or is not ready | systemctl/journalctl for codex-ssh-tunnel.service, key scope, outbound HTTPS |
| `Permission denied` | Documented alias, target account and key; this alone does not prove a password is wrong |
| New host key | Existing pin first; target-specific authorized TOFU only for first contact |
| Changed host key | Stop and investigate; do not remove the old pin automatically |
| VM runs but page is unavailable | Boot order, Cloud-Init, actual network attachment, service and HTTP content |
| Tools work in ChatGPT, not another task | Discover tools in that exact Codex surface; verify its connection assignment |

More: [local setup](bootstrap.md), [dependency integrity](dependencies.md),
[validation](validation.md) and [live record](live-testproxmox.md).
