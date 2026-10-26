# Changelog

## v0.2.1 — prepared, not released

- Diagnose APT dependency-source errors before SSH service changes; support scoped signed Debian sources without subscription changes.
- Fix controlling-terminal streams and preserve saved keys during interrupted guided setup.
- Report local installation, tunnel readiness and untested product connection separately, with explicit resume instructions after reboot.
- Retain native runtime supervision; persistent autostart remains separate in PR #4.
- Prepare reproducible bundles and checksums; no release tag, host deployment or reboot acceptance is implied.

## v0.2.0 — 2026-10-19

- Translate current documentation and skill instructions to English.
- Restructure the README around local-server/Proxmox use, architecture, one-line
  installation, account prerequisites, MCP connection and skill import.
- Add project icon, header banner and reusable architecture diagram.
- Add a versioned, checksum-verified guided installer bundle and hidden runtime-key
  input. Use tunnel-client's existing native runtime manager and preserve existing
  credentials/aliases on repeat setup.
- Record upstream pins in a dependency lock and verify their bytes during install
  and with a weekly GitHub Actions job. No automatic upstream upgrades.
- Add setup/integrity regression checks. The guided revision has not been installed
  live on another host; the earlier smoke test remains separate evidence.

## v0.1.1 — 2026-10-19

- Discover documented SSH aliases and existing keys before asking for credentials.
- Explain tunnel authentication, SSH user login and SSH host-key trust separately.
- Allow explicitly authorized target-specific TOFU with `accept-new`, persistent
  known_hosts and subsequent `yes`; never silently rotate changed keys.
- Record first identity enrollment honestly when no expected machine ID exists.
- Reuse existing scope for routine VM work. Check saved boot/disk/network settings
  and distinguish VLAN attachment from an extra guest tag.
- Verify actual guest login methods, provisioning and expected HTTP content.
- Document the first successful product-MCP/guest/HTTP smoke test separately from
  historical and still-open acceptance checks.

The installer and published v0.1.0 files were unchanged in that release.

## v0.1.0 — 2026-10-19

First published instruction skill for existing SSH-MCP through Secure MCP Tunnel.

- Debian/test-Proxmox workflow, host/guest identity, bounded commands/logs and
  resumable test runs.
- VM Description as a resumption record, including explicitly requested guest test
  credentials. No real credentials in the repository or download.
- Debian/Proxmox bootstrap with pinned upstreams and checksums, private loopback
  SSH and optional separate host-admin access.
- Installable skill ZIP, setup notes, source comparison and original live record.

At that release: six local bootstrap tests, shell checks and local MCP/SSH calls
passed on the test Proxmox. Product end-to-end discovery, guest creation and full
plain-Debian installation had not yet been established. Versioned historical ZIPs
retain their original language and bytes; later releases provide English content.
