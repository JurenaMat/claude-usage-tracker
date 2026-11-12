#!/bin/bash
# Removes the Claude Usage Tracker. Pass --keep-data to keep ~/.claude/usage-tracker.
BOARD="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/usage-tracker"
for label in com.claude-usage-tracker.refresh com.claude-usage-tracker.focus; do
  launchctl bootout "gui/$(id -u)/$label" 2>/dev/null
  rm -f "$HOME/Library/LaunchAgents/$label.plist"
done
rm -rf "$HOME/Library/Application Support/Übersicht/widgets/claude-usage-tracker.widget"
[ "${1:-}" = "--keep-data" ] || rm -rf "$BOARD"
echo "Claude Usage Tracker removed."
