#!/usr/bin/env bash
# Install casper-ctl (CLI), casper-gui (GTK3) and the desktop entry. Run: sudo ./install.sh
set -euo pipefail
[ "$EUID" -eq 0 ] || exec sudo -E bash "$0" "$@"
here="$(cd "$(dirname "$0")" && pwd)"

board="$(cat /sys/class/dmi/id/board_name 2>/dev/null || true)"
if [ "$board" != "NLCB 001" ]; then
  echo "WARNING: board is '$board', not 'NLCB 001' (Casper Excalibur G900)."
  echo "EC writes stay disabled on other boards. Read-only commands and CPU/GPU controls still work."
fi

if command -v apt-get >/dev/null 2>&1; then
  apt-get install -y acpica-tools python3 python3-gi gir1.2-gtk-3.0 pkexec \
    || echo "WARNING: install acpica-tools, python3-gi, gir1.2-gtk-3.0 and pkexec manually."
fi

install -m755 "$here/bin/casper-ctl" /usr/local/bin/casper-ctl
install -m755 "$here/gui/casper-gui.py" /usr/local/bin/casper-gui
install -m644 "$here/data/casper-gui.desktop" /usr/share/applications/casper-gui.desktop
mkdir -p /etc/casper-ctl/state

# Migrate a previous per-user state (saved keyboard color etc.) if present.
user="${SUDO_USER:-}"
if [ -n "$user" ]; then
  uhome="$(getent passwd "$user" | cut -d: -f6)"
  if [ -d "$uhome/.config/casper-ctl/state" ]; then
    for f in kbd_color kbd_LKBA kbd_LKBL kbd_LKBM; do
      [ -s "$uhome/.config/casper-ctl/state/$f" ] && cp -n "$uhome/.config/casper-ctl/state/$f" /etc/casper-ctl/state/ || true
    done
  fi
fi

# Decode the EC field map from this machine's own DSDT (needs acpica-tools).
if /usr/local/bin/casper-ctl ec-fields >/dev/null 2>&1; then
  echo "EC field map written to /etc/casper-ctl/ec_fields.txt ($(wc -l < /etc/casper-ctl/ec_fields.txt) fields)"
else
  echo "WARNING: could not decode the EC map. Run later: sudo casper-ctl ec-fields"
fi

echo
/usr/local/bin/casper-ctl doctor || echo "Run 'sudo casper-ctl doctor --fix' to install what is missing."
echo
echo "Installed. Try:  sudo casper-ctl status    |    casper-gui"
echo "Keep keyboard color across boot/resume:  sudo casper-ctl install-service none"
