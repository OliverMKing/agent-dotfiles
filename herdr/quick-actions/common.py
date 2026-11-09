import json
import os
import subprocess

HERDR = os.environ.get("HERDR_BIN_PATH", "herdr")


def herdr(*args):
    r = subprocess.run([HERDR, *args], capture_output=True, text=True)
    try:
        d = json.loads(r.stdout or r.stderr or "{}")
    except ValueError:
        d = {"raw": r.stdout + r.stderr}
    if r.returncode != 0 or "error" in d:
        raise RuntimeError(f"herdr {' '.join(args)}: {d.get('error', d)}")
    return d.get("result", d)


def notify(title, body=None):
    args = ["notification", "show", title] + (["--body", body] if body else [])
    subprocess.run([HERDR, *args], capture_output=True)


def focused_root():
    """(pane_id, workspace_id, git root or folder) of the pane the action was invoked from."""
    ctx = json.loads(os.environ.get("HERDR_PLUGIN_CONTEXT_JSON") or "{}")
    state_dir = os.environ.get("HERDR_PLUGIN_STATE_DIR")
    if state_dir:
        with open(os.path.join(state_dir, "last-context.json"), "w") as f:
            json.dump(ctx, f, indent=1)
    pane_id = os.environ.get("HERDR_PANE_ID") or _find(ctx, "focused_pane_id", "pane_id")
    wid = os.environ.get("HERDR_WORKSPACE_ID") or _find(ctx, "workspace_id")
    cwd = None
    if pane_id:
        try:
            pane = herdr("pane", "get", pane_id)["pane"]
            cwd = pane.get("foreground_cwd") or pane.get("cwd")
            wid = wid or pane.get("workspace_id")
        except RuntimeError:
            pass
    cwd = cwd or _find(ctx, "foreground_cwd", "cwd") or os.path.expanduser("~")
    return pane_id, wid, git(cwd, "rev-parse", "--show-toplevel") or cwd


def git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True).stdout.strip()


def _find(obj, *keys):
    if isinstance(obj, dict):
        for k in keys:
            if obj.get(k):
                return obj[k]
        for v in obj.values():
            r = _find(v, *keys)
            if r:
                return r
    return None
