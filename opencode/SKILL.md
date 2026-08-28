---
name: opencode
description: "Run local OpenCode only when the user invokes this skill."
disable-model-invocation: true
license: MIT
metadata:
  version: "2.3.0"
  platforms: "linux,macos,windows"
  source: "https://github.com/NousResearch/hermes-agent"
---

# OpenCode for Codex Skill

Run the local OpenCode CLI as a coding worker while the host Agent remains responsible for scope, permissions, verification, and reporting. The workflow is Codex-first but maps to Claude Code and other Agents that can run and monitor terminal commands.

## When to Use

Run this Skill only when the user explicitly invokes it or explicitly says to use OpenCode. A coding, review, refactoring, or delegation request that does not name OpenCode is not sufficient. Never choose OpenCode autonomously.

## Prerequisites

Assume OpenCode is already installed and authenticated. Do not install, upgrade, uninstall, authenticate, or reconfigure OpenCode. If the executable is missing or authentication fails, report the blocker and stop.

## How to Run

### Choose the execution mode

Use `opencode run` by default, including for long tasks that do not need input while they run. The process exits when that turn finishes; the OpenCode session remains available for later continuation.

Use a persistent TUI only when OpenCode needs live answers, approvals, or direction before the current turn can finish. A task being long is not by itself a reason to use the TUI.

### Build the command

Run in the exact working directory authorized by the user. Prefer the host terminal tool's working-directory option; if it has none, use OpenCode's `--dir` option instead of shell-specific `cd` chains.

Basic run:

```text
opencode run "<task>"
```

With files, model, and reasoning effort:

```text
opencode run --file "<path>" --model "<provider>/<model>" --variant "<effort>" "<task>"
```

Apply options with these rules:

- User-specified values always win. Otherwise leave the option out and use OpenCode's configured default.
- OpenCode selects a Provider through `--model provider/model`. If the user gives Provider and model separately, combine them once.
- If only a Provider is given, run `opencode models <provider>`. Select a model only if the result and user intent make it unique; otherwise ask the user.
- Treat `--variant` as Provider-specific Effort. Do not invent a value or silently downgrade an unsupported value.
- Keep `--thinking` off unless the user explicitly asks to see thinking output. Effort does not imply `--thinking`.
- Use `--pure` only when the user requests a plugin-free run or observed evidence shows plugin interference.
- Repeat `--file` for multiple attachments. Preserve spaces by quoting each path.
- Give OpenCode the compact delegation brief and final handoff below.

### Build a delegation brief

Compile the user's latest approved intent instead of copying the conversation. Preserve every hard requirement, prohibition, acceptance criterion, and named file or interface. Remove history, repetition, and abandoned alternatives before compressing approved requirements.

For conflicting task content, apply this order: the user's latest explicit override, the referenced specification or design, repository documentation and conventions, then the minimum assumptions OpenCode needs. This order does not override host instructions, permission boundaries, or missing authorization.

If an approved specification, issue, or design file exists, pass its exact path or attach it with `--file` as `SOURCE_OF_TRUTH`; add only the current task and explicit overrides. Otherwise use only the applicable parts of this structure:

```text
OBJECTIVE
<one observable outcome>

REQUIREMENTS
1. <required result or acceptance criterion>

ALLOWED_SCOPE
<files, modules, or operations that may change>

OUT_OF_SCOPE
<explicit exclusions>

VERIFICATION
<commands or observable success criteria>
```

Pass a short brief directly as the task argument. If no specification exists and the brief is long, multiline, or fragile to quote in the current shell, put it in one uniquely named host temporary Markdown file outside the repository, attach it with `--file` as `DELEGATION_BRIEF`, and remove only that exact file after the run.

Unless the user explicitly authorizes otherwise, direct OpenCode to preserve existing user changes, stay within scope, and avoid commit, push, or sharing. Resolve ambiguities that would materially change the result with the user before launch. If a new material ambiguity appears during execution, OpenCode must stop and report it; record smaller necessary assumptions in the final handoff.

### Require a compact final handoff

End every coding prompt with this requirement:

```text
Finish with one concise OPENCODE_FINAL_REPORT, normally about 1,000–1,500 tokens:
- status: complete, partial, or blocked
- summary: at most five outcome bullets
- changed_files: every handwritten file and its purpose; group generated files
- verification: each command actually run and PASS/FAIL
- review_first: at most five path:symbol-or-section locations and why they matter
- remaining: unresolved work or risks, or none
- assumptions: necessary assumptions made during execution, or none
Do not include full diffs, full logs, or a process narrative.
Return only this report block, with no text before or after it.
Exceed the target only to preserve a complete changed-file list, failed checks, or high-risk review guidance.
```

This report is an index for verification, not proof that the work is correct.

If a required field is missing, `status` is invalid, or any text appears outside the report block, continue the same session once with: `Return only a corrected OPENCODE_FINAL_REPORT. Do not repeat or rerun the task.` Do not request a second correction; verify the workspace directly instead.

### Continue a conversation

For work likely to need follow-up, add a concise unique `--title` and `--format json`, extract the exact `sessionID` from the event stream, and retain the title, ID, and compact status summaries. Do not copy the full JSON stream into the host Agent's context.

Continue a known session with:

```text
opencode run --session "ses_..." "<follow-up>"
```

Prefer the recorded ID over `--continue`; the latter can attach to an unrelated most-recent session. Use `--fork` with `--session` only when the user wants a new branch of the conversation.

Keep these identifiers separate:

- The host process handle identifies the currently running OS process and becomes invalid after exit.
- The OpenCode `ses_...` ID identifies the durable conversation and can be resumed by a later process.

### Monitor long tasks without consuming excess context

In Codex, start the command with `exec_command` in the target `workdir`. If it returns a live process/session handle, poll it with `write_stdin` using empty input. Other Agents should use their equivalent background-process and bounded-log tools.

- For a run expected or observed to exceed about five minutes, or one producing dense output, redirect raw output to a host-managed temporary log outside the repository. This needs shell redirection, not a script.
- Check the process about every 45–60 seconds. Read output only on a state change, user request, silence diagnosis, or completion; cap each read at about 500–1,000 tokens or the newest 20–50 lines. Loading then summarizing raw logs does not recover host context.
- Continuing output or a growing log shows activity. After three silent checks, verify the process and log timestamp or size, then inspect only its newest output; silence alone does not justify termination.
- Wait while the process is alive and no contrary evidence exists. Stop on normal exit, an unrecoverable error, repeated unresolved permission input, user cancellation, or an agreed time budget.
- On completion, extract the session ID and report, remove the exact temporary log unless the user wants it, and verify files and tests. These limits save host context, not OpenCode Provider tokens.

### Use the interactive TUI only when necessary

Start `opencode` with a pseudo-terminal and keep the host process handle. In Codex this means `exec_command` with `tty: true`, followed by `write_stdin` for input and bounded output reads. Other Agents must map this to an equivalent PTY-capable terminal tool.

Send `Ctrl+C` to exit cleanly. Do not type `/exit`; it is not a reliable exit command. Force termination only for cancellation or a process that is demonstrably unresponsive.

## Quick Reference

| Option | Purpose |
|---|---|
| `run "<task>"` | Execute one turn, then exit the process |
| `--session <id>` / `-s` | Continue an exact OpenCode session |
| `--continue` / `-c` | Continue the most recent session when unambiguous |
| `--fork` | Branch a continued session |
| `--model provider/model` / `-m` | Select Provider and model |
| `--variant <value>` | Select Provider-specific reasoning Effort |
| `--agent <name>` | Select an OpenCode Agent |
| `--file <path>` / `-f` | Attach a file; repeat for multiple files |
| `--format json` | Emit machine-readable events for session capture |
| `--pure` | Exclude external plugins for requested or diagnosed plugin-free runs |
| `--thinking` | Show thinking blocks when explicitly requested |
| `--title <name>` | Give a session a recognizable title |
| `--attach <url>` | Use an existing server supplied by the user |
| `--dir <path>` | Set the project directory when the host cannot |
| `--auto` | Auto-approve allowed permissions; never enable by default |
| `--share` | Share a session; never enable without explicit authorization |

Useful management commands:

```text
opencode session list
opencode stats --days 7 --models 10
opencode models <provider>
```

`opencode stats --models` accepts a count or no value; it does not accept a model name.

## Procedure

1. Pass the invocation gate, identify the working directory, scope, source of truth, deliverables, and requested options, then resolve material ambiguity.
2. Record version-control status before launch when available; otherwise inventory the authorized paths. Treat every pre-existing changed or untracked path as a protected baseline and do not attribute it to OpenCode later.
3. Choose the execution mode, compile the brief, append the handoff requirement, and run with only required flags; monitor with bounded reads.
4. After exit, compare the baseline, current status, diff statistics, and report. Apply the one-correction rule if needed, inspect `review_first`, and run proportionate tests; read the full diff only for discrepancies, failures, or high-risk changes.
5. Report the captured title and session ID, actual changed files, verification, incomplete work, and risks.

## Special Workflows

### Pull request review

`opencode pr <number>` fetches and checks out that PR before opening OpenCode. Use it only in the intended repository, with a safe working tree, and with a pseudo-terminal:

```text
opencode pr <number>
```

If isolation is needed, use a clone or worktree already prepared or explicitly authorized by the user. Do not create or delete isolation directories implicitly.

### Parallel work

Run parallel OpenCode processes only when the user explicitly requests parallel execution. Give every process a separate working directory or worktree and a non-overlapping task. Never run multiple editing sessions against the same working tree.

## Platform Notes

The OpenCode command and flags above are the same on macOS, Linux, and Windows. Avoid Bash-only variables, command substitutions, pipelines, and temporary-directory one-liners in portable instructions.

For long-run logs, use a unique file under the host system's temporary directory, outside the repository: `$TMPDIR` or `/tmp` on macOS/Linux, and `$env:TEMP` in PowerShell. Use that shell's native output redirection and remove only the exact log created for the run.

Do not resolve the binary on every run. Only when `opencode` is not found or behavior suggests a PATH mismatch, diagnose without changing the system:

macOS or Linux shell:

```text
command -v opencode
which -a opencode
opencode --version
```

Windows PowerShell:

```text
Get-Command opencode -All
opencode --version
```

If Windows is using WSL, follow the macOS/Linux-style shell commands inside WSL. When a resolved absolute executable path is required, use the path returned by the current host instead of guessing an installation directory.

## Verification

Start with the smallest reliable verification surface:

- The process exit status is known.
- Baseline and current version-control status or scoped file inventory account for every reported file and pre-existing change.
- Reported `review_first` files and symbols contain the intended change.
- Relevant focused tests pass; broader tests run when the risk warrants them.
- Generated or plugin state such as `.omo` is distinguished; clean only artifacts created by the current run.
- No unauthorized commit, push, share, or out-of-scope modification occurred.

Do not run a model-backed smoke test before every task. Use `opencode --version` only for diagnosis, and run an OpenCode smoke prompt only when the user asks to troubleshoot execution.
