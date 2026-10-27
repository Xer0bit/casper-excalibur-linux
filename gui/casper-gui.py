#!/usr/bin/env python3
"""casper-gui: GTK3 front end for casper-ctl (Casper Excalibur G900, board NLCB 001).

The GUI never touches hardware itself. It starts ONE privileged helper
(`pkexec casper-ctl shell`, so the password is asked once) and sends it
one casper-ctl command per line. Each reply ends with a line "@@DONE <rc>".
"""
import os
import queue
import re
import shutil
import subprocess
import sys
import threading

DONE = "@@DONE"
FAN_RE = re.compile(r"fan1=(\d+)rpm fan2=(\d+)rpm temp=(\d+)C")
SWATCHES = (("Red", "FF0000"), ("Orange", "FF8000"), ("Yellow", "FFE000"), ("Green", "00FF00"),
            ("Cyan", "00FFFF"), ("Blue", "0000FF"), ("Purple", "8000FF"), ("Pink", "FF2D95"), ("White", "FFFFFF"))
CSS = b"""
.card { background: alpha(@theme_fg_color, 0.06); border-radius: 12px; padding: 12px 16px; }
.card-title { opacity: 0.65; font-size: 9pt; }
.card-value { font-size: 20pt; font-weight: 700; }
.section { font-weight: 700; margin-top: 4px; }
.swatch { min-width: 44px; min-height: 44px; border-radius: 22px; border: 2px solid alpha(@theme_fg_color, 0.25);
          background-image: none; padding: 0; }
.swatch:hover { border-color: @theme_fg_color; }
levelbar trough { min-height: 8px; }
levelbar block { min-height: 8px; border-radius: 4px; }
levelbar.hot block.filled { background-image: none; background-color: #e5484d; }
levelbar.warm block.filled { background-image: none; background-color: #f5a524; }
levelbar.cool block.filled { background-image: none; background-color: #30a46c; }
.log { font-size: 9pt; }
"""


class Helper:
    """Serialises commands to the casper-ctl shell process."""

    def __init__(self, argv):
        self.proc = subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1)
        self.q = queue.Queue()
        self.lock = threading.Lock()
        self.pending = 0
        self.alive = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            item = self.q.get()
            if item is None:
                return
            cmd, cb = item
            lines, rc = [], 127
            try:
                self.proc.stdin.write(cmd + "\n")
                self.proc.stdin.flush()
                while True:
                    line = self.proc.stdout.readline()
                    if line == "":
                        self.alive = False
                        lines.append("helper exited")
                        break
                    if line.startswith(DONE):
                        rc = int(line.split()[1])
                        break
                    lines.append(line.rstrip("\n"))
            except (BrokenPipeError, OSError, ValueError) as exc:
                self.alive = False
                lines.append(str(exc))
            with self.lock:
                self.pending -= 1
            cb(rc, "\n".join(lines).strip("\n"))

    def run(self, cmd, cb):
        with self.lock:
            self.pending += 1
        self.q.put((cmd, cb))

    def idle(self):
        with self.lock:
            return self.pending == 0

    def close(self):
        self.q.put(None)
        try:
            self.proc.stdin.write("quit\n")
            self.proc.stdin.flush()
            self.proc.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            self.proc.kill()


def find_ctl():
    return os.environ.get("CASPER_CTL") or shutil.which("casper-ctl") or "/usr/local/bin/casper-ctl"


def default_helper_argv():
    ctl = find_ctl()
    if os.geteuid() == 0:
        return [ctl, "shell"]
    return ["pkexec", ctl, "shell"]


def main(argv):
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gdk, GLib, Gtk

    helper_argv = default_helper_argv()
    if "--helper" in argv:  # development: --helper "bash bin/casper-ctl shell"
        helper_argv = argv[argv.index("--helper") + 1].split()

    class App(Gtk.Window):
        def __init__(self):
            super().__init__(title="Casper Excalibur G900")
            self.set_default_size(700, 780)
            self.set_icon_name("casper-gui")
            self.helper = Helper(helper_argv)
            self.connect("destroy", self.on_destroy)

            css = Gtk.CssProvider()
            css.load_from_data(CSS + "".join(".sw-%s { background-color: #%s; }\n" % (hx, hx) for _, hx in SWATCHES).encode())
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

            hb = Gtk.HeaderBar(show_close_button=True, title="Casper Excalibur G900", subtitle="Linux control")
            self.set_titlebar(hb)

            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            outer.set_border_width(14)
            self.add(outer)

            dash = Gtk.Box(spacing=10, homogeneous=True)
            self.fan1 = self.card(dash, "FAN 1", 6500)
            self.fan2 = self.card(dash, "FAN 2", 6500)
            self.temp = self.card(dash, "TEMPERATURE", 100)
            outer.pack_start(dash, False, False, 0)

            self.status = Gtk.Label(label="reading status...", xalign=0)
            self.status.set_line_wrap(True)
            self.status.set_no_show_all(True)   # shown only while there is a message
            self.status.get_style_context().add_class("card-title")
            outer.pack_start(self.status, False, False, 0)

            nb = Gtk.Notebook()
            outer.pack_start(nb, True, True, 0)
            nb.append_page(self.page_keyboard(), Gtk.Label(label="Keyboard"))
            nb.append_page(self.page_fans(), Gtk.Label(label="Fans"))
            nb.append_page(self.page_cpu(), Gtk.Label(label="CPU / Power"))
            nb.append_page(self.page_gpu(), Gtk.Label(label="GPU"))

            self.log = Gtk.TextView(editable=False, monospace=True)
            self.log.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            self.log.get_style_context().add_class("log")
            sw = Gtk.ScrolledWindow()
            sw.set_min_content_height(130)
            sw.add(self.log)
            expander = Gtk.Expander(label="Log", expanded=True)
            expander.add(sw)
            outer.pack_start(expander, False, False, 0)

            GLib.timeout_add_seconds(2, self.poll)
            self.poll()

        @staticmethod
        def card(parent, title, top):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            box.get_style_context().add_class("card")
            head = Gtk.Label(label=title, xalign=0)
            head.get_style_context().add_class("card-title")
            value = Gtk.Label(label="--", xalign=0)
            value.get_style_context().add_class("card-value")
            bar = Gtk.LevelBar()
            bar.set_min_value(0)
            bar.set_max_value(top)
            for w in (head, value, bar):
                box.pack_start(w, False, False, 0)
            parent.pack_start(box, True, True, 0)
            return value, bar, top

        def show_status(self, rc, out):
            m = FAN_RE.search(out) if rc == 0 else None
            if not m:
                self.status.set_text(("fan status unavailable: " if rc else "unexpected status: ") + out)
                self.status.set_visible(True)
                return
            for (label, bar, top), val, unit in zip((self.fan1, self.fan2, self.temp),
                                                    map(int, m.groups()), (" RPM", " RPM", " °C")):
                label.set_text("%d%s" % (val, unit))
                bar.set_value(min(val, top))
                ctx = bar.get_style_context()
                for c in ("cool", "warm", "hot"):
                    ctx.remove_class(c)
                ctx.add_class("hot" if val / top > 0.85 else "warm" if val / top > 0.6 else "cool")
            self.status.set_visible(False)

        # ---- plumbing ----
        def on_destroy(self, *_):
            self.helper.close()
            Gtk.main_quit()

        def say(self, text):
            buf = self.log.get_buffer()
            buf.insert(buf.get_end_iter(), text + "\n")
            self.log.scroll_to_iter(buf.get_end_iter(), 0.0, False, 0.0, 0.0)

        def cmd(self, command):
            def done(rc, out):
                GLib.idle_add(self.say, "$ casper-ctl %s  [rc=%d]\n%s" % (command, rc, out))
            self.helper.run(command, done)

        def poll(self):
            if not self.helper.alive:
                self.status.set_text("helper not running (authentication cancelled or casper-ctl missing)")
                self.status.set_visible(True)
                return False
            if self.helper.idle():
                def done(rc, out):
                    GLib.idle_add(self.show_status, rc, out)
                self.helper.run("fan-status", done)
            return True

        @staticmethod
        def row(label, *widgets):
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            lab = Gtk.Label(label=label, xalign=0)
            lab.set_size_request(150, -1)
            box.pack_start(lab, False, False, 0)
            for w in widgets:
                box.pack_start(w, False, False, 0)
            return box

        @staticmethod
        def page():
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            box.set_border_width(12)
            return box

        @staticmethod
        def note(text):
            lab = Gtk.Label(label=text, xalign=0)
            lab.set_line_wrap(True)
            return lab

        def button(self, text, command_fn):
            b = Gtk.Button(label=text)
            b.connect("clicked", lambda *_: self.cmd(command_fn()))
            return b

        # ---- pages ----
        def page_keyboard(self):
            p = self.page()
            color = Gtk.ColorButton()
            color.set_rgba(Gdk.RGBA(0, 1, 0, 1))

            def hexcolor():
                c = color.get_rgba()
                return "%02X%02X%02X" % (round(c.red * 255), round(c.green * 255), round(c.blue * 255))
            p.pack_start(self.row("Color", color, self.button("Apply", lambda: "kbd-color " + hexcolor())), False, False, 0)

            quick = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            for name, hx in SWATCHES:
                b = self.button("", lambda hx=hx: "kbd-color " + hx)
                b.set_tooltip_text(name)
                b.get_accessible().set_name(name)
                b.get_style_context().add_class("swatch")
                b.get_style_context().add_class("sw-" + hx)
                quick.pack_start(b, False, False, 0)
            p.pack_start(self.row("Quick colors", quick), False, False, 0)

            level = Gtk.ComboBoxText()
            for v in ("0", "1", "2"):
                level.append_text(v)
            level.set_active(0)
            p.pack_start(self.row("Level (raw LKBL)", level,
                                  self.button("Apply", lambda: "kbd-level %s" % level.get_active_text())), False, False, 0)
            mode = Gtk.SpinButton.new_with_range(0, 15, 1)
            p.pack_start(self.row("Mode (raw LKBM)", mode,
                                  self.button("Apply", lambda: "kbd-mode %d" % mode.get_value_as_int())), False, False, 0)
            eff = Gtk.SpinButton.new_with_range(0, 15, 1)
            p.pack_start(self.row("Effect (raw LKBA)", eff,
                                  self.button("Apply", lambda: "kbd-effect %d" % eff.get_value_as_int())), False, False, 0)
            p.pack_start(self.row("Saved state", self.button("Re-apply saved", lambda: "restore"),
                                  self.button("Read EC", lambda: "ec-get LKBR LKBG LKBB LKBL LKBM LKBA")), False, False, 0)
            p.pack_start(self.note(
                "Each apply runs the firmware's own handshake and saves to the EC. "
                "Level, mode and effect are raw EC values; their meanings are not mapped yet."), False, False, 0)
            return p

        def page_fans(self):
            p = self.page()
            p.pack_start(self.note(
                "Monitoring only. Manual fan speed is not available: this board's EC fan interface "
                "has not been reverse-engineered. Live RPM and temperature are shown at the top."), False, False, 0)
            p.pack_start(self.row("Status", self.button("Full status", lambda: "status")), False, False, 0)
            return p

        def page_cpu(self):
            p = self.page()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            for name in ("quiet", "balanced", "performance", "max"):
                box.pack_start(self.button(name, lambda n=name: "preset " + n), False, False, 0)
            p.pack_start(self.row("Preset", box), False, False, 0)

            pl1 = Gtk.SpinButton.new_with_range(5, 120, 1)
            pl1.set_value(45)
            pl2 = Gtk.SpinButton.new_with_range(5, 135, 1)
            pl2.set_value(65)
            p.pack_start(self.row("PL1 / PL2 (W)", pl1, pl2, self.button(
                "Apply", lambda: "rapl %d %d" % (pl1.get_value_as_int(), pl2.get_value_as_int()))), False, False, 0)

            turbo = Gtk.ComboBoxText()
            for v in ("on", "off"):
                turbo.append_text(v)
            turbo.set_active(0)
            p.pack_start(self.row("Turbo", turbo, self.button(
                "Apply", lambda: "turbo %s" % turbo.get_active_text())), False, False, 0)

            epp = Gtk.ComboBoxText()
            for v in ("performance", "balance_performance", "default", "balance_power", "power"):
                epp.append_text(v)
            epp.set_active(1)
            p.pack_start(self.row("Energy preference", epp, self.button(
                "Apply", lambda: "cpu-epp %s" % epp.get_active_text())), False, False, 0)

            gov = Gtk.ComboBoxText()
            for v in ("powersave", "performance"):
                gov.append_text(v)
            gov.set_active(0)
            p.pack_start(self.row("Governor", gov, self.button(
                "Apply", lambda: "cpu-gov %s" % gov.get_active_text())), False, False, 0)
            p.pack_start(self.note(
                "Firmware or the EC may reset power limits; the log shows the value read back."), False, False, 0)
            return p

        def page_gpu(self):
            p = self.page()
            p.pack_start(self.row("Status", self.button("Refresh", lambda: "gpu-status")), False, False, 0)
            lo = Gtk.SpinButton.new_with_range(210, 2100, 15)
            lo.set_value(300)
            hi = Gtk.SpinButton.new_with_range(210, 2100, 15)
            hi.set_value(1500)
            p.pack_start(self.row("Clock lock (MHz)", lo, hi,
                                  self.button("Lock", lambda: "gpu-lock %d %d" % (lo.get_value_as_int(), hi.get_value_as_int())),
                                  self.button("Unlock", lambda: "gpu-unlock")), False, False, 0)
            w = Gtk.SpinButton.new_with_range(30, 200, 1)
            w.set_value(80)
            p.pack_start(self.row("Power limit (W)", w, self.button(
                "Apply", lambda: "gpu-pl %d" % w.get_value_as_int())), False, False, 0)
            p.pack_start(self.note(
                "On this laptop the vBIOS reports the GPU power limit as N/A, so the power limit "
                "may be refused. Clock lock works through nvidia-smi."), False, False, 0)
            return p

    win = App()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main(sys.argv[1:])