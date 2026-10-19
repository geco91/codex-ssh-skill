# Run the task on the right host or guest

## Platform and permissions

After the identity check compare the assigned role with the observed platform.
`/etc/pve`, `pveversion` and `qm` together identify Proxmox. Partial or conflicting
signals require clarification, not a fallback to plain Debian installation.

- Plain Debian: test directly in the authorized checkout on that machine.
- Proxmox: host management and MCP/tunnel components belong on the host; project
  dependencies and tests belong in explicitly assigned guest VMs.

Use existing `qm`/Proxmox API operations. Inspect installed help instead of
inventing flags or endpoints. The bootstrap's explicit `--proxmox-admin` option
creates `codex-proxmox-host` with full host-root access, not a technical limit to
specific VM IDs. Otherwise use the account's existing rights or an already
authorized Proxmox API connection. Report missing rights precisely.

## Provision and recover a VM

1. Read `qm list` and descriptions of relevant VMs first. Match purpose/project
   and run identity, not just a name. Read existing guest logins from Description.
   Reuse a suitable assigned VM rather than creating a duplicate.
2. Before creating a VM establish scope, resources, node, storage, bridge and
   approved image/template provenance and integrity. Prefer existing configured
   resources; ask only for genuinely missing choices. Never turn example IPs,
   bridge names, storage IDs or VM IDs into real defaults.
   For static networking establish IP/prefix, gateway, DNS and assigned use of
   that address. Distinguish an uplink already connected to a VLAN from a required
   guest/bridge tag: inspect bridge ports, host addressing and VLAN configuration.
   Do not infer a tag from a subnet number. Ask if the attachment remains ambiguous.
3. Prefer an existing verified Debian Cloud-Init template and `qm clone`; otherwise
   use the documented `qm create`/import path. Configure Cloud-Init, the guest user,
   SSH login key and requested test password inside the guest. Check available
   storage and authentication rules. No host dist-upgrade or project packages.
4. Recheck the free VM ID immediately before creation. Save VM ID, project/run
   identity and current step in Description as soon as creation is confirmed.
   After timeout inspect inventory and task status before retrying create/clone.
   Never overwrite or automatically delete an unrelated VM.
5. Save the Description, including guest credentials, before first boot. After
   disk import, seed/Cloud-Init attachment and Description updates read back the
   actual saved configuration: correct system disk, system disk first in boot
   order, seed medium, NIC/bridge/tag, resources and guest-agent channel. Redact
   credentials from output. Diagnose boot problems using the new VM's console
   and repair that VM rather than creating another. `qm status` or a successful
   Proxmox task does not establish guest SSH readiness.
6. Obtain guest addressing from configured static IP, DHCP, Cloud-Init or Guest
   Agent data. Clones need their own machine ID and SSH host keys. Prefer pinning
   the public guest host key through the verified host's QEMU Guest Agent or
   guest console. A network keyscan or an address alone is not independent proof.
   Explicit authorization for this guest can instead use the [TOFU path](access.md),
   with its limits reported honestly.
7. Create a dedicated guest alias on the MCP host with its account, pinned host
   key and bounded connection time. Reuse the same MCP server/tunnel for this
   guest. Switch explicitly and compare machine ID, user and directory. Transfer
   project code separately if needed and verify SHA/worktree before code tests.
8. Follow the [test workflow](workflow.md). Keep Description current with guest
   alias and run status, not growing logs. For a Hello World server verify finished
   provisioning/Cloud-Init, active service, guest login and HTTP 200 with expected
   content. Fetch from outside the guest on the intended network when reachable.
   Actually test a requested password login or mark it unverified; key-login
   success does not prove password login. Image integrity and tested code SHA
   are distinct evidence.

A scoped VM provisioning task authorizes the necessary routine checks and changes.
Ask for missing configuration, rights or scope extensions, not for every command.

## Description as the resumption record

For **assigned test VMs you create**, the explicitly requested operating rule is
to store the real guest login user and generated test password in the Proxmox
Description. It is visible to users with VM-description access and is not a
secret vault. Never put host-root or tunnel credentials there. Configure guest
SSH to support the documented login and verify it. Automation may also use a key.

Only this placeholder schema belongs in the public repository:

```text
Codex test VM — schema 1
Purpose/project: <PROJECT>
Task/run: <TASK_OR_RUN_ID>
Node / VMID / name: <NODE> / <VMID> / <NAME>
Created UTC: <UTC>
Template/image and version: <SOURCE_AND_CHECKSUM>
Resources / storage / bridge: <CONFIGURED_VALUES>
Guest IP / SSH alias: <ADDRESS_AND_PREFIX> / <ALIAS>
Gateway / DNS / VLAN attachment: <CONFIGURED_VALUES>
Login user: <GUEST_TEST_USER>
Login password: <GENERATED_GUEST_TEST_PASSWORD>
Login verified UTC: <UTC_OR_PENDING>
Guest identity / SSH fingerprint: <VERIFIED_VALUES_OR_PENDING>
Trust mode / login methods tested: <PIN_OR_TOFU> / <KEY_PASSWORD_OR_PENDING>
Provisioning / service / HTTP checks: <STATUS_EXITCODES_AND_EXPECTED_CONTENT>
Checkout / tested SHA / logs: <PATHS_AND_SHA_OR_NOT_APPLICABLE>
Provisioning state / active run: <STATE_AND_REFERENCE>
Retention / cleanup scope: <USER_AUTHORIZED_POLICY>
```

Update only your own bounded Description block with existing configuration tools,
e.g. `qm set --description` after checking installed help. Preserve unrelated text.
Generate passwords locally and suppress unnecessary output/trace logging. Do not
embed them as literals in public scripts or chat commands.

## Resume after an interruption

Recheck host identity, VM inventory and the matching Description. Reuse the VM
ID, purpose, login and previous run reference; verify current guest identity.
Missing data or a failed login calls for a specific repair, not blind creation or
password rotation. Inspect the old process/run and its result before starting
another test. Delete, restore snapshots or replace a VM only when explicitly
within scope. An installation task does not authorize deleting older VMs.
