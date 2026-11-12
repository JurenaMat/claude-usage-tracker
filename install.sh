#!/bin/bash
# Claude Usage Tracker installer (macOS). Safe to run again to update.
#   ./install.sh              install everything
#   ./install.sh --no-focus   skip the "time in the app" tracker
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
BOARD="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/usage-tracker"
AGENTS="$HOME/Library/LaunchAgents"
UID_="$(id -u)"
FOCUS=1; [ "${1:-}" = "--no-focus" ] && FOCUS=0

[ "$(uname)" = "Darwin" ] || { echo "The installer is for macOS. On other systems run: python3 src/build.py --html dashboard.html"; exit 1; }
PY=/usr/bin/python3
"$PY" -c 'import sys; assert sys.version_info >= (3, 8)' 2>/dev/null || { echo "Needs Python 3.8+ at /usr/bin/python3. Run: xcode-select --install"; exit 1; }

echo "→ Copying files to $BOARD"
mkdir -p "$BOARD" "$AGENTS"
cp "$HERE/src/build.py" "$HERE/src/dashboard.html" "$HERE/src/focus-tick.sh" "$BOARD/"
chmod +x "$BOARD/focus-tick.sh"

# Upgrading from the earlier name, Claude Usage Board: retire the old jobs and widget, keep the tracked minutes.
OLD="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/usage-board"
if [ -d "$OLD" ] || [ -f "$AGENTS/com.claude-usage-board.focus.plist" ]; then
  echo "→ Moving over your Claude Usage Board setup"
  for label in com.claude-usage-board.refresh com.claude-usage-board.focus com.claude-usage.focus; do
    launchctl bootout "gui/$UID_/$label" 2>/dev/null || true
    rm -f "$AGENTS/$label.plist"
  done
  rm -rf "$HOME/Library/Application Support/Übersicht/widgets/claude-usage.widget"
  if [ -f "$OLD/focus.log" ]; then cat "$OLD/focus.log" >> "$BOARD/focus.log"; mv "$OLD/focus.log" "$OLD/focus.log.moved"; fi
fi

plist() { # label, interval seconds, command...
  local label="$1" interval="$2"; shift 2
  local args=""; for a in "$@"; do args="$args<string>$a</string>"; done
  cat > "$AGENTS/$label.plist" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key><array>$args</array>
  <key>StartInterval</key><integer>$interval</integer>
  <key>RunAtLoad</key><true/>
  <key>EnvironmentVariables</key><dict><key>CLAUDE_CONFIG_DIR</key><string>${CLAUDE_CONFIG_DIR:-$HOME/.claude}</string></dict>
</dict></plist>
PL
  launchctl bootout "gui/$UID_/$label" 2>/dev/null || true
  launchctl bootstrap "gui/$UID_" "$AGENTS/$label.plist"
}

echo "→ Refreshing the dashboard every hour"
plist com.claude-usage-tracker.refresh 3600 "$PY" -I "$BOARD/build.py" "$BOARD/claude-usage.json" --html "$BOARD/dashboard.html"

if [ "$FOCUS" = 1 ]; then
  echo "→ Tracking minutes the Claude app is in front (once a minute, nothing else recorded)"
  plist com.claude-usage-tracker.focus 60 /bin/bash "$BOARD/focus-tick.sh"
fi

WIDGETS="$HOME/Library/Application Support/Übersicht/widgets"
if [ -d "/Applications/Übersicht.app" ]; then
  echo "→ Adding the desktop widget to Übersicht"
  mkdir -p "$WIDGETS/claude-usage-tracker.widget"
  sed "s|__BOARD__|$BOARD|g" "$HERE/widget/index.jsx" > "$WIDGETS/claude-usage-tracker.widget/index.jsx"
  open -a "Übersicht"
else
  echo "→ Skipping the desktop widget: Übersicht isn't installed."
  echo "  Get it with 'brew install --cask ubersicht', then run ./install.sh again."
fi

"$PY" -I "$BOARD/build.py" "$BOARD/claude-usage.json" --html "$BOARD/dashboard.html" >/dev/null
echo
echo "Done. Your dashboard: $BOARD/dashboard.html"
open "$BOARD/dashboard.html"
