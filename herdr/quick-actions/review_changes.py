"""Open a 'review' tab: file viewer on the changes (left) + a read-only pi reviewer (right)."""
import os
import random
import re
import subprocess
import sys
import time

sys.path.insert(0, ".")
from common import focused_root, git, herdr, notify  # noqa: E402

# Standard tier, random vendor (matches ~/agents/models.json "standard").
PI_MODELS = ["copilot-claude/claude-sonnet-5-5", "copilot-openai/gpt-6.1-terra"]
PI_TOOLS = "read,grep,find,ls"  # read-only: pi has no permission prompts

_, wid, root = focused_root()
if not git(root, "rev-parse", "--git-dir"):
    notify("Review changes", f"Not a git repo: {root}")
    sys.exit(1)

# Baseline = merge-base with the default branch (same default as the viewer's `b` toggle).
default = git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD") or "origin/main"
base = git(root, "merge-base", "HEAD", default) or "HEAD"
branch = git(root, "branch", "--show-current") or "HEAD"
repo = os.path.basename(root)

state = os.environ.get("HERDR_PLUGIN_STATE_DIR") or "/tmp"
stamp = time.strftime("%Y%m%d-%H%M%S")
diff_path = os.path.join(state, f"review-{repo}-{stamp}.diff")
diff = subprocess.run(["git", "-C", root, "diff", "--stat", "--patch", base],
                      capture_output=True, text=True).stdout
untracked = git(root, "ls-files", "--others", "--exclude-standard")
with open(diff_path, "w") as f:
    f.write(f"# repo: {root}\n# branch: {branch}\n# base: {default} merge-base {base}\n")
    f.write("# includes committed + uncommitted changes to tracked files since base\n\n")
    f.write(diff or "(no changes to tracked files)\n")
    if untracked:
        f.write("\n# untracked files (contents not inlined; read them directly):\n")
        f.write("\n".join(f"#   {p}" for p in untracked.splitlines()) + "\n")
if not diff and not untracked:
    notify("Review changes", f"No changes in {repo} vs {default}")
    sys.exit(0)

# 1. File viewer in a new tab, rooted at the repo.
opened = herdr("plugin", "pane", "open", "--plugin", "herdr-file-viewer", "--entrypoint", "file-viewer",
               "--placement", "tab", "--workspace", wid, "--cwd", root,
               "--env", f"HERDR_FILE_VIEWER_ROOT={root}", "--focus")
viewer = (opened.get("pane") or {}).get("pane_id") or opened.get("pane_id")
if not viewer:  # fall back: newest pane in the workspace
    panes = herdr("pane", "list", "--workspace", wid)["panes"]
    viewer = max(panes, key=lambda p: int(p["pane_id"].split(":p")[-1]))["pane_id"]
tab = herdr("pane", "get", viewer)["pane"]["tab_id"]
herdr("tab", "rename", tab, re.sub(r"[^A-Za-z0-9._-]", "-", f"review-{repo}")[:32])
herdr("pane", "rename", viewer, "files")

# 2. pi beside it, read-only, asked to review.
pi_pane = herdr("pane", "split", viewer, "--direction", "right", "--cwd", root, "--no-focus")["pane"]["pane_id"]
herdr("pane", "rename", pi_pane, "pi review")
model = random.choice(PI_MODELS)
name = f"review-{wid.lower()}-{stamp[-6:]}"
try:
    herdr("agent", "start", name, "--kind", "pi", "--pane", pi_pane, "--timeout", "60000",
          "--", "--model", model, "--thinking", "medium", "--tools", PI_TOOLS)
except RuntimeError as e:
    notify("Review changes", f"pi did not start: {e}")
    sys.exit(1)

herdr("agent", "prompt", name, f"""Review the code changes in {root} (branch {branch}).
The full diff against {default} (merge-base {base[:12]}) is in {diff_path}; read it first.
Untracked files are listed at the end of that file; read them directly if relevant.

1. Summary: what changed, grouped by file or feature, in a few lines.
2. Findings, most severe first, each with file:line, the concrete failure, and a suggested fix:
   correctness bugs, risky or surprising changes, missing or weak tests, then minor issues.
Skip style nits. You are read-only: do not try to modify anything.
Then wait. The user may paste notes from the file viewer (lines marked with `a`, copied with `A` then `y`).""")
notify("Review changes", f"{repo}: {model.split('/')[1]} reviewing vs {default}")
print(name, model, diff_path)
