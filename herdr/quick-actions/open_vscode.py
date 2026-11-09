"""Open the focused pane's git root (or its folder) in VS Code."""
import subprocess
import sys

sys.path.insert(0, ".")  # plugin dir is the cwd; -I drops it from sys.path
from common import focused_root, notify  # noqa: E402

_, _, root = focused_root()
subprocess.Popen(["code", root], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                 stderr=subprocess.DEVNULL, start_new_session=True)
notify("VS Code", root)
print(root)
