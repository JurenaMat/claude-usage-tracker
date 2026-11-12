#!/bin/bash
# Removes the Claude Usage Board. Pass --keep-data to keep ~/.claude/usage-board.
BOARD="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/usage-board"
for label in com.claude-usage-board.refresh com.claude-usage-board.focus; do
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null
  rm -f "$HOME/Library/LaunchAgents/$label.plist"
done
rm -rf "$HOME/Library/Application Support/Übersicht/widgets/claude-usage.widget"
[ "${1:-}" = "--keep-data" ] || rm -rf "$BOARD"
echo "Claude Usage Board removed."
