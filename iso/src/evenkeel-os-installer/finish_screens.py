"""The installing screen and the screens shown when it ends."""
import datetime
import json
import subprocess
import urllib.parse

from gi.repository import Gdk, Gio, GLib, Gtk

import data
import screens


ENGINE = "/usr/libexec/evenkeel-os-install-engine"


class InstallingScreen(screens.Screen):
    """Runs the install engine as root (pkexec) and follows the progress it reports, one JSON object a line."""
    title = "Installing EvenKeelOS"
    intro = "This takes a while."
    back = False
    next_label = None

    def build(self):
        self.bar = Gtk.ProgressBar()
        self.body.append(self.bar)
        self.pulsing = None
        self.progress(0, "Getting ready")

    def progress(self, fraction, what):
        self.stop_pulse()
        self.bar.set_fraction(fraction)
        self.done = f"{fraction * 100:.0f}% done. {what}..."
        if getattr(self.win, "current", None) is self:      # so the screen shows the latest step
            self.changed()

    def pulse(self, what):
        """A step whose length can't be measured: the bar moves, and the status says what it is doing."""
        self.done = f"{what}. This is the longest step..."
        if self.pulsing is None:
            self.pulsing = GLib.timeout_add(120, lambda: self.bar.pulse() or True)
        self.changed()

    def stop_pulse(self):
        if self.pulsing is not None:
            GLib.source_remove(self.pulsing)
            self.pulsing = None

    def start(self):
        c = self.c
        h24 = c.clock_24 if c.clock_24 is not None else not data.uses_12_hour(c.locale)
        choices = {"disk": c.disk["path"], "disk_identity": c.disk["identity"], "encrypt": c.encrypt,
                   "disk_password": c.disk_password,
                   "locale": c.locale, "layouts": c.layouts, "boot_layout": c.boot_layout or c.layouts[0],
                   "timezone": c.timezone, "time_automatic": c.time_automatic,
                   "manual_time": c.manual_time.isoformat(), "time_servers": c.time_servers, "clock_24": h24,
                   "hostname": c.hostname, "root_password": c.root_password if c.root_enabled else None,
                   "full_name": c.full_name, "username": c.username, "admin": c.admin,
                   "user_password": c.user_password}
        try:
            self.engine = Gio.Subprocess.new(["pkexec", ENGINE],
                                             Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_PIPE)
        except GLib.Error as e:
            self.win.install_failed(f"The installer could not start: {e.message}", data.LOG)
            return
        stdin = self.engine.get_stdin_pipe()
        stdin.write_all(json.dumps(choices).encode(), None)
        stdin.close(None)
        self.reader = Gio.DataInputStream.new(self.engine.get_stdout_pipe())
        self.reader.read_line_async(GLib.PRIORITY_DEFAULT, None, self._line)

    def _line(self, stream, result):
        line, _length = stream.read_line_finish_utf8(result)
        if line is None:                    # the engine ended without saying how: treat it as an error
            self.stop_pulse()
            self.win.install_failed("The installer stopped unexpectedly.", data.LOG)
            return
        try:
            msg = json.loads(line)
        except ValueError:
            msg = {}
        if "progress" in msg:
            self.progress(msg["progress"], msg["step"])
        elif "pulse" in msg:
            self.pulse(msg["step"])
        elif "error" in msg:
            self.stop_pulse()
            self.win.install_failed(msg["error"], msg["log"])
            return
        elif msg.get("done"):
            self.stop_pulse()
            self.win.install_done()
            return
        stream.read_line_async(GLib.PRIORITY_DEFAULT, None, self._line)

    def status(self):
        return self.done


class LogScreen(screens.ListScreen):
    """A final screen that can save the install log to a USB stick."""
    next_label = None
    first_stage = "main"

    def build(self):
        super().build()
        self.stage, self.saved, self.found = "main", "", []

    @property
    def back(self):
        return self.stage != "main"

    def enter(self):
        self.stage, self.saved = "main", ""
        super().enter()

    def refresh(self, to_chosen=True):
        super().refresh(to_chosen)
        self.list.set_visible(self.stage == "sticks")

    def items(self):
        if self.stage != "sticks":
            return []
        return [(f"{s['name']}, {s['size']}", s["path"], False) for s in self.found]

    def find_sticks(self):
        self.stage, self.found = "sticks", data.sticks()
        self.saved = "" if self.found else "No USB stick found. Plug one in, then try again."
        self.choose(to_chosen=True)

    def pick(self, i):
        stick = self.found[i]
        name = f"evenkeel-os-install-log-{datetime.datetime.now():%Y%m%d-%H%M}.txt"
        problem = data.save_to_stick(stick["path"], data.LOG, name)
        self.saved = (f"Saved on {stick['name']} as {name}. You can take the stick out now." if not problem else
                      f"Not saved: {problem}")
        self.stage = "main" if not problem else "sticks"
        self.choose(to_chosen=True)

    def status(self):
        return self.saved


class DoneScreen(LogScreen):
    title = "EvenKeelOS is installed"
    back = False
    main = "Restart"

    @property
    def intro(self):
        if self.stage == "sticks":
            return "Plug in a second USB stick, then click it to save the log on it. Or click Back."
        return ("Click Restart to start EvenKeelOS. Click Save the log to put the details of this install on a "
                "second USB stick.")

    def actions(self):
        return [("Restart", self.win.restart), ("Save the log", self.find_sticks)]


class ErrorScreen(LogScreen):
    """The install stopped: save the log to a stick, show a QR code, or open a report in Firefox."""
    title = "The install stopped"
    next_label = None
    ISSUES = "https://github.com/ctsdownloads/evenkeel-os/issues/new"
    BODY_MAX = 7000              # the body length Anaconda's GitHub report links were limited to
    QR_URL_MAX = 1800            # a denser code is harder for a phone to read off a screen

    def build(self):
        self.what = Gtk.Label(xalign=0, wrap=True, selectable=True, css_classes=["heading"])
        self.body.append(self.what)
        self.code = Gtk.Picture(can_shrink=True, halign=Gtk.Align.CENTER, visible=False)
        self.code.set_size_request(360, 360)
        self.body.append(self.code)
        super().build()
        self.problem, self.log = "", ""

    def failed(self, problem, log):
        self.problem, self.log = problem, log
        self.what.set_text(problem)

    @property
    def intro(self):
        if self.stage == "sticks":
            return ("Plug in a USB stick, then click it to save the log on it. Click Refresh if it isn't listed, "
                    "or Back.")
        if self.stage == "code":
            return ("Point your phone's camera at the code. It opens the report on GitHub with the details filled in, "
                    "ready to send. It carries the end of the log; the whole log can go on a USB stick. Click "
                    "Back when done.")
        return ("Nothing more was changed on the disk. Save the log puts the details on a USB stick for your "
                "helper; no account is needed. Show a QR code sends a report from your phone. Report on GitHub "
                "sends it from Firefox, with a free GitHub account. Or click Restart.")

    def refresh(self, to_chosen=True):
        super().refresh(to_chosen)
        self.code.set_visible(self.stage == "code")

    def actions(self):
        if self.stage == "sticks":
            return [("Refresh", self.find_sticks)]
        if self.stage == "code":
            return []
        return [("Save the log", self.find_sticks), ("Show a QR code", self.show_code),
                ("Report on GitHub", self.report), ("Restart", self.win.restart)]

    def show_code(self):
        made = subprocess.run(["qrencode", "-t", "PNG", "-l", "L", "-s", "8", "-m", "4", "-o", "-",
                               self.issue_url(self.QR_URL_MAX)], capture_output=True)
        if made.returncode != 0:
            self.saved = "The QR code could not be made. Save the log to a stick instead."
        else:
            self.code.set_paintable(Gdk.Texture.new_from_bytes(GLib.Bytes.new(made.stdout)))
            self.stage, self.saved = "code", ""
        self.choose(to_chosen=True)

    def issue_url(self, url_max=None):
        """New-issue link with the error and as much of the log's end as fits."""
        try:
            with open(self.log, errors="replace") as f:
                lines = f.read().splitlines(keepends=True)
        except OSError:
            lines = []
        kept, size = [], 0                  # start from the lines that can fit at all
        for line in reversed(lines):
            size += len(line)
            if size > self.BODY_MAX:
                break
            kept.insert(0, line)
        lines = kept or [line[-self.BODY_MAX // 2:] for line in lines[-1:]]     # one line longer than all of it
        head = f"The installer stopped with:\n\n    {self.problem}\n\nThe end of the installer's log:\n\n```\n"
        title = f"Install stopped: {self.problem}"[:256]
        while True:
            body = head + "".join(lines) + "```"
            url = f"{self.ISSUES}?{urllib.parse.urlencode({'title': title, 'body': body})}"
            if not lines or (len(body) <= self.BODY_MAX and (url_max is None or len(url) <= url_max)):
                return url
            if len(lines) > 1:
                lines.pop(0)
            else:                           # the last line alone is too long: keep its end
                lines[0] = lines[0][len(lines[0]) // 4:] if len(lines[0]) > 80 else ""
                lines = [x for x in lines if x]

    def report(self):
        Gtk.UriLauncher.new(self.issue_url()).launch(self.win, None, None, None)
