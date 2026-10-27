#!/usr/bin/env bash
# Offline tests against a fake EC image (no hardware needed).
#   ./tests/run.sh
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
ROOT="$PWD"
CTL="$ROOT/bin/casper-ctl"
T="$(mktemp -d)"
EMU=""
trap '[ -n "$EMU" ] && kill "$EMU" 2>/dev/null; rm -rf "$T"' EXIT
mkdir -p "$T/conf/state"
fails=0

ok()  { echo "ok   - $1"; }
bad() { echo "FAIL - $1"; fails=$((fails+1)); }
check() { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (expected '$2', got '$3')"; fi; }
has() { case "$3" in *"$2"*) ok "$1";; *) bad "$1 (missing '$2' in: $3)";; esac; }
ctl() { bash "$CTL" "$@" 2>&1; }

export EC_IO="$T/ec.bin" CASPER_CONF_DIR="$T/conf" CASPER_SKIP_BOARD_CHECK=1
head -c 256 /dev/zero > "$EC_IO"
# bit offset, field name, width: the real NLCB 001 layout for the fields used here
cat > "$T/conf/ec_fields.txt" <<'EOF'
704 RTMP 8
1096 LKBR 8
1104 LKBG 8
1112 LKBB 8
1304 CBSC 8
1360 LKCC 1
1361 LKBE 1
1362 LKBC 1
1363 LKBS 1
1364 LKBA 4
1544 LKBL 4
1548 LKBM 4
1560 FANM 1
1616 FN1R 16
1632 FN2R 16
1682 FANE 1
1683 FAND 1
EOF

# EC emulator: acknowledge keyboard commits by raising LKBE (0xAA bit 1)
python3 -I - "$EC_IO" <<'PY' &
import sys, time
p = sys.argv[1]
while True:
    with open(p, "r+b") as f:
        b = f.read(256)[0xAA]
        if (b & 1) or (b & 8):
            f.seek(0xAA)
            f.write(bytes([b | 2]))
    time.sleep(0.03)
PY
EMU=$!

byte() { od -An -tx1 -j "$1" -N1 "$EC_IO" | tr -d ' '; }

# --- keyboard color via the DSDT handshake
out="$(ctl kbd-color FF8040)"; check "kbd-color exits cleanly" "" "$out"
out="$(ctl ec-get LKBR LKBG LKBB)"
has "red written"   "LKBR = 255" "$out"
has "green written" "LKBG = 128" "$out"
has "blue written"  "LKBB = 64"  "$out"

# --- bit-safe neighbours: LKBL (low nibble) and LKBM (high nibble) share 0xC1
ctl kbd-level 2 >/dev/null; ctl kbd-mode 5 >/dev/null
check "0xC1 holds level 2 + mode 5" "52" "$(byte $((0xC1)))"
ctl kbd-effect 9 >/dev/null
check "0xAA = LKCC|LKBE|LKBS + LKBA=9" "9b" "$(byte $((0xAA)))"

# --- validation
out="$(ctl kbd-level 3)"; has "kbd-level 3 rejected" "usage" "$out"
out="$(ctl ec-setf LKBL 16)"; has "oversized value rejected" "does not fit" "$out"
out="$(ctl kbd-color nothex)"; has "bad color rejected" "usage" "$out"

# --- restore: re-applies after the EC lost its state, skips when already applied
for off in 0x89 0x8A 0x8B 0xC1; do printf '\x00' | dd of="$EC_IO" bs=1 seek=$((off)) conv=notrunc 2>/dev/null; done
ctl restore >/dev/null
out="$(ctl ec-get LKBR LKBG LKBB LKBL LKBM)"
has "restore re-applied color" "LKBR = 255" "$out"
has "restore re-applied level" "LKBL = 2" "$out"
has "restore re-applied mode"  "LKBM = 5" "$out"
out="$(ctl restore)"; has "restore skips when unchanged" "already applied" "$out"

# --- fans: tach is stored high byte first
printf '\x0a\x91\x0a\xe8' | dd of="$EC_IO" bs=1 seek=$((0xCA)) conv=notrunc 2>/dev/null
printf '\x3a' | dd of="$EC_IO" bs=1 seek=$((0x58)) conv=notrunc 2>/dev/null
out="$(ctl fan-status)"
has "fan1 rpm decoded" "fan1=2705rpm" "$out"
has "fan2 rpm decoded" "fan2=2792rpm" "$out"
has "temperature decoded" "temp=58C" "$out"

# --- board guard (skipped when run on the real NLCB 001 board)
if [ "$(cat /sys/class/dmi/id/board_name 2>/dev/null)" != "NLCB 001" ]; then
  out="$(CASPER_SKIP_BOARD_CHECK=0 ctl kbd-color 00FF00)"
  has "EC writes refused on other boards" "NLCB 001" "$out"
fi

# --- shell mode (used by the GUI)
out="$(printf 'ec-get LKBG\nbogus\nec-watch X\nquit\n' | bash "$CTL" shell 2>&1)"
has "shell: ok reply"        "@@DONE 0" "$out"
has "shell: unknown command" "@@DONE 1" "$out"
has "shell: blocked command" "@@DONE 2" "$out"
out="$(ctl doctor)"
has "doctor: reports board"  " board " "$out"
has "doctor: reports ec_sys" " ec_sys " "$out"
# globbing must work inside shell mode (regression: set -f broke cpu[0-9]* paths)
mkdir -p "$T/cpu/cpu0/cpufreq"; echo powersave > "$T/cpu/cpu0/cpufreq/scaling_governor"
out="$(printf 'cpu-gov performance\nquit\n' | CPUF="$T/cpu" bash "$CTL" shell 2>&1)"
has "shell: glob expands" "@@DONE 0" "$out"
check "shell: governor written" "performance" "$(cat "$T/cpu/cpu0/cpufreq/scaling_governor")"

# --- GUI helper protocol (no GTK needed)
out="$(python3 -I - "$ROOT/gui/casper-gui.py" "$CTL" <<'PY' 2>&1
import importlib.util, sys, threading
spec = importlib.util.spec_from_file_location("casper_gui", sys.argv[1])
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
h = mod.Helper(["bash", sys.argv[2], "shell"])
ev, res = threading.Event(), {}
def cb(rc, text):
    res["rc"], res["text"] = rc, text; ev.set()
h.run("ec-get LKBG", cb)
ev.wait(10)
print("RC=%s TEXT=%s" % (res.get("rc"), res.get("text")))
h.close()
PY
)"
has "GUI helper round trip" "RC=0 TEXT=LKBG = 128" "$out"

# --- undo log (last: it rewinds every write made above)
out="$(ctl ec-undo)"; has "ec-undo restores bytes" "restored EC" "$out"
out="$(ctl ec-get LKBG)"; has "ec-undo rewound the color" "LKBG = 0" "$out"

echo
[ "$fails" -eq 0 ] && echo "all tests passed" || echo "$fails test(s) failed"
exit "$fails"
