#!/usr/bin/env bash
# install.sh: wire this repo into the local machine. Safe to run again.
#
#   ./install.sh               agents, watcher service, herdr plugins and keys, pi config
#   ./install.sh --renderers   also install delta, bat and glow into ~/.local/bin
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_HOME="${AGENTS_HOME:-$HOME/agents}"
HERDR_CONFIG="${HERDR_CONFIG:-$HOME/.config/herdr/config.toml}"
FILE_VIEWER_REF="d17a068ee753daf5ba205bafd59c130b81b8c6c0"   # smarzban/herdr-file-viewer, reviewed
STAMP="$(date +%Y%m%d%H%M%S)"

say()  { printf '\033[1m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33mwarning: %s\033[0m\n' "$*" >&2; }
have() { command -v "$1" >/dev/null 2>&1; }

for tool in herdr python3 git; do have "$tool" || { echo "missing required tool: $tool" >&2; exit 1; }; done
for tool in claude codex pi; do have "$tool" || warn "$tool not found; agents of that kind will not start"; done

# 1. ~/agents -> repo (state, personal context and build output stay local)
say "linking $AGENTS_HOME to $REPO/agents"
mkdir -p "$AGENTS_HOME/spaces"
for item in bin roles models.json settings.json context.example.md; do
  dst="$AGENTS_HOME/$item"
  if [ -e "$dst" ] && [ ! -L "$dst" ]; then mv "$dst" "$dst.bak-$STAMP"; warn "moved old $dst to $dst.bak-$STAMP"; fi
  ln -sfn "$REPO/agents/$item" "$dst"
done
# herdr resumes agents after a server restart with `agentctl resume ...`; it must be a plain name on PATH
mkdir -p "$HOME/.local/bin"
ln -sfn "$AGENTS_HOME/bin/agentctl" "$HOME/.local/bin/agentctl"
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) warn "add ~/.local/bin to PATH so herdr can resume agents" ;; esac
if [ ! -e "$AGENTS_HOME/context.md" ]; then
  cp "$REPO/agents/context.example.md" "$AGENTS_HOME/context.md"
  warn "created $AGENTS_HOME/context.md from the example; edit it with your own context"
fi

# 2. watcher service: a chief of staff in every new herdr workspace
if have systemctl && systemctl --user show-environment >/dev/null 2>&1; then
  say "installing the herdr-space-cos user service"
  mkdir -p "$HOME/.config/systemd/user"
  cp "$REPO/systemd/herdr-space-cos.service" "$HOME/.config/systemd/user/"
  systemctl --user daemon-reload
  systemctl --user enable herdr-space-cos.service >/dev/null
  systemctl --user restart herdr-space-cos.service
else
  warn "no systemd user session; run '$AGENTS_HOME/bin/agentctl watch' yourself"
fi

# 3. herdr plugins and key bindings
say "linking herdr plugins"
plugin_ids="$(herdr plugin list --json 2>/dev/null | python3 -c 'import json,sys
try: print(" ".join(p["plugin_id"] for p in json.load(sys.stdin)["result"]["plugins"]))
except Exception: pass')"
case " $plugin_ids " in *" agent-dotfiles.quick-actions "*) herdr plugin unlink agent-dotfiles.quick-actions >/dev/null ;; esac
herdr plugin link "$REPO/herdr/quick-actions" >/dev/null
case " $plugin_ids " in
  *" herdr-file-viewer "*) ;;
  *) herdr plugin install smarzban/herdr-file-viewer --ref "$FILE_VIEWER_REF" --yes >/dev/null ;;
esac

if ! grep -q '>>> agent-dotfiles quick actions >>>' "$HERDR_CONFIG" 2>/dev/null; then
  say "adding key bindings to $HERDR_CONFIG"
  mkdir -p "$(dirname "$HERDR_CONFIG")"
  [ -f "$HERDR_CONFIG" ] && cp "$HERDR_CONFIG" "$HERDR_CONFIG.bak-$STAMP"
  { printf '\n'; cat "$REPO/herdr/keys.toml"; } >> "$HERDR_CONFIG"
fi
herdr server reload-config >/dev/null 2>&1 || warn "herdr server not running; keys load on next start"

# 4. pi: providers for a local copilot-api proxy (only if you have no config yet)
mkdir -p "$HOME/.pi/agent"
for f in models.json settings.json; do
  [ -e "$HOME/.pi/agent/$f" ] || { cp "$REPO/pi/$f" "$HOME/.pi/agent/$f"; say "installed ~/.pi/agent/$f"; }
done
have pi && herdr integration install pi >/dev/null

# 5. optional renderers for the file viewer, verified against GitHub release digests
install_renderer() {  # repo tag asset binary
  local repo="$1" tag="$2" asset="$3" bin="$4" tmp want got
  have "$bin" && { echo "$bin already installed"; return; }
  tmp="$(mktemp -d)"
  gh release download "$tag" -R "$repo" -p "$asset" -D "$tmp"
  want="$(gh api "repos/$repo/releases/tags/$tag" --jq ".assets[]|select(.name==\"$asset\").digest")"
  got="sha256:$(sha256sum "$tmp/$asset" | cut -d' ' -f1)"
  [ "$want" = "$got" ] || { echo "checksum mismatch for $asset" >&2; rm -rf "$tmp"; return 1; }
  tar xzf "$tmp/$asset" -C "$tmp"
  install -m755 "$(find "$tmp" -type f -name "$bin" -perm -u+x | head -1)" "$HOME/.local/bin/$bin"
  rm -rf "$tmp"; echo "installed $bin ($tag)"
}
if [ "${1:-}" = "--renderers" ]; then
  have gh || { echo "--renderers needs the GitHub CLI (gh)" >&2; exit 1; }
  say "installing file viewer renderers into ~/.local/bin"
  mkdir -p "$HOME/.local/bin"
  install_renderer dandavison/delta 0.20.1 delta-0.20.1-x86_64-unknown-linux-musl.tar.gz delta
  install_renderer sharkdp/bat v0.26.1 bat-v0.26.1-x86_64-unknown-linux-musl.tar.gz bat
  install_renderer charmbracelet/glow v3.0.0 glow_3.0.0_Linux_x86_64.tar.gz glow
fi

say "done. Open a new herdr workspace: its first tab starts a chief of staff."
