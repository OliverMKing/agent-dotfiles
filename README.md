# agent-dotfiles

This repository holds a farm-flavored multi-agent setup for [herdr](https://herdr.dev). Each herdr space (workspace) is a field. Each field gets its own lead farmer, which is a chief of staff (CoS) agent. The lead farmer plans the work in its field, and it starts and stops farmers (lead agents) for that work. Farmers give bounded tasks to animals (single-use child agents).

| Farm name | Agent role | `agentctl` role | Animal on the farm page |
|---|---|---|---|
| Lead farmer | Chief of staff, one for each space | `chief-of-staff` | 👩‍🌾 at the farmhouse |
| Farmer | Lead for one area of work | `lead` | 🧑‍🌾 in a plot |
| Horse | Worker that changes something | `worker` | 🐴 |
| Dog | Researcher that finds something out (read-only) | `researcher` | 🐕 |
| Goose | Reviewer that checks a change (read-only) | `reviewer` | 🪿 |
| Specialist animal | A worker, researcher or reviewer with a specialty | the base role | its own species |

In this README, "CoS" and "lead farmer" mean the same agent, and "lead" and "farmer" mean the same agent. Each agent uses Claude Code or Codex at random, with a model that matches the task difficulty. The repository also adds herdr quick actions to open VS Code and to review code changes with a file viewer and the pi coding agent.

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

## The farm page

The `herdr-farm` service serves a live view at http://127.0.0.1:8787. It listens only on your machine, because it shows agent screens.

- Each space is a field with a farmhouse for its lead farmer and a fenced plot for each farmer. The animals of a farmer stand in its plot.
- An agent bobs or trots when it works, shows 💤 when it is idle, and shows ❗ when it is blocked on a dialog.
- The bar under an agent is a hay bale that shows how full its context is.
- A "Needs you" panel at the top of the page lists everything that needs you, in every field, most urgent first:
  - open decisions;
  - agents that wait on a dialog (for example folder trust or a permission prompt);
  - an unsent draft of yours that holds messages back;
  - a lead farmer that stopped.
- The counters at the top are buttons. "Need you" jumps to the "Needs you" panel. "Messages waiting" jumps to the agent that the messages are for. A 📬 badge marks each agent with waiting messages.
- Each item has a "Show me" button that switches herdr to the right pane. The browser tab title shows the count, and "Notify me" turns on desktop notifications for new items.
- The page and the agent messages name a location as workspace › tab › pane, for example "GlobalGatewayController" › tab "fix Private Link approval". They do not use herdr IDs such as `w1:pG`.
- Click an agent to see its details. A "Now:" line shows what it does at the moment, for example "Running: go test ./..." or "Editing: reconciler.go", from its latest tool call or note. A farmer or an animal also has a "Messages" view, with labeled messages: its task, messages from its parent, your messages, reports from its animals, its own reports, and its replies. Tool output is left out. The raw terminal is still available, collapsed.
- A quota bar at the top shows the Copilot premium credits used this month, from the `/usage` endpoint of the copilot-api proxy. A marker shows how much of the month has passed. The bar turns amber when the use is ahead of that pace or above 80%, and red when the quota is used up. The farm sends only the quota numbers to the page. Set `AGENTCTL_PROXY_URL` if the proxy is not on `http://localhost:4141`.

## Decisions

The lead farmer records each question for you with `agentctl ask`. `agentctl` assigns the ID (D1, D2 and so on), shows a herdr notification, shows the count in the pane title of the lead farmer ("lead farmer · needs you: 2"), and lists the question on the farm page. Answer in the pane of the lead farmer, for example `D1 yes`. The lead farmer forwards your answer and closes the item with `agentctl resolve`. It ends every turn with the output of `agentctl decisions`, so the open questions are always the last lines in its pane.

## Specialist animals

A specialty is a reusable specialist, for example a telemetry analyst or a CI babysitter. Define it one time in `~/agents/specialties/<name>.md`:

```
---
role: researcher
animal: owl
description: Answers telemetry questions with KQL
---
Focus, tools and skills to use, sources to trust, and the exact output format.
```

Start it with `agentctl spawn researcher <slug> --specialty <name> ...`. The specialty adds its text to the role prompt. It never adds permissions, because the base role sets them. If the file names no animal, `agentctl` picks a species from the name, so the same specialist always looks the same. `agentctl specialties` lists the specialties.

## How the chief of staff works

To convert a space that existed before the service started, run `agentctl adopt` for each agent that you started by hand, then run `agentctl start-cos <workspace>`. Then tell the chief of staff about the adopted leads. If the space has no free pane, open a new tab first.

The service runs `agentctl watch`. The watcher listens for the herdr `workspace_created` event. For each new space, it starts an agent in the first pane and labels that tab `lead farmer`.

- The CoS works only in its own space. It ignores other spaces.
- The CoS decides which leads the space needs. It can start, expand, split, merge or retire a lead at any time.
- Each lead opens in its own tab. The tab label is a short task title, for example `review auth token refresh PR`. The title must contain a verb and an object, and it must be 40 characters or fewer.
- A lead can start worker, reviewer and researcher agents. These open as splits in the tab of the lead. The CoS can also start them directly.
- The CoS and the leads choose the child role by the verb. A researcher finds something out, a worker changes something, and a reviewer checks a change.
- Researchers and reviewers are read-only. Each one writes only to its own output directory, `~/agents/spaces/<workspace>/research/<agent>/` or `.../reviews/<agent>/`. A researcher can search the web, and it returns a report with an answer, a confidence level and cited evidence.
- Children report to their parent with `agentctl report`. The report goes to an inbox file, `~/agents/inbox/<parent>.jsonl`. The watcher types it into the parent pane only when the parent's input box is empty and the parent is not blocked on a dialog. A busy parent still gets it: Claude queues it, and Codex takes it into the current turn. If you have a draft in the pane, the messages wait. They do not cut into your typing. Messages that wait arrive together as one message. If a draft holds messages back for 10 minutes, you get a notification.
- Workers, reviewers and researchers are single-use. A child sends its last report with `agentctl report --final`. After the watcher delivers that report, it marks the child done and closes its pane. A sandboxed agent that cannot write the inbox writes `outbox.jsonl` in its output directory instead, and the watcher moves the messages from there. A parent never sends a second task to a finished child. It starts a new one and gives it the earlier output.
- A lead owns its area. It plans, delegates, integrates and verifies. It does small tasks itself and gives longer, parallel or context-heavy tasks to fresh children. Only one agent edits a worktree at a time.
- The CoS refreshes a lead at a new phase, after a major milestone, or when the context of the lead is more than about 60% full. The old lead writes `handoff.md`, and a new lead starts from it.
- Before a lead asks to push, merge or post, a fresh reviewer checks the change. The decision includes the path of the findings file.
- If the watcher was down when a space was created, it starts the CoS when it reconnects.

### A clean conversation with the lead farmer

Reports from farmers do not go into the conversation that you have with the lead farmer. When reports wait, the watcher types only one short line into its pane: `📬 N new report(s) from <names>. Read them with: agentctl inbox`. The lead farmer reads them with `agentctl inbox`, and it tells you about them only when something changed for you. It gets a new nudge only after it reads the earlier reports.

You can also type to any agent from the farm page. The details panel of each agent has a message box, and the text goes into its pane as if you typed it there. The page does not send while you have unsent text in the terminal input of that agent, or while the agent waits on a dialog. Each decision on the "Needs you" board has an "Accept rec" button, which sends "D3: yes, go with your recommendation". It also has a "Reply…" button, which opens the lead farmer with "D3 " filled in.

On the farm page, click the lead farmer to see "Your conversation". This view shows only your messages and its replies to them. It reads them from the transcript of the lead farmer and leaves out reports, watchdog notes, nudges and tool output. The full live screen is still available below the conversation.

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

### Context size

Large contexts make every turn slower and more expensive, and they lower quality. The watcher reads the token use of each agent from its own transcript. For Claude, it reads `~/.claude/projects/*/<session>.jsonl`. For Codex, it reads `~/.codex/sessions/**/<session>.jsonl`. It then acts in this order:

1. When an agent is idle and its context is more than `compact_at_tokens` (100k) or `compact_at_fraction` (40%) of its window, the watcher sends `/compact`. For Claude, the command says what to keep. The watcher never types over a draft.
2. After `max_compactions` (2), the watcher tells the CoS to refresh the lead. The lead writes `handoff.md`, and a new lead starts from it.
3. For a CoS, the watcher clears its context (`/clear` or `/new`). Then it tells the CoS to rebuild from `roster.md`, `decisions.md`, `charters/` and the registry. For this reason, the CoS keeps these files current at the end of every turn.

Workers, reviewers and researchers are single-use, so their contexts stay small. `agentctl ls` shows the context size and compaction count of each agent. The limits are in the `context` section of `agents/models.json`.

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
| `agentctl adopt <pane> <slug> --title "<task>"` | Make an agent that you started by hand a lead of the space's CoS. It keeps its own launch options when herdr resumes it. |
| `agentctl report --as <name> "<text>"` | Send a report as an adopted agent, whose shell can lack the `AGENT_*` environment |
| `agentctl ask --lead <who> --question "..." --rec "..." --default "..."` | Record a decision for you (the lead farmer uses this) |
| `agentctl resolve D<n> --answer "..."` | Close a decision |
| `agentctl decisions` | Print the open decisions |
| `agentctl specialties` | List specialist animals |
| `agentctl farm` | Serve the farm page (the `herdr-farm` service runs it) |
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
| `agents/farm/index.html` | The farm page |
| `systemd/` | The watcher service and the farm service |
| `install.sh` | The install script |

Runtime state stays in `~/agents` and is not in git: `context.md`, `spaces/<workspace>/` (roster, decisions and preferences) and `.build/` (merged role prompts).
