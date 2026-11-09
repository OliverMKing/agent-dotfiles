# User context (example)

Copy this file to `~/agents/context.md` and edit it. `agentctl` appends it to every agent's
role prompt. It is personal, so it is not in git. Delete sections that you do not need.

## Who the user is

- Name: <your name>
- Role and main areas: <for example: backend engineer on the payments service>

## Memories and notes

- Memory index: <path, for example ~/.claude/projects/<your-home-path>/memory/MEMORY.md>
- Format: <how a memory file looks, or "one Markdown file per fact with frontmatter">
- Read the index before you start, especially feedback entries about how the user wants work done.

## Repo rules

- <repo>: make worktrees from <path>; never clone it again.
- <repo>: commit message format, PR description template, build or lint quirks.

## Useful skills and tools

- <skill or CLI>: <when to use it>
