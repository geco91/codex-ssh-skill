# Use the existing tools

These names were verified in the documented upstream versions, not guaranteed
for the current connection. Read its actual schemas first.

| Capability | slepp/ssh-mcp | tufantunc/ssh-mcp v2 |
| --- | --- | --- |
| Bounded command | `ssh_exec` | `read-command`, `run-command` |
| Find a session | `ssh_list_sessions` | `list-sessions` |
| Open/reuse a session | `ssh_ensure_session` | `open-session` |
| Read output | `ssh_read_session` | `read-session-output` |
| Read part of a file | `ssh_view` with `view_range` | Inspect the offered file/read tool |

## Short commands

First establish the [target and trust mode](access.md). Normally use `ssh_exec`
with the assigned `target`, `cwd`, `strict_host_key_checking: "yes"`, the MCP
host's known_hosts file, `timeout: 10` and `tty: false`.
`extra_ssh_args: ["-o", "BatchMode=yes", "-o", "ConnectTimeout=5"]` avoids
unattended authentication and long connection waits. Read targets and paths from
configuration rather than guessing. For explicitly authorized TOFU, use
`accept-new` for the first identity call, then `yes`. Reuse existing alias setup.
Evaluate `stdout`, `stderr`, `exit_code` and `timed_out` separately. Exit 255
usually indicates SSH/transport failure, not a failing project test.

The inspected `ssh_exec` schema has no general output-cap argument. Redirect
potentially large output into a protected file in the authorized working area,
then read finite `ssh_view` ranges, such as `view_range: [1, 100]`. A single line
can still be huge: use an existing byte-limited reader or `head -c` as needed.
Writing those logs must be covered by the task scope.

## Longer tests and resumption

1. In the intended checkout record `git rev-parse HEAD` and `git status --porcelain`.
   Compare the SHA to the task. Preserve unrelated edits. Missing code transfer
   is a separate gap; never silently test a different checkout. “Local” upload
   paths refer to the MCP host, not necessarily the Codex cloud checkout.
2. Prefer an existing runner with run ID and status. Otherwise use an existing
   MCP session. With slepp first call `ssh_list_sessions` for the target and a
   stable `session_name`. `ssh_ensure_session` can create a missing session;
   reuse alone does not prove that a previous test ended. Session IDs survive
   only until the MCP server restarts.
3. For a new run use a unique run ID and a new private results directory. Start
   the intended test once, redirect stdout and stderr separately, and record
   shell PID, start time/process identity and tested SHA. Save the actual test
   exit code immediately afterward in a status file, preferably with atomic
   rename. Starting a background process is not test success. Use a small
   task-specific shell sequence, not another universal runner implementation.
4. Read briefly: for example `ssh_read_session` with `wait_seconds: 1` and
   `max_output_chars: 4096`. Account for pending output, truncation and losses.
   A PTY may merge streams; separate log files remain authoritative. A returned
   shell prompt does not establish a test exit code.
5. After interruption inspect stored run data, sessions, status and process.
   A PID can be reused: compare start time, command, working directory and run ID.
   Observe a matching live process; evaluate an existing terminal result. If the
   process/session is gone without a final status, report **unknown** and resolve
   the old run before starting another. New attempts need new run IDs.

An MCP session does not guarantee survival across tunnel/server restarts. Use
an already available durable runner/tmux/systemd workflow if required; otherwise
report the limitation. A timeout may leave the remote process alive. Stop only
the clearly assigned run within scope, never with a global `pkill`.

## Report the evidence

`Target alias | SHA (+ dirty when applicable) | test/run ID | success/failure/timeout/unknown`

Include trust mode (preverified / TOFU first enrollment), exit code or “unavailable”,
short stdout/stderr evidence, output completeness and local log references.
Keep raw identities and secrets private. For ongoing runs report “unknown, still
running” and the next bounded check. A timeout concerns that operation's limit,
not necessarily the remote test's lifetime.

For infrastructure/webserver setup, record image version and checksum instead
of inventing a code SHA. Establish provisioning completion, guest identity,
actually tested login methods, HTTP status and the expected page content.
