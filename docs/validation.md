# Validation and remaining coverage

## Evidence levels

| Check | Recorded result | Boundary |
| --- | --- | --- |
| Original bootstrap on assigned Proxmox | `BOOTSTRAP_EXIT=0`, local SSH checks passed | One host, not Debian 12/13 and Proxmox 8/9 coverage |
| Local MCP initialization and tool calls | `MCP_LOCAL_OK`, exit 0 | Initially local, before product discovery |
| Product MCP host and guest calls | Passed | This selected connection, not every Codex surface |
| Debian 13 VM, key/password login and Hello World HTTP | Passed | One infrastructure smoke test, no project commit |
| Revised guided installer | See local checks below | No new live host bootstrap claimed |
| Negative host keys, timeout recovery, session/reboot recovery | Still open | Never infer these from basic HTTP success |

The [live record](live-testproxmox.md) includes the original apt failure, approved
repair, installed versions, boot-order correction and actual observed limits.

## Local checks

From the repository root:

```bash
python3 -m unittest discover -s tests -v
bash -n scripts/bootstrap-debian.sh scripts/setup.sh scripts/install.sh
python3 scripts/check-upstreams.py --offline
python3 scripts/check-upstreams.py
git diff --check
```

Bootstrap tests cover Debian/Proxmox detection, incomplete-platform rejection,
CLI validation and the generated effective sshd configuration, when OpenSSH is
available. They start no services and run no apt operations. Guided-setup tests
cover secret-file permissions and overwrite refusal, tunnel-ID validation,
existing-runtime conflicts, strict readiness fields, native client command
construction, interrupted/resumed setup and subprocess error handling. Corrupt
artifact tests ensure a changed upstream archive is rejected.

For release 0.2.0, all 18 local tests passed, along with Bash syntax, ShellCheck,
37 local documentation targets, English/frontmatter checks and deterministic
release/source verification. All three real upstream downloads matched their
locked SHA-256 values.

The pinned 0.0.16 client help was inspected against the guide's actual flags. Its
real `init` command also generated an offline stdio profile using a file-secret
reference; no real key or control-plane call was used.
Private configuration tests use fake subprocess responses; that does not prove
account permissions, network availability or live tunnel polling. Documentation
links, skill frontmatter, archive contents and release checksums are checked
locally. The weekly workflow also fetches the fixed upstream artifacts.

## Earlier upstream checks

At slepp commit `37381ddc68a941b62ed8557dcbb5644dc3b6c5fd`, six existing upstream
unit tests passed: host-key modes through tool calls, stdio JSON-RPC round trip,
ensure-session reuse, view truncation, ranged view and repeated named-session
reuse. Additional local fake-SSH checks exercised stdout/stderr separation, exit 7,
timeout, bounded output and run resumption. These were local test doubles, not
real network host-key or product compatibility tests.

The original installer was syntax/ShellCheck checked and its generated client
configuration inspected with `ssh -G` without connecting. Both upstream archive
hashes were checked; arm64 metadata was inspected without running an arm64 binary.
Read this as historical evidence for that revision, not a blanket claim for later
code or all supported operating systems.

## Manual skill scenarios

- Find the documented admin alias before asking for another root password.
- Existing scoped authorization covers ordinary inventory/configuration/tests.
- Explicitly authorized first-contact TOFU persists the key, then uses strict
  checking. Without an expected machine ID, label first enrollment honestly.
- Missing TOFU authorization requires one focused question before connecting.
- Changed pins or known identity mismatches stop; no silent deletion/re-pinning.
- Exit 255 without supplied credentials does not establish password invalidity.
- Check saved boot order and disk attachment before boot; repair the assigned VM
  rather than create another on uncertainty.
- Inspect actual VLAN attachment; do not derive tags from subnet numbers.
- HTTP 200 with wrong content or incomplete provisioning is not task completion.

These are manual consistency scenarios, not an automated model behavior evaluation.

## Further live acceptance

Use an explicitly assigned connection in the intended product. Establish target,
account, trust mode, identity and permitted working/log area. For code tests also
supply checkout, SHA and the approved command. Then test bounded success/error/
timeout outputs, finite log reads, and exactly-once run recovery after a deliberate
observation interruption. Check process identity after timeout before retrying.
For a new host use preverification or explicitly authorized target-specific TOFU;
never damage an existing pin just to test a negative case. Record dates, versions,
run IDs, exit codes and limits without publishing private identifiers or secrets.

Published older downloads retain their original bytes, language and checksums.
The current English skill is in the source directory and the 0.2.0 download.
