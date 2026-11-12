#!/bin/bash
# Runs once a minute (LaunchAgent com.claude-usage-tracker.focus). Appends one line to focus.log,
# next to this script,
# when the Claude app is in front and the Mac has had keyboard/mouse input in the last 5 minutes.
# Nothing else is recorded: no window titles, no other apps.
name=$(/usr/bin/lsappinfo info -only name "$(/usr/bin/lsappinfo front)" 2>/dev/null | /usr/bin/sed -E 's/.*="(.*)"/\1/')
idle=$(/usr/sbin/ioreg -c IOHIDSystem | /usr/bin/awk '/HIDIdleTime/ {print int($NF/1000000000); exit}')
if [ "$name" = "Claude" ] && [ "${idle:-0}" -lt 300 ]; then
  /bin/date "+%Y-%m-%dT%H:%M" >> "$(/usr/bin/dirname "$0")/focus.log"
fi
