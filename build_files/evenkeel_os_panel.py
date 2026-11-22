"""The System Tools window: every EvenKeelOS tool, on pages in one window."""
import os
import shutil
import subprocess
import threading
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402
from evenkeel_os_packages import zoom  # noqa: E402

APP_ID = "io.github.ctsdownloads.evenkeel-os.Tools"
TOOLS = "/usr/bin/evenkeel-os-tools"
PACKAGES = "/usr/bin/evenkeel-os-packages"
PACKAGE_TYPES = (".rpm", ".deb")
WINDOWS_TYPES = (".exe", ".msi")
CSS = b"""
.ek-banner { background: #12355b; color: #f4f1ea; border-radius: 18px; padding: 24px; }
.ek-banner .ek-sub { color: #c9d4e2; }
.ek-banner image { color: #2bb3a3; }
.ek-banner button { background: #f4f1ea; color: #12355b; font-weight: bold; }
.ek-banner.ek-warn { background: #7a5600; }
.ek-drop { border: 2px dashed alpha(currentColor, 0.3); border-radius: 18px; padding: 22px; }
.ek-drop.ek-over { border-color: @accent_color; background: alpha(@accent_color, 0.08); }
.ek-layout { border-radius: 16px; padding: 14px; border: 2px solid transparent; }
.ek-layout:checked { border-color: @accent_bg_color; background: alpha(@accent_bg_color, 0.15); }
"""

PAGES = [("overview", "Overview", "go-home-symbolic"),
         ("updates", "Updates", "software-update-available-symbolic"),
         ("apps", "Apps", "view-app-grid-symbolic"),
         ("disk", "Disk and startup", "drive-harddisk-symbolic"),
         ("yours", "Make it yours", "applications-graphics-symbolic"),
         ("help", "Get help", "help-about-symbolic")]


def spawn(argv, done=None):
    """Start a tool in its own windows; done(exit code) runs in the window once it has closed."""
    try:
        proc = Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE)
    except GLib.Error:
        return False
    if done:
        proc.wait_async(None, lambda p, r: done(p.get_exit_status() if p.wait_finish(r) else 1))
    return True


def zoom_usual_browser():
    """True when Zoom meetings were set to open in the usual browser (zoom.py's own choice file)."""
    try:
        return zoom.CHOICE.read_text().strip() == "default"
    except OSError:
        return False


class Tool:
    """One row: where it lives, what it says, and what it runs (a command line, or a function of the window)."""

    def __init__(self, page, group, title, about, icon, run, command="", keywords=""):
        self.page, self.group, self.title, self.about, self.icon = page, group, title, about, icon
        self.run, self.command, self.keywords = run, command, keywords

    def matches(self, words):
        text = f"{self.title} {self.about} {self.command} {self.keywords}".lower()
        return all(w in text for w in words)


def tool_list():
    t = [TOOLS]
    p = [PACKAGES]
    return [
        Tool("overview", "Quick fixes", "Undo the last update", "Go back to the version from before the last update",
             "edit-undo-symbolic", t + ["undo-update"], "evenkeel-os-tools undo-update", "rollback revert"),
        Tool("overview", "Quick fixes", "Free up disk space", "Remove things the computer no longer needs",
             "user-trash-symbolic", t + ["free-space"], "evenkeel-os-tools free-space", "clean storage"),
        Tool("overview", "Quick fixes", "Save problem details", "A file of recent errors to email to your helper",
             "document-save-symbolic", t + ["problem-details"], "evenkeel-os-tools problem-details",
             "logs report error"),
        Tool("overview", "Getting started", "Setup checklist",
             "Media codecs, disk unlock and getting apps, one at a time",
             "checkbox-checked-symbolic", t + ["setup"], "evenkeel-os-tools setup", "first start"),
        Tool("updates", "Updating", "System Update", "Update the system, apps, app boxes and Homebrew now",
             "software-update-available-symbolic", ["/usr/bin/evenkeel-os-update"], "evenkeel-os-update",
             "upgrade uupd"),
        Tool("updates", "Updating", "Automatic updates", "Turn them on or off", "alarm-symbolic",
             t + ["updates"], "evenkeel-os-tools updates", "pause resume"),
        Tool("updates", "Updating", "Update firmware", "Updates for the computer's own parts, like the BIOS",
             "preferences-system-symbolic", t + ["firmware"], "evenkeel-os-tools firmware", "fwupd uefi"),
        Tool("updates", "If something went wrong", "Undo the last update",
             "Go back to the version from before the last update. Automatic updates then pause for 3 days.",
             "edit-undo-symbolic", t + ["undo-update"], "evenkeel-os-tools undo-update", "rollback revert"),
        Tool("apps", "Get apps", "Get apps", "Browse and install apps in Bazaar. They update on their own.",
             "system-software-install-symbolic", ["gtk-launch", "io.github.kolunmi.Bazaar"], "",
             "bazaar store flathub"),
        Tool("apps", "Apps from package files", "Install a package file", "Pick an .rpm or .deb file from Downloads",
             "package-x-generic-symbolic", p + ["install"], "evenkeel-os-packages install", "rpm deb"),
        Tool("apps", "Apps from package files", "Remove apps",
             "Apps you added from files, Get a VPN or Windows programs",
             "user-trash-symbolic", p + ["remove"], "evenkeel-os-packages remove", "uninstall delete"),
        Tool("apps", "Apps from package files", "Start apps at login", "Pick which ones open when you log in",
             "media-playback-start-symbolic", p + ["login"], "evenkeel-os-packages login", "autostart"),
        Tool("apps", "Fixes and extras", "Repair app boxes", "Set a broken box up again. Your files aren't touched.",
             "applications-engineering-symbolic", p + ["repair"], "evenkeel-os-packages repair", "distrobox fix"),
        Tool("apps", "Fixes and extras", "Media codecs", "Optional formats left out for legal reasons",
             "applications-multimedia-symbolic", ["/usr/bin/evenkeel-os-codecs", "gui"], "evenkeel-os-codecs gui",
             "h264 video audio"),
        Tool("apps", "Fixes and extras", "Remove media codecs", "Take the extra formats out again",
             "edit-delete-symbolic", "codecs-remove", "evenkeel-os-codecs remove", "uninstall h264"),
        Tool("apps", "More ways to get apps", "Get a VPN", "Mullvad, Proton, IVPN or NordVPN, kept up to date",
             "network-vpn-symbolic", p + ["vpn"], "evenkeel-os-packages vpn", "mullvad proton ivpn nordvpn"),
        Tool("apps", "More ways to get apps", "Windows programs", "Pick an .exe or .msi to get its Linux version",
             "application-x-executable-symbolic", "windows", "evenkeel-os-packages windows FILE", "exe msi"),
        Tool("apps", "More ways to get apps", "Zoom meetings", "", "camera-video-symbolic", "zoom", "", "chrome"),
        Tool("disk", "Disk space", "Free up disk space", "Remove old system versions and unused app parts",
             "user-trash-symbolic", t + ["free-space"], "evenkeel-os-tools free-space", "clean storage"),
        Tool("disk", "Starting the computer", "Unlock disk automatically",
             "Skip the disk password at startup. Uses the computer's security chip.", "channel-secure-symbolic",
             t + ["disk-unlock"], "evenkeel-os-tools disk-unlock", "tpm luks encryption"),
        Tool("disk", "Starting the computer", "Restart into BIOS settings", "Open the computer's own settings screen",
             "system-reboot-symbolic", t + ["bios"], "evenkeel-os-tools bios", "uefi firmware setup"),
        Tool("yours", "Desktop layout", "Desktop layout",
             "Standard top bar, or Windows-style bottom bar and start menu",
             "view-grid-symbolic", "layout", "evenkeel-os-layout windows (or current)",
             "taskbar start menu windows-style dock top bar"),
        Tool("yours", "Colors and wallpaper", "Accent color and wallpaper",
             "Teal to start. Folder icons follow whatever color you pick.", "applications-graphics-symbolic",
             ["gnome-control-center", "background"], "", "theme folder appearance background"),
        Tool("help", "Something not right?", "Undo the last update",
             "If it started after an update, go back to the version from before it", "edit-undo-symbolic",
             t + ["undo-update"], "evenkeel-os-tools undo-update", "rollback revert"),
        Tool("help", "Something not right?", "Save problem details",
             "Makes one file of recent errors. Email it to your helper.", "document-save-symbolic",
             t + ["problem-details"], "evenkeel-os-tools problem-details", "logs report error"),
        Tool("help", "Check that it can't break", "Test automatic rollback",
             "Check that the computer goes back by itself when a new version won't start", "view-refresh-symbolic",
             t + ["test-rollback"], "evenkeel-os-tools test-rollback", "greenboot"),
    ]


class Window(Adw.ApplicationWindow):
    def __init__(self, app, tools_module):
        super().__init__(application=app, title="System Tools", default_width=1040, default_height=760)
        self.t = tools_module
        self.tools = tool_list()
        self.toasts = Adw.ToastOverlay()
        self.subtitles = {}          # Tool -> its row, for rows whose text shows the current state
        self.running = set()         # tools whose windows are open, so a second click doesn't start another
        self.banner = None
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        for key, name, _ in PAGES:
            self.stack.add_named(self.page(key), key)
        self.results = Adw.PreferencesGroup()
        search_page = Adw.PreferencesPage()
        search_page.add(self.results)
        self.stack.add_named(search_page, "search")

        self.content_title = Adw.WindowTitle(title="Overview")
        content_bar = Adw.HeaderBar(title_widget=self.content_title)
        content = Adw.ToolbarView(content=self.stack)
        content.add_top_bar(content_bar)

        self.search = Gtk.SearchEntry(placeholder_text="Search tools", margin_start=10, margin_end=10,
                                      margin_bottom=6)
        self.search.connect("search-changed", self.on_search)
        self.search.connect("activate", lambda *_: self.split.set_show_content(True))
        self.sidebar = Gtk.ListBox(css_classes=["navigation-sidebar"])
        for key, name, icon in PAGES:
            box = Gtk.Box(spacing=12, margin_top=8, margin_bottom=8, margin_start=6)
            box.append(Gtk.Image.new_from_icon_name(icon))
            box.append(Gtk.Label(label=name, xalign=0))
            r = Gtk.ListBoxRow(child=box)
            r.key = key
            self.sidebar.append(r)
        self.sidebar.connect("row-selected", self.on_page)
        self.sidebar.connect("row-activated", self.on_page)       # the page already shown, picked again after a search
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        side.append(self.search)
        side.append(Gtk.ScrolledWindow(child=self.sidebar, vexpand=True))
        side_view = Adw.ToolbarView(content=side)
        side_view.add_top_bar(Adw.HeaderBar(title_widget=Adw.WindowTitle(title="System Tools")))

        split = Adw.NavigationSplitView(sidebar=Adw.NavigationPage(child=side_view, title="System Tools"),
                                        content=Adw.NavigationPage(child=content, title="Overview"),
                                        min_sidebar_width=230, max_sidebar_width=260)
        self.split = split
        self.toasts.set_child(split)
        self.set_content(self.toasts)
        bp = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 640sp"))
        bp.add_setter(split, "collapsed", True)
        self.add_breakpoint(bp)
        self.refresh()

    # ------------------------------------------------------------ pages

    def page(self, key):
        page = Adw.PreferencesPage()
        if key == "overview":
            page.add(self.overview_banner())
        if key == "apps":
            page.add(self.drop_zone())
        groups = {}
        if key == "disk":
            groups["Disk space"] = self.disk_space()
            page.add(groups["Disk space"])
        if key == "yours":
            page.add(self.layout_picker())
        for tool in self.tools:
            if tool.page != key or tool.run == "layout":      # the layout row is the picker; search finds it
                continue
            if tool.group not in groups:
                groups[tool.group] = Adw.PreferencesGroup(title=tool.group)
                page.add(groups[tool.group])
            groups[tool.group].add(self.row(tool))
        if key == "updates":
            g = Adw.PreferencesGroup(title="Apps from their own download sources")
            g.add(Adw.ActionRow(title="Checked every day too",
                                subtitle="VPNs, codecs and apps added to the system, while automatic updates are on. "
                                         "New versions start at the next restart.",
                                icon_name="view-refresh-symbolic"))
            page.add(g)
        if key == "help":
            page.add(self.terminal_list())
        return page

    def row(self, tool, where=""):
        r = Adw.ActionRow(title=tool.title, subtitle=where or tool.about, activatable=True)
        r.add_prefix(Gtk.Image.new_from_icon_name(tool.icon))
        r.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        r.connect("activated", lambda *_: self.activate_tool(tool))
        if not where:
            self.subtitles.setdefault(tool.title, []).append(r)
        return r

    def overview_banner(self):
        g = Adw.PreferencesGroup()
        box = Gtk.Box(spacing=20, css_classes=["ek-banner"])
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, hexpand=True, valign=Gtk.Align.CENTER)
        self.banner_title = Gtk.Label(xalign=0, wrap=True, css_classes=["title-2"])
        self.banner_sub = Gtk.Label(xalign=0, wrap=True, css_classes=["ek-sub"])
        text.append(self.banner_title)
        text.append(self.banner_sub)
        self.banner_button = Gtk.Button(valign=Gtk.Align.CENTER, css_classes=["pill"], visible=False)
        self.banner_button.connect("clicked", self.on_banner_button)
        self.banner_icon = Gtk.Image(icon_name="object-select-symbolic", pixel_size=40)
        box.append(self.banner_icon)
        box.append(text)
        box.append(self.banner_button)
        self.banner = box
        g.add(box)
        return g

    def drop_zone(self):
        g = Adw.PreferencesGroup()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, css_classes=["ek-drop"])
        box.append(Gtk.Image(icon_name="document-send-symbolic", pixel_size=32))
        box.append(Gtk.Label(label="Drop a file here", css_classes=["title-4"]))
        box.append(Gtk.Label(label="An .rpm or .deb installs the app. An .exe or .msi gets its Linux version.",
                             wrap=True, justify=Gtk.Justification.CENTER, css_classes=["dim-label"]))
        target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        target.connect("enter", lambda *_: box.add_css_class("ek-over") or Gdk.DragAction.COPY)
        target.connect("leave", lambda *_: box.remove_css_class("ek-over"))
        target.connect("drop", self.on_drop, box)
        box.add_controller(target)
        g.add(box)
        return g

    def disk_space(self):
        g = Adw.PreferencesGroup(title="Disk space")
        self.disk_row = Adw.ActionRow(title="Reading the disk")
        self.disk_bar = Gtk.LevelBar(min_value=0, max_value=1, valign=Gtk.Align.CENTER, width_request=180)
        self.disk_row.add_suffix(self.disk_bar)
        g.add(self.disk_row)
        return g

    def layout_picker(self):
        g = Adw.PreferencesGroup(title="Desktop layout",
                                 description="A new layout shows after you log out and back in. It changes only "
                                             "your own desktop.")
        box = Gtk.Box(spacing=16, homogeneous=True)
        r = subprocess.run(["/usr/bin/evenkeel-os-layout"], capture_output=True, text=True)
        now = r.stdout.strip() or "current"
        first = None
        self.layout_buttons = []
        for key, name, about in (("current", "Standard", "Top bar, apps from the bottom dock"),
                                 ("windows", "Windows-style", "Bottom bar and a start menu")):
            b = Gtk.ToggleButton(css_classes=["ek-layout"], active=key == now, group=first)
            first = first or b
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            head = Gtk.Box(spacing=8)
            head.append(Gtk.Label(label=name, xalign=0, hexpand=True, css_classes=["heading"]))
            tick = Gtk.Image(icon_name="object-select-symbolic", visible=key == now)
            b.connect("toggled", lambda btn, i=tick: i.set_visible(btn.get_active()))
            head.append(tick)
            inner.append(head)
            inner.append(Gtk.Label(label=about, xalign=0, css_classes=["dim-label"]))
            b.set_child(inner)
            b.connect("toggled", self.on_layout, key)
            self.layout_buttons.append(b)
            box.append(b)
        g.add(box)
        return g

    def terminal_list(self):
        g = Adw.PreferencesGroup(title="Prefer the terminal?", description="Every tool here has a command.")
        seen = set()
        for tool in self.tools:
            if tool.command and tool.command not in seen:
                seen.add(tool.command)
                r = Adw.ActionRow(title=tool.command, subtitle=tool.title, css_classes=["property"])
                r.set_subtitle_selectable(True)
                g.add(r)
        return g

    # ------------------------------------------------------------ state

    def refresh(self, *_):
        threading.Thread(target=self.read_state, daemon=True).start()

    def read_state(self):
        on = self.t.updates_on()
        state = {"on": on, "paused": on and self.t.paused_until(), "unlock": self.t.DISK_UNLOCK_ON.exists(),
                 "disk": shutil.disk_usage("/var/home" if os.path.isdir("/var/home") else str(Path.home())),
                 "chrome": bool(zoom.chrome_command()), "usual": zoom_usual_browser()}
        ds = self.t.deployments() or []
        state["staged"] = next((d for d in ds if d.get("staged")), None)
        booted = next((d for d in ds if d.get("booted")), None)
        state["since"] = self.t.when(booted) if booted else ""
        GLib.idle_add(self.show_state, state)

    def show_state(self, s):
        if s["staged"]:
            title, sub, button, warn = ("A new version is ready", "It starts when you restart the computer.",
                                        "Restart now", False)
        elif s["paused"]:
            title, sub, button, warn = (f"Automatic updates are paused until {self.t.day(s['paused'])}",
                                        "After an undo, so the same update doesn't come straight back. They turn back "
                                        "on by themselves.", "Resume now", True)
        elif not s["on"]:
            title, sub, button, warn = ("Automatic updates are off", "Nothing updates until you run System Update.",
                                        "Turn on", True)
        else:
            title, sub, button, warn = ("Your computer is in good shape", "Automatic updates are on.", "Update now",
                                        False)
        if s["since"]:
            sub += f" This version is from {s['since']}."
        self.banner_title.set_label(title)
        self.banner_sub.set_label(sub)
        self.banner_button.set_label(button)
        self.banner.remove_css_class("ek-warn")
        self.banner_icon.set_from_icon_name("emblem-important-symbolic" if warn else "object-select-symbolic")
        if warn:
            self.banner.add_css_class("ek-warn")
        self.banner_button.set_visible(True)
        d, mb = s["disk"], 1_000_000
        self.disk_row.set_title(f"{self.t.human(d.free // mb)} free")
        self.disk_row.set_subtitle(f"{self.t.human(d.used // mb)} of {self.t.human(d.total // mb)} used")
        self.disk_bar.set_value(d.used / d.total if d.total else 0)
        auto = "On" if s["on"] and not s["paused"] else "Paused" if s["paused"] else "Off"
        self.set_subtitle("Automatic updates", f"{auto}. Turn them on or off.")
        self.set_subtitle("Unlock disk automatically",
                          ("On. " if s["unlock"] else "Off. ") + "Skip the disk password at startup.")
        self.usual = s["usual"]
        self.set_subtitle("Zoom meetings", "They open in Chrome." if s["chrome"] else
                          "They open in your usual browser. Choose to be asked about Chrome again." if s["usual"] else
                          "The first meeting asks whether to install Chrome or use your usual browser.")
        return False

    def set_subtitle(self, title, text):
        for r in self.subtitles.get(title, []):
            r.set_subtitle(text)

    # ------------------------------------------------------------ actions

    def activate_tool(self, tool):
        if tool.run == "windows":
            self.pick_windows_file()
        elif tool.run == "zoom":
            self.zoom_choice()
        elif tool.run == "layout":
            self.show("yours")
        elif tool.run == "codecs-remove":
            self.remove_codecs()
        elif tool.title in self.running:
            self.toast(f"{tool.title} is already open.")
        elif spawn(tool.run, lambda rc, t=tool.title: self.finished(t)):
            self.running.add(tool.title)
        else:
            self.toast(f"{tool.title} didn't start.")

    def finished(self, title):
        self.running.discard(title)
        self.refresh()

    def remove_codecs(self):
        d = Adw.AlertDialog(heading="Remove the media codecs?",
                            body="Video and audio that need them stop playing. Needs your password and a restart.")
        d.add_response("cancel", "Cancel")
        d.add_response("remove", "Remove")
        d.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)

        def answered(dialog, response):
            if response == "remove":
                spawn(["/usr/bin/evenkeel-os-codecs", "remove"],
                      lambda rc: self.toast("The codecs are removed. Restart to finish." if rc == 0 else
                                            "The codecs weren't removed."))
        d.connect("response", answered)
        d.present(self)

    def on_banner_button(self, button):
        label = button.get_label()
        if label == "Restart now":
            spawn(["gnome-session-quit", "--reboot"])
        elif label in ("Resume now", "Turn on"):
            spawn([TOOLS, "updates"], self.refresh)
        else:
            self.activate_tool(next(t for t in self.tools if t.title == "System Update"))

    def on_page(self, box, row):
        if row is None:
            return
        self.search.set_text("")
        self.stack.set_visible_child_name(row.key)
        self.content_title.set_title(dict((k, n) for k, n, _ in PAGES)[row.key])
        self.split.set_show_content(True)

    def on_search(self, entry):
        words = entry.get_text().lower().split()
        if not words:
            row = self.sidebar.get_selected_row()
            self.stack.set_visible_child_name(row.key if row else "overview")
            return
        page = self.stack.get_child_by_name("search")
        page.remove(self.results)
        self.results = Adw.PreferencesGroup(title="Matching tools")
        names = dict((k, n) for k, n, _ in PAGES)
        shown = set()
        for tool in self.tools:
            if tool.matches(words) and tool.title not in shown:
                shown.add(tool.title)
                self.results.add(self.row(tool, where=f"{names[tool.page]}: {tool.about}".rstrip(": ")))
        if not shown:
            self.results.set_description("No tool matches. Try another word.")
        page.add(self.results)
        self.stack.set_visible_child_name("search")
        self.content_title.set_title("Search")
        if not self.split.get_collapsed():      # narrow window: the results show on Enter, keeping the box in view
            self.split.set_show_content(True)

    def on_drop(self, target, value, x, y, box):
        box.remove_css_class("ek-over")
        files = [f.get_path() for f in value.get_files() if f.get_path()]
        if not files:
            self.toast("Save the file to your computer first, then drop it here.")
            return False
        if len(files) > 1:
            self.toast("One file at a time: the first one is opening.")
        for f in files[:1]:
            low = f.lower()
            if low.endswith(PACKAGE_TYPES):
                spawn([PACKAGES, "install", f], self.refresh)
            elif low.endswith(WINDOWS_TYPES):
                spawn([PACKAGES, "windows", f], self.refresh)
            else:
                self.toast("Drop an .rpm, .deb, .exe or .msi file.")
                return False
        return bool(files)

    def pick_windows_file(self):
        f = Gtk.FileFilter(name="Windows programs (.exe, .msi)")
        for pattern in ("*.exe", "*.msi", "*.EXE", "*.MSI"):
            f.add_pattern(pattern)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        downloads = Path.home() / "Downloads"
        dialog = Gtk.FileDialog(title="Pick a Windows program", filters=filters, default_filter=f)
        if downloads.is_dir():
            dialog.set_initial_folder(Gio.File.new_for_path(str(downloads)))

        def picked(d, result):
            try:
                path = d.open_finish(result).get_path()
            except GLib.Error:
                return
            spawn([PACKAGES, "windows", path], self.refresh)
        dialog.open(self, None, picked)

    def zoom_choice(self):
        if not getattr(self, "usual", False):
            self.toast("Nothing to change: Zoom meetings open in Chrome, or the first one asks.")
            return
        zoom.CHOICE.unlink(missing_ok=True)
        self.toast("Done. The next Zoom meeting asks about Chrome again.")
        self.refresh()

    def on_layout(self, button, key):
        if not button.get_active():
            return
        r = subprocess.run(["/usr/bin/evenkeel-os-layout"], capture_output=True, text=True)
        if r.stdout.strip() == key:
            return
        if subprocess.run(["/usr/bin/evenkeel-os-layout", key], capture_output=True).returncode == 0:
            self.toast("Log out and back in to see the new layout.")
            return
        self.toast("The layout didn't change.")
        for b in self.layout_buttons:
            if b is not button:
                b.set_active(True)

    def toast(self, text):
        self.toasts.add_toast(Adw.Toast(title=text, timeout=6))

    def show(self, page):
        keys = [k for k, _, _ in PAGES]
        self.sidebar.select_row(self.sidebar.get_row_at_index(keys.index(page) if page in keys else 0))
        self.present()
        self.sidebar.get_selected_row().grab_focus()      # not the search box, so its hint stays readable


def run(tools_module, page="overview"):
    """Open the window (or bring it to the front, on the page asked for)."""
    app = Adw.Application(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS)

    def command_line(a, cl):
        args = cl.get_arguments()[1:]
        want = next((x.split("=", 1)[1] for x in args if x.startswith("--page=")), page)
        win = a.get_active_window()
        if win is None:
            Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider,
                                                      Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            win = Window(a, tools_module)
        win.show(want)
        return 0
    app.connect("command-line", command_line)
    return app.run([TOOLS, f"--page={page}"])
