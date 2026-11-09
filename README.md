# agent-dotfiles

This repository holds a multi-agent setup for [herdr](https://herdr.dev). Each herdr space (workspace) gets its own chief of staff (CoS) agent. The CoS plans the work in its space, and it starts and stops lead agents for that work. Each agent uses Claude Code or Codex at random, with a model that matches the task difficulty. The repository also adds herdr quick actions to open VS Code and to review code changes with a file viewer and the pi coding agent.

## Requirements

- herdr 0.9 or later, Python 3.10 or later, and git.
- Claude Code (`claude`), Codex (`codex`), or both. The default model table expects a [copilot-api](https://github.com/caozhiyuan/copilot-api) proxy on `localhost:4141`.
- pi (`npm install -g @earendil-works/pi-coding-agent`) for the review action.
- The GitHub CLI (`gh`), only if you use `install.sh --renderers`.

## Install

1. Clone this repository.
2. Run `./install.sh`. To also install the file viewer renderers (`delta`, `bat` and `glow`), run `./install.sh --renderers`.
3. Edit `~/agents/context.md`. This file tells every agent who you are and which rules apply to your repos. It stays on your machine and is not in git.
4. Open a new herdr space. The first tab starts the chief of staff.

The install script does these steps:

- It links `~/agents/bin`, `~/agents/roles`, `~/agents/models.json` and `~/agents/settings.json` to this repository. If a real file or directory is in the way, the script moves it to a `.bak-<time>` copy first.
- It installs and starts the `herdr-space-cos` systemd user service.
- It links the quick-actions plugin and installs the [herdr-file-viewer](https://github.com/smarzban/herdr-file-viewer) plugin at a reviewed commit.
- It adds the key bindings from `herdr/keys.toml` to your herdr config one time, after a backup.
- It copies the pi provider config to `~/.pi/agent/` if you do not have one, and it installs the herdr pi integration.

## How the chief of staff works

The service runs `agentctl watch`. The watcher listens for the herdr `workspace_created` event. For each new space, it starts an agent in the first pane and labels that tab `chief of staff`.

- The CoS works only in its own space. It ignores other spaces.
- The CoS decides which leads the space needs. It can start, expand, split, merge or retire a lead at any time.
- Each lead opens in its own tab. The tab label is a short task title, for example `review auth token refresh PR`. The title must contain a verb and an object, and it must be 40 characters or fewer.
- A lead can start worker, reviewer and researcher agents. These open as splits in the tab of the lead. The CoS can also start them directly.
- The CoS and the leads choose the child role by the verb. A researcher finds something out, a worker changes something, and a reviewer checks a change.
- Researchers and reviewers are read-only. Each one writes only to its own output directory, `~/agents/spaces/<workspace>/research/<agent>/` or `.../reviews/<agent>/`. A researcher can search the web, and it returns a report with an answer, a confidence level and cited evidence.
- Children report to their parent with `agentctl report`. The message goes into the parent pane.

### Decisions and alerts

Leads send decisions to the CoS. The CoS ends each turn with a "Needs you" list:

```
Needs you:
 D1 P2 auth-fix   Push the fix and re-run CI?   rec: yes  (default: wait)
```

Answer in the CoS pane, for example `D1 yes`. The CoS sends your answer to the lead that asked.

herdr alerts you when an agent is blocked on a question or a permission prompt. herdr does not alert for a normal end of turn. For this reason, the CoS runs `agentctl needs-you` when it adds new decisions. This command shows a herdr notification with the request sound.

### Watchdog

The watcher also follows every agent that `spawn` starts. `spawn` records each child in `~/agents/spaces/<workspace>/agents/<name>.json`, and `report` updates the time of its last report. The watchdog types a `[watch]` note into the parent pane in these cases:

- A child stays blocked on a dialog for 30 seconds. The parent then asks you through its "Needs you" list. It does not answer the dialog itself.
- A child ends a turn without a report.
- A child stops running, and its pane goes back to a shell.

If a chief of staff exits, or a parent cannot get the note, the watchdog shows a herdr notification to you.

### Restart and resume

herdr resumes agent panes after a server restart. herdr's own Claude and Codex integrations resume with only `claude --resume <id>` or `codex resume <id>`. That command loses the model, the permission mode, the settings, the role prompt and the agent environment. To prevent this, the watchdog reports a resume command for every agent that `agentctl` starts:

```
agentctl resume <agent> <session-id>
```

After a restart, herdr runs this command in the restored pane. `agentctl resume` reads the agent from the registry. It restores the `AGENT_*` environment, which includes the parent link, and starts the same vendor with the same arguments and the resume flag. `install.sh` links `agentctl` into `~/.local/bin`, because herdr needs a plain command name on `PATH`.

### Models

`agents/models.json` holds the model table. Each new agent gets a random vendor. The CoS or the lead chooses the tier for each agent.

| Tier | Claude | Codex | Use |
|---|---|---|---|
| `cos` | Sonnet, high effort | GPT-6.1 Sol, medium effort | Every chief of staff |
| `light` | Haiku | GPT-6 Luna | Lookups and mechanical edits |
| `standard` | Sonnet | GPT-6.1 Terra | Default for leads and workers |
| `heavy` | Opus | GPT-6.1 Sol | Hard debugging, design, root cause and security work |

If one vendor does not start, `agentctl` tries the other vendor.

### Safety

- Claude agents use auto permission mode and the deny rules in `agents/settings.json`. These rules block merges, force pushes, pushes to `main` or `master`, and herdr server and workspace control.
- Codex agents use `--approve-for-me`, which is automatic approval review. Codex does not read the Claude deny rules. The role prompts and the automatic review protect Codex agents.
- Researchers and reviewers cannot write outside their output directory:
  - A Codex researcher or reviewer runs in a workspace-write sandbox whose only writable root is the output directory. `/tmp` is excluded, and approvals are never granted.
  - A Claude researcher or reviewer gets its own settings file. That file denies edits to the repo, which also covers shell redirects and file commands, and it sets `blockWritesOutsideWorkingDirectories`. The output directory is the only other working directory.
- Agents never answer a folder-trust or permission dialog. When a dialog appears, the CoS asks you to answer it.
- Folder trust is separate for Claude and Codex. If Claude trusts a folder, a Codex agent gets a trust override for that session only. If only Codex trusts a folder, the agent uses Codex.

## Quick actions

| Key | Action |
|---|---|
| `prefix+shift+v` | Open the git root of the focused pane in VS Code |
| `prefix+f` | Open the file viewer in a split |
| `prefix+shift+f` | Open the file viewer in a tab |
| `prefix+alt+r` | Review changes: open a tab with the file viewer and a pi reviewer |

The review action writes the diff against the merge base with the default branch to a file. The diff includes committed and uncommitted changes, and the file lists untracked files. Then the action starts pi with read-only tools (`read`, `grep`, `find` and `ls`) and asks it for a summary and findings. To send notes to pi, mark lines in the file viewer with `a`, copy them with `A` and then `y`, and paste them into the pi pane.

## Commands

| Command | Use |
|---|---|
| `agentctl start-cos [workspace]` | Start a CoS in a space that already exists |
| `agentctl spawn lead\|worker\|reviewer\|researcher <slug> --title "<task>" --task -` | Start an agent (the CoS and leads use this command) |
| `agentctl report "<text>"` | Send a message to the parent agent |
| `agentctl needs-you "<text>"` | Alert the user that a decision is waiting |
| `agentctl ls` | List the agents in the current space |
| `agentctl resume <agent> <session-id>` | Start an agent again with its full settings (herdr runs this after a restart) |
| `systemctl --user stop herdr-space-cos` | Stop new spaces from getting a CoS |

## Layout

| Path | Contents |
|---|---|
| `agents/bin/agentctl` | The watcher and the agent commands |
| `agents/roles/` | Role prompts for the chief of staff, leads, workers, reviewers and researchers |
| `agents/context.example.md` | A template for your personal `~/agents/context.md` |
| `agents/models.json` | Vendors, tiers and models |
| `agents/settings.json` | Deny rules for Claude agents |
| `herdr/quick-actions/` | The herdr plugin for the VS Code and review actions |
| `herdr/keys.toml` | Key bindings that `install.sh` adds to your herdr config |
| `pi/` | pi providers for the copilot-api proxy |
| `systemd/` | The watcher service |
| `install.sh` | The install script |

Runtime state stays in `~/agents` and is not in git: `context.md`, `spaces/<workspace>/` (roster, decisions and preferences) and `.build/` (merged role prompts).
