"""A tool's questions, messages, lists, password box and progress, shown inside the Wheelhouse window.

Tools started from the window get EVENKEEL_OS_PANEL, the path of a socket here; evenkeel-os-dialog connects to it
with one request per question and waits for the answer.
"""
import json
import os
import shutil
import socket
import tempfile
import threading

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk, Pango  # noqa: E402
from evenkeel_os_ui import _, user_folder  # noqa: E402

ICONS = {"question": "dialog-question-symbolic", "info": "dialog-information-symbolic",
         "warning": "dialog-warning-symbolic", "error": "dialog-error-symbolic", "list": "view-list-symbolic",
         "password": "dialog-password-symbolic", "progress": "view-refresh-symbolic",
         "file-selection": "document-open-symbolic"}


def set_text(label, text, markup):
    """Markup when the tool asked for it and it parses; plain text otherwise."""
    if markup:
        try:
            Pango.parse_markup(text, -1, "\0")
            label.set_markup(text)
            return
        except GLib.Error:
            pass
    label.set_text(text)


class Request:
    """One question from a tool, answered once."""

    def __init__(self, dialogs, conn, f, req):
        self.dialogs, self.conn, self.f, self.req = dialogs, conn, f, req
        self.kind, self.flags = req.get("kind"), req.get("flags", [])
        self.answered, self.pulse, self.widget = False, 0, None
        self.cancellable = Gio.Cancellable()      # closes the file window if the tool stops first

    def reply(self, button, **extra):
        if self.answered:
            return
        self.answered = True
        self.cancellable.cancel()
        if self.pulse:
            GLib.source_remove(self.pulse)
            self.pulse = 0
        try:
            self.f.write(json.dumps({"button": button, **extra}) + "\n")
            self.f.flush()
        except (OSError, ValueError):
            pass        # the tool already stopped
        try:
            self.conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.dialogs.done(self)

    # ---------------------------------------------------------------- the view for this request

    def build(self, window):
        r, kind = self.req, self.kind
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin_top=36, margin_bottom=36,
                      margin_start=12, margin_end=12)
        head = Gtk.Box(spacing=14)
        head.append(Gtk.Image(icon_name=ICONS[kind], pixel_size=32, valign=Gtk.Align.START))
        head.append(Gtk.Label(label=r.get("title") or "EvenKeelOS Wheelhouse", wrap=True, xalign=0, hexpand=True,
                              css_classes=["title-2"]))
        box.append(head)
        self.label = Gtk.Label(wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, xalign=0, selectable=True,
                               visible=bool(r.get("text")))
        set_text(self.label, r.get("text", ""), "no-markup" not in self.flags)
        box.append(self.label)
        self.ok = None
        if kind == "list":
            box.append(self.list_box())
        elif kind == "password":
            box.append(self.password_box())
        elif kind == "progress":
            self.bar = Gtk.ProgressBar(margin_top=6)
            box.append(self.bar)
            if "pulsate" in self.flags:
                self.pulse = GLib.timeout_add(150, self.on_pulse)
        elif kind == "file-selection":
            self.pick_file(window)
        box.append(self.buttons())
        self.widget = box
        return box

    def list_box(self):
        hidden = int(self.req.get("hide-column") or 0) - 1
        columns = [c for i, c in enumerate(self.req.get("columns", [])) if i != hidden]
        self.rows = Gtk.ListBox(css_classes=["boxed-list"], activate_on_single_click=False)
        for i, row in enumerate(self.req.get("rows", [])):
            shown = [c for j, c in enumerate(row) if j != hidden]
            r = Adw.ActionRow(title=shown[0] if shown else "", subtitle=" · ".join(c for c in shown[1:] if c),
                              use_markup=False, activatable=True)
            r.index = i
            self.rows.append(r)
        self.rows.connect("row-selected", self.on_selected)
        self.rows.connect("row-activated", lambda _lb, row: self.reply("ok", row=row.index))
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        if len(columns) > 1:
            box.append(Gtk.Label(label=" · ".join(columns), xalign=0, css_classes=["dim-label", "caption"]))
        box.append(Gtk.ScrolledWindow(child=self.rows, propagate_natural_height=True, max_content_height=420,
                                      hscrollbar_policy=Gtk.PolicyType.NEVER))
        return box

    def on_selected(self, _rows, row):
        if self.ok:
            self.ok.set_sensitive(row is not None)

    def password_box(self):
        self.entry = Adw.PasswordEntryRow(title=_("Password"))
        self.entry.connect("entry-activated", lambda *_: self.reply("ok", value=self.entry.get_text()))
        box = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        box.append(self.entry)
        return box

    def buttons(self):
        r, kind = self.req, self.kind
        if kind == "question":
            labels = [("cancel", r.get("cancel-label") or _("No")), ("extra", r.get("extra-button")),
                      ("ok", r.get("ok-label") or _("Yes"))]
        elif kind in ("list", "password"):
            labels = [("cancel", r.get("cancel-label") or _("Cancel")), ("ok", r.get("ok-label") or _("OK"))]
        elif kind == "progress":
            labels = [] if "no-cancel" in self.flags else [("cancel", _("Cancel"))]
        elif kind == "file-selection":
            labels = []
        else:
            labels = [("ok", r.get("ok-label") or _("OK"))]
        row = Gtk.Box(spacing=12, halign=Gtk.Align.END, margin_top=6)
        for button, text in labels:
            if not text:
                continue
            b = Gtk.Button(label=text, css_classes=["pill"] + (["suggested-action"] if button == "ok" else []))
            b.connect("clicked", self.on_button, button)
            row.append(b)
            if button == "ok":
                self.ok = b
                b.set_sensitive(kind != "list")
        return row

    def on_button(self, _button, button):
        if button == "ok" and self.kind == "list":
            row = self.rows.get_selected_row()
            if row:
                self.reply("ok", row=row.index)
        elif button == "ok" and self.kind == "password":
            self.reply("ok", value=self.entry.get_text())
        else:
            self.reply(button)

    def focus(self):
        target = {"password": getattr(self, "entry", None), "list": getattr(self, "rows", None)}.get(self.kind, self.ok)
        if target:
            target.grab_focus()

    # ---------------------------------------------------------------- progress and files

    def on_pulse(self):
        self.bar.pulse()
        return True

    def progress(self, message):
        """A line from the tool: a number moves the bar, "# text" replaces the text; the end closes the view."""
        if self.answered:
            return
        if message.get("end"):
            self.reply("ok")
            return
        line = message.get("line", "").strip()
        if line.startswith("#"):
            set_text(self.label, line[1:].strip(), True)
            self.label.set_visible(True)
            return
        try:
            percent = float(line)
        except ValueError:
            return
        if not self.pulse:
            self.bar.set_fraction(min(max(percent, 0), 100) / 100)
        if percent >= 100 and "auto-close" in self.flags:
            self.reply("ok")

    def pick_file(self, window):
        name, _sep, patterns = self.req.get("file-filter", "").partition("|")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        dialog = Gtk.FileDialog(title=self.req.get("title") or _("Pick a file"))
        if patterns.strip():
            f = Gtk.FileFilter(name=name.strip())
            for p in patterns.split():
                f.add_pattern(p)
            filters.append(f)
            dialog.set_filters(filters)
            dialog.set_default_filter(f)
        downloads = user_folder("DOWNLOAD")
        if downloads.is_dir():
            dialog.set_initial_folder(Gio.File.new_for_path(str(downloads)))

        def picked(d, result):
            try:
                self.reply("ok", value=d.open_finish(result).get_path())
            except GLib.Error:
                self.reply("cancel")
        dialog.open(window, self.cancellable, picked)


class Dialogs:
    """The socket tools connect to, and the view showing the newest open request (or Working while there is none)."""

    def __init__(self, window, changed):
        self.window, self.changed = window, changed     # changed(): a request arrived or ended
        self.open = []
        self.folder = tempfile.mkdtemp(prefix="evenkeel-os-tools-", dir=os.environ.get("XDG_RUNTIME_DIR"))
        self.path = os.path.join(self.folder, "dialogs")
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(self.path)
        self.server.listen(4)
        self.view = Adw.Clamp(maximum_size=640)
        self.widget = Gtk.ScrolledWindow(child=self.view, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.title = ""
        threading.Thread(target=self.accept, daemon=True).start()

    def close(self):
        self.server.close()
        shutil.rmtree(self.folder, ignore_errors=True)

    def accept(self):
        while True:
            try:
                conn, _addr = self.server.accept()
            except OSError:
                return
            threading.Thread(target=self.serve, args=(conn,), daemon=True).start()

    def serve(self, conn):
        f = conn.makefile("rw", encoding="utf-8")
        try:
            req = json.loads(f.readline() or "null")
        except ValueError:
            req = None
        if not isinstance(req, dict) or req.get("kind") not in ICONS:
            conn.close()
            return
        request = Request(self, conn, f, req)
        GLib.idle_add(self.add, request)
        try:
            for line in f:
                GLib.idle_add(request.progress, json.loads(line))
        except (OSError, ValueError):
            pass
        GLib.idle_add(request.reply, "cancel")      # the tool stopped, or the request was answered
        for closing in (f, conn):
            try:
                closing.close()
            except OSError:
                pass

    def add(self, request):
        self.open.append(request)
        self.view.set_child(request.build(self.window))
        request.focus()
        self.changed()

    def done(self, request):
        if request in self.open:
            self.open.remove(request)
        self.show()
        self.changed()

    def show(self, title=None):
        """The newest open request, or a Working note for the running tool."""
        self.title = title or self.title
        if self.open:
            self.view.set_child(self.open[-1].widget)
            self.open[-1].focus()
            return
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin_top=72, valign=Gtk.Align.START)
        box.append(Adw.Spinner(width_request=32, height_request=32))
        box.append(Gtk.Label(label=_("{title}: working…").format(title=self.title) if self.title else _("Working…"),
                             wrap=True,
                             css_classes=["title-4"]))
        self.view.set_child(box)
