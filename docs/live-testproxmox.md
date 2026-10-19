# Live setup and first MCP/guest smoke test

Date: 2026-10-19. This record separates the original human-reviewed local setup
from the later product-MCP test. Real hostnames, private addresses, machine IDs,
keys and credentials are intentionally omitted.

## Original AITL setup

The user authorized the test Proxmox. Initial commands ran through the existing
Admin in the Loop connection; only terminal output shared by the human was used.
Observed: Proxmox 9.2.2, Debian 13.5, active host SSH and no guests in `qm list`/
`pct list`. That human-reviewed path did not prove SSH-MCP access from Codex.

The executed bootstrap snapshot was checked on the host against SHA-256
`fed824d64fc8ac8651e3b421ce28ebc7a92b14e8a5e07a5b831e038d0ba33bcb`.
This preceded the optional apt-source-file addition. The first installation exited
100 because both Enterprise sources returned 401 Unauthorized. The reserved
installation directories and test account did not yet exist.

At the user's explicit request, the original `pve-enterprise.sources` and
`ceph.sources` were backed up and disabled with `Enabled: no`; `proxmox.sources`
was added with the official `pve-no-subscription` repository. No Ceph configuration
was present. Existing Proxmox signing keys stayed in use, with no disabled package
signature checks or general host upgrade. The local backup was under
`/root/codex-ssh-bootstrap-fed824d64fc8/apt-sources-backup`.
The next `apt-get update` exited 0. Source:
[official Proxmox repository documentation](https://github.com/proxmox/pve-docs/blob/master/pve-package-repos.adoc).

The repeated `--install --proxmox-admin` run returned `BOOTSTRAP_EXIT=0`:

- slepp-ssh-mcp 0.2.0 was installed in its own venv.
- tunnel-client 0.0.16 was installed; both downloaded archives matched their hashes.
- The separate loopback-only SSH service was enabled.
- The unprivileged SSH self-test printed `loopback-ssh-ok`.
- The separate root alias passed an identity/Proxmox-version check.

apt installed four Python venv/wheel packages and updated four Python 3.13
 dependencies from Debian revision deb13u2 to deb13u5. There was no general
Proxmox upgrade; `--no-upgrade` does not prohibit all dependency upgrades.

A local MCP initialize/discovery test and two harmless `ssh_exec` calls passed
with `MCP_LOCAL_OK`, exit 0 and no timeout. They tested Hello World as `codex-test`
and `id -u` through the admin alias. Both accounts were on the host; a one-off
“guest-account” marker did not mean a guest VM existed.

Runtime credentials were entered privately under the test account's local config.
`TUNNEL_CREDENTIALS_READY` was shared without values. Native tunnel startup/status
returned process_running, healthy and ready true, with connect/status exit 0.
The profile referenced a protected runtime-key file. No paid agent API replaced
the existing connection. Control-plane polling was still unknown in that snapshot.
The user reported the product connection as “Codex-Proxmox”; tools were not yet
visible in that earlier session.

## First product-MCP and guest verification

In the subsequent session the selected connection's actual SSH tools were offered
and callable. A direct-address attempt after explicit TOFU authorization saved a
host key but failed authentication with exit 255. The password had not been passed,
so this did not demonstrate a wrong password. An MCP session also failed without
providing an accessible SSH password prompt.

Repository research identified the existing `codex-proxmox-host` alias. Its bounded
identity command with strict host-key checking returned exit 0, root and the
expected directory. The machine ID matched the local bootstrap manifest. This
alias reused the existing key/pin and did not need the direct-address TOFU step.

Inventory still contained no VMs. An authorized Debian 13 test guest was created
with 1 vCPU, 1024 MiB RAM and an 8 GiB disk. The official
`debian-13-generic-amd64.qcow2` from
`https://cloud.debian.org/images/cloud/trixie/latest/` matched its HTTPS-delivered
SHA512SUMS entry. The exact hash was saved in the local VM record. No additional
upstream signature check was performed. The existing bridge already carried the
assigned guest network, so no extra guest VLAN tag was added.

The first boot attempted network boot and showed “No bootable device”. The saved
boot order excluded the system disk. Only this newly created VM was stopped;
after explicitly setting `order=scsi0` and starting again, Debian booted. The
reason for the earlier unexpected order was not conclusively established. This
motivated reading back the saved configuration after updates.

Observed final results:

- The provisioning script saved exit 0; the boot issue was subsequently corrected.
  `cloud-init status --wait` returned `status: done`.
- The guest reported Debian 13.7; nginx and QEMU Guest Agent were active.
- Public guest host key and machine ID came through QEMU Guest Agent. A dedicated
  guest alias used that key; the MCP guest identity call exited 0 and matched.
- Key login through the MCP alias and a separate password login through existing
  OpenSSH both passed; the password check exited 0. Password material stayed local.
- HTTP from the guest returned 200 and expected Hello World content; the same
  page was also reachable from the Proxmox host.
- Generated guest credentials, image checksum, identity and check results were
  recorded in the VM Description. The user confirmed the first test succeeded.

This establishes the concrete product-MCP → Proxmox → guest → HTTP smoke test.
It did not test a project checkout/commit, a separate Codex Cloud task, negative
host-key cases, post-reboot/session recovery or a full plain-Debian bootstrap.

## Guided installer revision

Release 0.2.0 adds English documentation and guided runtime configuration. The
historic live test above predates those changes. Unit/integration checks of the
new configuration code and pinned client CLI are separate evidence; they do not
claim another live installation or a successful production control-plane call.
