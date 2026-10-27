#!/usr/bin/env bash
# Remove casper-ctl, casper-gui and the systemd units. Keeps /etc/casper-ctl (settings) unless --purge.
set -uo pipefail
[ "$EUID" -eq 0 ] || exec sudo -E bash "$0" "$@"
systemctl disable --now casper-ctl.service casper-ctl-resume.service 2>/dev/null
rm -f /etc/systemd/system/casper-ctl.service /etc/systemd/system/casper-ctl-resume.service
systemctl daemon-reload
rm -f /usr/local/bin/casper-ctl /usr/local/bin/casper-gui /usr/share/applications/casper-gui.desktop
[ "${1:-}" = --purge ] && rm -rf /etc/casper-ctl
echo "removed"
