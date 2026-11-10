"""Open a 'review' tab: file viewer on the changes (left) + a read-only Claude or Codex reviewer (right)."""
import os
import random
import re
import subprocess
import sys
import time

sys.path.insert(0, ".")
from common import HERDR, focused_root, git, herdr, notify  # noqa: E402

# Standard tier, random vendor (matches ~/agents/models.json "standard"). Both run read-only:
# Claude in plan mode (no edits or changing commands), Codex in its read-only sandbox.
REVIEWERS = {
    "claude": ["--model", "sonnet", "--effort", "high", "--permission-mode", "plan"],
    "codex": ["--no-daemon", "-m", "gpt-6.1-terra", "-c", 'model_reasoning_effort="high"', "-s", "read-only",
              "-a", "never", "-c", "check_for_update_on_startup=false"],
}

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

# 2. a read-only reviewer beside it, asked to review.
review_pane = herdr("pane", "split", viewer, "--direction", "right", "--cwd", root, "--no-focus")["pane"]["pane_id"]
herdr("pane", "rename", review_pane, "reviewer")
vendor = os.environ.get("REVIEW_VENDOR") or random.choice(list(REVIEWERS))  # override for tests
name = f"review-{wid.lower()}-{stamp[-6:]}"
try:
    herdr("agent", "start", name, "--kind", vendor, "--pane", review_pane, "--timeout", "60000",
          "--", *REVIEWERS[vendor])
except RuntimeError as e:
    if "agent_not_ready" not in str(e):
        notify("Review changes", f"the {vendor} reviewer did not start: {e}")
        sys.exit(1)
    # still starting, or waiting on a folder-trust dialog: give the user up to 3 minutes to answer it
    notify("Review changes", "If the reviewer pane asks whether to trust this folder, answer it there.")
    try:
        herdr("agent", "wait", name, "--until", "idle", "--until", "done", "--timeout", "180000")
    except RuntimeError:
        notify("Review changes", "The reviewer never became ready.")
        sys.exit(1)

prompt_text = f"""Review the code changes in {root} (branch {branch}).
The full diff against {default} (merge-base {base[:12]}) is in {diff_path}; read it first.
Untracked files are listed at the end of that file; read them directly if relevant.

1. Summary: what changed, grouped by file or feature, in a few lines.
2. Findings, most severe first, each with file:line, the concrete failure, and a suggested fix:
   correctness bugs, risky or surprising changes, missing or weak tests, then minor issues.
Skip style nits. You are read-only: do not modify anything.
Then wait. The user may paste notes from the file viewer (lines marked with `a`, copied with `A` then `y`)."""
herdr("agent", "prompt", name, prompt_text)
# a long pasted prompt can stay unsent in the input box: if the reviewer did not start, press Enter
time.sleep(4)
if herdr("agent", "get", name)["agent"]["agent_status"] not in ("working", "blocked"):
    subprocess.run([HERDR, "agent", "send-keys", name, "enter"], capture_output=True)
notify("Review changes", f"{repo}: {vendor} reviewing vs {default}")
print(name, vendor, diff_path)
