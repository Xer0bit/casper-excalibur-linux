#!/usr/bin/env bash
# Build dist/casper-excalibur-linux_<version>_all.deb.   ./packaging/build-deb.sh [version]
set -euo pipefail
cd "$(dirname "$0")/.."
ver="${1:-$(sed -n 's/^VERSION="\(.*\)"/\1/p' packaging/VERSION.sh 2>/dev/null || echo 0.1.0)}"
name=casper-excalibur-linux
root="$(mktemp -d)"; trap 'rm -rf "$root"' EXIT
pkg="$root/$name"

install -Dm755 bin/casper-ctl      "$pkg/usr/bin/casper-ctl"
install -Dm755 gui/casper-gui.py   "$pkg/usr/bin/casper-gui"
install -Dm644 data/casper-gui.desktop "$pkg/usr/share/applications/casper-gui.desktop"
sed -i 's|^Exec=.*|Exec=casper-gui|' "$pkg/usr/share/applications/casper-gui.desktop"
install -Dm644 data/casper-gui.svg "$pkg/usr/share/icons/hicolor/scalable/apps/casper-gui.svg"
install -Dm644 README.md "$pkg/usr/share/doc/$name/README.md"
install -Dm644 README.en.md "$pkg/usr/share/doc/$name/README.en.md"
install -Dm644 docs/INSTALL.md "$pkg/usr/share/doc/$name/INSTALL.md"
install -Dm644 docs/INSTALL.en.md "$pkg/usr/share/doc/$name/INSTALL.en.md"
install -Dm644 docs/EC-MAP.md "$pkg/usr/share/doc/$name/EC-MAP.md"
install -Dm644 docs/EC-MAP.en.md "$pkg/usr/share/doc/$name/EC-MAP.en.md"
install -Dm644 LICENSE "$pkg/usr/share/doc/$name/copyright"

mkdir -p "$pkg/DEBIAN"
cat > "$pkg/DEBIAN/control" <<CTL
Package: $name
Version: $ver
Architecture: all
Section: utils
Priority: optional
Maintainer: Xer0bit <Xer0bit@users.noreply.github.com>
Homepage: https://github.com/Xer0bit/casper-excalibur-linux
Depends: bash, python3, python3-gi, gir1.2-gtk-3.0, pkexec | policykit-1, acpica-tools
Recommends: ubuntu-drivers-common
Description: Linux support for the Casper Excalibur G900 (keyboard color, fans, power)
 casper-ctl and casper-gui talk to the laptop's embedded controller and the
 kernel's cpufreq/RAPL/nvidia-smi interfaces. Keyboard color, fan RPM and
 temperature monitoring, CPU power limits and GPU clock lock.
 Run 'sudo casper-ctl doctor' to detect missing drivers.
 Not endorsed by Casper. EC writes are enabled only for board NLCB 001.
CTL

cat > "$pkg/DEBIAN/postinst" <<'SH'
#!/bin/sh
set -e
if [ "$1" = configure ]; then
  mkdir -p /etc/casper-ctl/state
  # decode this machine's EC map from its own DSDT; harmless if it fails
  command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
  /usr/bin/casper-ctl ec-fields >/dev/null 2>&1 || echo "casper-excalibur-linux: run 'sudo casper-ctl doctor --fix' to finish setup"
fi
exit 0
SH
cat > "$pkg/DEBIAN/prerm" <<'SH'
#!/bin/sh
set -e
if [ "$1" = remove ] || [ "$1" = purge ]; then
  systemctl disable --now casper-ctl.service casper-ctl-resume.service 2>/dev/null || true
  rm -f /etc/systemd/system/casper-ctl.service /etc/systemd/system/casper-ctl-resume.service
  systemctl daemon-reload 2>/dev/null || true
fi
exit 0
SH
cat > "$pkg/DEBIAN/postrm" <<'SH'
#!/bin/sh
set -e
[ "$1" = purge ] && rm -rf /etc/casper-ctl
exit 0
SH
chmod 755 "$pkg/DEBIAN/postinst" "$pkg/DEBIAN/prerm" "$pkg/DEBIAN/postrm"

mkdir -p dist
fakeroot dpkg-deb --build "$pkg" "dist/${name}_${ver}_all.deb" >/dev/null
echo "built dist/${name}_${ver}_all.deb"
