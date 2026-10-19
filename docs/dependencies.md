# Pinned dependencies and integrity checks

The machine-readable source of the published pins is
[`dependencies.lock.json`](../dependencies.lock.json). The standalone bootstrap
also embeds the same values so it can be inspected and used independently.
The verification command rejects drift between that lock and the actual installer.

| Dependency | Pinned version | Integrity |
| --- | --- | --- |
| [slepp/ssh-mcp](https://github.com/slepp/ssh-mcp) | Package 0.2.0; commit `37381ddc68a941b62ed8557dcbb5644dc3b6c5fd` | Full source archive SHA-256 |
| [openai/tunnel-client](https://github.com/openai/tunnel-client) | 0.0.16 | Separate amd64/arm64 release-archive SHA-256 |
| Guided installer bundle | Repository release 0.3.0 | SHA-256 embedded in its versioned launcher |
| GitHub Actions checkout | Full commit in the workflow | No floating action tag |

SHA-256 values are in the lock file; do not replace them just because a download
fails. An archive changing at the same commit/release URL causes a hard failure
before that artifact is installed. Re-running the bootstrap also verifies the
retained SSH-MCP source archive. This does not hash every installed Python file
or establish that a running process has not been modified.

## Verify the pins

```bash
# Lock/schema and actual installer agree; no downloads:
python3 scripts/check-upstreams.py --offline

# Fetch the fixed upstream URLs and verify their bytes:
python3 scripts/check-upstreams.py
```

Build versioned downloads with `python3 scripts/package-release.py --version 0.3.0`
and verify them against the source with the same command plus `--check`. The
builder refuses to replace different existing versioned download bytes; use a
new release version for published changes. The generated launcher embeds the
installer archive hash, so it is intentionally outside that archive.

The repository workflow runs the same verification on pushes, pull requests,
manual dispatch and a weekly schedule. It fails on changed/unavailable upstream
bytes; notifications use your GitHub Actions notification preferences. Nothing
rewrites the lock or upgrades installations automatically. New upstream releases
can exist without changing the pinned artifact and do not trigger a checksum
failure; reviewing new versions is a separate maintenance decision.

For an intentional update: inspect upstream changes and provenance, record the
new full commit/version and expected hash, update bootstrap and lock together,
run tests and artifact verification, then publish a new versioned installer.
The official tunnel guide recommends keeping up with supported client releases;
this project deliberately requires a reviewed version bump rather than a floating
`latest` installation. Existing pinned clients may need such an update later.

## Reproducibility limits

The initial HTTPS launcher must itself be trusted; its embedded hash verifies the
bundle, not an independent publisher signature. Likewise HTTPS plus a pinned
archive hash is not a new upstream signature-verification claim. Signed apt
repositories and pip build tooling still supply dependencies that are not fully
locked here. `--no-upgrade` does not prevent all transitive apt changes.

Published versioned downloads are immutable in this project. Older skill ZIPs
retain their original language and behavior; current English source and downloads
are in release 0.2.0. Do not rewrite old archive bytes or old checksums.
