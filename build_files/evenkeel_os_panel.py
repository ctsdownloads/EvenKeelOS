"""The System Tools window: every EvenKeelOS tool, on pages in one window."""
import os
import shutil
import socket
import subprocess
import threading
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402
import evenkeel_os_bootopts as bootopts  # noqa: E402
import evenkeel_os_guide as guide  # noqa: E402
import evenkeel_os_network as net  # noqa: E402
import evenkeel_os_sharing as sharing  # noqa: E402
from evenkeel_os_dialogs import Dialogs  # noqa: E402
from evenkeel_os_packages import zoom  # noqa: E402

APP_ID = "io.github.ctsdownloads.evenkeel-os.Tools"
TOOLS = "/usr/bin/evenkeel-os-tools"
ADMIN = ["pkexec", "/usr/libexec/evenkeel-os-tools-admin"]
BOOT_OPTIONS = ["pkexec", "/usr/libexec/evenkeel-os-boot-options"]
PACKAGES = "/usr/bin/evenkeel-os-packages"
OURS = (TOOLS, PACKAGES, "/usr/bin/evenkeel-os-update", "/usr/bin/evenkeel-os-codecs")   # their windows show here
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
         ("network", "Network safety", "security-high-symbolic"),
         ("sharing", "Shared folders", "folder-remote-symbolic"),
         ("disk", "Disk and startup", "drive-harddisk-symbolic"),
         ("yours", "Make it yours", "applications-graphics-symbolic"),
         ("help", "Get help", "help-about-symbolic")]


def spawn(argv, done=None, panel=None):
    """Start a program; done(exit code) runs in the window once it has ended. panel: the socket for its windows."""
    launcher = Gio.SubprocessLauncher.new(Gio.SubprocessFlags.NONE)
    if panel:
        launcher.setenv("EVENKEEL_OS_PANEL", panel, True)
    try:
        proc = launcher.spawnv(argv)
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
        Tool("network", "This network", "Network safety", "Home, Work or Public place, and what each lets in",
             "security-high-symbolic", "network",
             "nmcli connection modify NETWORK connection.zone evenkeel-home (or evenkeel-work, evenkeel-public)",
             "firewall wifi wi-fi wired zone home work public ssh printer ports"),
        Tool("sharing", "Shared folders", "Shared folders",
             "Let computers on your Home network open folders you pick, with a password",
             "folder-remote-symbolic", "sharing",
             "pkexec /usr/libexec/evenkeel-os-tools-admin sharing add FOLDER ro (or rw)",
             "samba smb share sharing windows mac network folder files nas"),
        Tool("disk", "Disk space", "Free up disk space", "Remove old system versions and unused app parts",
             "user-trash-symbolic", t + ["free-space"], "evenkeel-os-tools free-space", "clean storage"),
        Tool("disk", "Starting the computer", "Unlock disk automatically",
             "Skip the disk password at startup. Uses the computer's security chip.", "channel-secure-symbolic",
             t + ["disk-unlock"], "evenkeel-os-tools disk-unlock", "tpm luks encryption"),
        Tool("disk", "Boot options", "Boot options",
             "Fixes for screen flicker and drive freezes, or your own kernel settings", "preferences-other-symbolic",
             "bootopts", "pkexec /usr/libexec/evenkeel-os-boot-options set SETTING... (the full list)",
             "kernel arguments karg kargs grub flicker psr panel replay amdgpu i915 xe nvme freeze"),
        Tool("disk", "Starting the computer", "Restart into BIOS settings", "Open the computer's own settings screen",
             "system-reboot-symbolic", t + ["bios"], "evenkeel-os-tools bios", "uefi firmware setup"),
        Tool("yours", "Desktop layout", "Desktop layout",
             "Standard top bar, or Windows-style bottom bar and start menu",
             "view-grid-symbolic", "layout", "evenkeel-os-layout windows (or current)",
             "taskbar start menu windows-style dock top bar"),
        Tool("yours", "Colors and wallpaper", "Accent color and wallpaper",
             "Teal to start. Folder icons follow whatever color you pick.", "applications-graphics-symbolic",
             ["gnome-control-center", "background"], "", "theme folder appearance background"),
        Tool("help", "How to do things", "EvenKeelOS guide",
             "How to do things, step by step: the desktop, files, apps and more", "help-about-symbolic",
             "guide", "evenkeel-os-tools --page=guide", "guide manual help how to tutorial windows beginner"),
        *[Tool("help", "How to do things", title, about, icon, f"guide-{key}", "",
               "guide how to " + " ".join(h for h, _ in articles))
          for key, title, icon, about, articles in guide.TOPICS],
        Tool("help", "Something not right?", "Undo the last update",
             "If it started after an update, go back to the version from before it", "edit-undo-symbolic",
             t + ["undo-update"], "evenkeel-os-tools undo-update", "rollback revert"),
        Tool("help", "Something not right?", "Save problem details",
             "Makes one file of recent errors. Email it to your helper.", "document-save-symbolic",
             t + ["problem-details"], "evenkeel-os-tools problem-details", "logs report error"),
        Tool("help", "Check that it can't break", "Test automatic rollback",
             "Check that the computer goes back by itself when a new version won't start, and puts back deleted "
             "settings", "view-refresh-symbolic", t + ["test-rollback"], "evenkeel-os-tools test-rollback",
             "greenboot repair settings"),
        Tool("help", "Check that it can't break", "Certificate alerts",
             "Security certificates that expired, expire within 30 days or were removed", "security-high-symbolic",
             t + ["certificates"], "evenkeel-os-tools certificates", "certificate ssl tls https trust expire"),
    ]


class Window(Adw.ApplicationWindow):
    def __init__(self, app, tools_module):
        super().__init__(application=app, title="System Tools", default_width=1040, default_height=760)
        self.t = tools_module
        self.tools = tool_list()
        self.toasts = Adw.ToastOverlay()
        self.subtitles = {}          # Tool -> its row, for rows whose text shows the current state
        self.current = None          # the tool running now: one at a time, its windows on the "tool" page
        self.current_argv = None
        self.before = "overview"     # the page to go back to from the tool page
        self.dialogs = Dialogs(self, self.on_dialogs)
        self.banner = None
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        for key, name, _ in PAGES:
            self.stack.add_named(self.page(key), key)
        self.results = Adw.PreferencesGroup()
        search_page = Adw.PreferencesPage()
        search_page.add(self.results)
        self.stack.add_named(search_page, "search")
        self.stack.add_named(self.dialogs.widget, "tool")
        self.trail = []              # pages the back arrow returns to, newest last
        self.guide_pages()

        self.content_title = Adw.WindowTitle(title="Overview")
        content_bar = Adw.HeaderBar(title_widget=self.content_title)
        self.back = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text="Back", visible=False)
        self.back.connect("clicked", lambda *_: self.go_back())
        content_bar.pack_start(self.back)
        content = Adw.ToolbarView(content=self.stack)
        content.add_top_bar(content_bar)
        self.waiting = Adw.Banner(button_label="Show")     # a tool is open while another page is shown
        self.waiting.connect("button-clicked", lambda *_: self.show_tool())
        content.add_top_bar(self.waiting)

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
        self.connect("close-request", self.on_close)
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
        if key == "network":
            self.network_page(page)
        if key == "sharing":
            self.sharing_page(page)
        for tool in self.tools:
            if tool.page != key or tool.run in ("layout", "network", "sharing", "bootopts"):  # shown as a section
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
        if key == "disk":
            self.boot_section(page)
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

    def guide_pages(self):
        """The guide: a list of topics, and a page of numbered steps for each. Show me opens what a step names."""
        home = Adw.PreferencesPage()
        home.add(self.guide_banner(guide.TITLE, guide.INTRO))
        g = Adw.PreferencesGroup()
        for key, title, icon, about, _ in guide.TOPICS:
            row = Adw.ActionRow(title=title, subtitle=about, activatable=True)
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            row.connect("activated", lambda *_, k=key: self.go(f"guide-{k}"))
            g.add(row)
        home.add(g)
        self.stack.add_named(home, "guide")
        for key, title, _icon, about, articles in guide.TOPICS:
            page = Adw.PreferencesPage()
            page.add(self.guide_banner(title, about + "."))
            for heading, steps in articles:
                g = Adw.PreferencesGroup(title=heading)
                for n, (text, show) in enumerate(steps, 1):
                    row = Adw.ActionRow(title=text, title_lines=0)
                    row.add_prefix(Gtk.Label(label=f"{n}", width_chars=2, css_classes=["heading", "dim-label"]))
                    if show:
                        b = Gtk.Button(label="Show me", valign=Gtk.Align.CENTER)
                        b.update_property([Gtk.AccessibleProperty.LABEL], [f"Show me: {self.guide_target(show)}"])
                        b.connect("clicked", lambda *_, s=show: self.on_show_me(s))
                        row.add_suffix(b)
                    g.add(row)
                page.add(g)
            if key == guide.WELCOME:
                g = Adw.PreferencesGroup()
                more = Adw.ActionRow(title="The full guide", subtitle="How to do things, step by step",
                                     activatable=True)
                more.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
                more.connect("activated", lambda *_: self.go("guide"))
                g.add(more)
                self.guide_hide = Gtk.CheckButton(label="Don't show this again at login", visible=False,
                                                  margin_top=12)
                self.guide_hide.connect("toggled", self.on_guide_hide)
                g.add(self.guide_hide)
                page.add(g)
            self.stack.add_named(page, f"guide-{key}")

    @staticmethod
    def guide_banner(title, text):
        g = Adw.PreferencesGroup()
        box = Gtk.Box(spacing=20, css_classes=["ek-banner"])
        box.append(Gtk.Image(icon_name="help-about-symbolic", pixel_size=40))
        words = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, hexpand=True, valign=Gtk.Align.CENTER)
        words.append(Gtk.Label(label=title, xalign=0, wrap=True, css_classes=["title-2"]))
        words.append(Gtk.Label(label=text, xalign=0, wrap=True, css_classes=["ek-sub"]))
        box.append(words)
        g.add(box)
        return g

    @staticmethod
    def guide_target(show):
        kind, _, key = show.partition(":")
        if kind == "page":
            return dict((k, n) for k, n, _ in PAGES)[key]
        if kind == "topic":
            return guide.topic(key)[1]
        return "Settings"

    def on_show_me(self, show):
        kind, _, key = show.partition(":")
        if kind == "settings":
            if not spawn(["gnome-control-center", key]):
                self.toast("Settings didn't open.")
        else:
            self.go(key if kind == "page" else f"guide-{key}")

    def page_title(self, name):
        if name == "guide":
            return guide.TITLE
        if name.startswith("guide-"):
            return guide.topic(name[len("guide-"):])[1]
        return dict((k, n) for k, n, _ in PAGES).get(name, "Search")

    def go(self, name):
        """Open a page from inside another; the back arrow returns, one page at a time."""
        here = self.stack.get_visible_child_name()
        if here != name:
            self.trail.append(self.before if here == "tool" else here)
        self.stack.set_visible_child_name(name)
        self.content_title.set_title(self.page_title(name))
        self.back.set_visible(True)
        self.show_waiting()
        self.split.set_show_content(True)

    def open_guide(self, at_login=False):
        if at_login:
            self.guide_hide.set_visible(True)
        self.go(f"guide-{guide.WELCOME}" if at_login else "guide")
        self.present()

    def on_guide_hide(self, button):
        try:
            if button.get_active():
                self.t.STATE.mkdir(parents=True, exist_ok=True)
                self.t.GUIDE_HIDDEN.touch()
            else:
                self.t.GUIDE_HIDDEN.unlink(missing_ok=True)
        except OSError:
            self.toast("That couldn't be saved.")

    def network_page(self, page):
        """Which place the network you're on is, every saved network's place, and what Home and Work let in."""
        box = Gtk.Box(spacing=20, css_classes=["ek-banner"])
        box.append(Gtk.Image(icon_name="security-high-symbolic", pixel_size=40))
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, hexpand=True, valign=Gtk.Align.CENTER)
        self.net_title = Gtk.Label(xalign=0, wrap=True, css_classes=["title-2"], label="Checking the network…")
        self.net_sub = Gtk.Label(xalign=0, wrap=True, css_classes=["ek-sub"])
        text.append(self.net_title)
        text.append(self.net_sub)
        box.append(text)
        self.net_fix = Gtk.Button(label="Fix", valign=Gtk.Align.CENTER, css_classes=["pill"], visible=False)
        self.net_fix.connect("clicked", lambda *_: self.admin(["firewall", "default"],
                                                              "New networks are a Public place now."))
        box.append(self.net_fix)
        self.net_banner = box
        g = Adw.PreferencesGroup()
        g.add(box)
        page.add(g)
        self.net_list = Adw.PreferencesGroup(title="Your networks",
                                             description="Home and Work let in phones, file sharing and apps you "
                                                         "run. A Public place lets nothing in.")
        page.add(self.net_list)
        self.net_rows = []
        g = Adw.PreferencesGroup(title="Also let in, on Home and Work",
                                 description="Never on a Public place. Each change asks for your password.")
        self.net_switches = {}
        for service, title, about in (("ssh", "Log in from another computer (SSH)", "Off unless you need it"),
                                      ("ipp", "Share my printer", "Other computers print to a printer plugged "
                                                                  "into this one")):
            row = Adw.SwitchRow(title=title, subtitle=about, sensitive=False)
            row.connect("notify::active", self.on_net_switch, service)
            self.net_switches[service] = row
            g.add(row)
        page.add(g)
        self.net_updating = False

    def show_network(self, nets, default, services):
        self.net_updating = True
        on = next((n for n in nets if n.device), None)
        public = default == net.PUBLIC
        if default is None:
            self.net_title.set_label("The firewall isn't answering")
            self.net_sub.set_label("Network safety can't check or change it right now. Restart the computer. If "
                                   "this stays, use Save problem details in Get help.")
        elif on:
            zone = on.zone or default or net.PUBLIC
            what = {net.HOME: "your home network", net.WORK: "your work network", net.PUBLIC: "a public place"}
            self.net_title.set_label(f"{on.name} is {what[zone]}" if zone in what else
                                     f"{on.name} uses another firewall setting: {zone}")
            self.net_sub.set_label(net.LETS_IN.get(zone, "Pick Home, Work or Public place for it below."))
        else:
            self.net_title.set_label("Not connected")
            self.net_sub.set_label("The next network you join starts as a Public place.")
        self.net_banner.remove_css_class("ek-warn")
        self.net_fix.set_visible(not public and default is not None)
        if not public:
            self.net_banner.add_css_class("ek-warn")
        if default is not None and not public:
            self.net_sub.set_label("New networks on this computer aren't a Public place yet. Fix sets that.")
        for row in self.net_rows:
            self.net_list.remove(row)
        self.net_rows = []
        names = list(net.PLACES.values())
        for n in nets:
            zone = n.zone or default or net.PUBLIC
            about = n.kind + (", connected now" if n.device else "")
            if n.fixed_public:
                if zone == net.PUBLIC:
                    row = Adw.ActionRow(title=n.name, subtitle=f"{about}. Open Wi-Fi is always a Public place.")
                    row.add_suffix(Gtk.Label(label=net.PLACES[net.PUBLIC], css_classes=["dim-label"]))
                else:       # set another way (a terminal); open Wi-Fi shouldn't let anything in
                    row = Adw.ActionRow(title=n.name, subtitle=f"{about}. Open Wi-Fi, but set to "
                                        f"{net.PLACES.get(zone, zone)}. Anyone can make a network with its name.")
                    fix = Gtk.Button(label="Make it a Public place", valign=Gtk.Align.CENTER)
                    fix.connect("clicked", lambda *_, n=n: self.save_place(n, net.PUBLIC))
                    row.add_suffix(fix)
                self.net_list.add(row)
                self.net_rows.append(row)
                continue
            if n.kind == "Wired":
                about += ". Applies to every cable you plug in, not only this one"
            choices = names + ([] if zone in net.PLACES else [f"Other ({zone})"])
            row = Adw.ComboRow(title=n.name, model=Gtk.StringList.new(choices), subtitle=about)
            row.set_selected(list(net.PLACES).index(zone) if zone in net.PLACES else len(names))
            row.connect("notify::selected", self.on_place, n)
            self.net_list.add(row)
            self.net_rows.append(row)
        if not nets:
            row = Adw.ActionRow(title="No saved networks yet")
            self.net_list.add(row)
            self.net_rows.append(row)
        for service, row in self.net_switches.items():
            row.set_sensitive(services is not None)
            row.set_active(bool(services) and service in services)
        self.net_updating = False

    def on_place(self, row, _param, network):
        zones = list(net.PLACES)
        if self.net_updating or row.get_selected() >= len(zones):
            return
        self.save_place(network, zones[row.get_selected()])

    def save_place(self, network, zone):
        def save():
            done = net.set_place(network, zone)
            GLib.idle_add(self.toast, {"now": f"{network.name} is {net.PLACES[zone]} now.",
                                       "later": f"{network.name} is {net.PLACES[zone]} from the next time it "
                                                "connects."}.get(done, f"{network.name} didn't change. Try again."))
            GLib.idle_add(self.refresh)
        threading.Thread(target=save, daemon=True).start()

    def on_net_switch(self, row, _param, service):
        if not self.net_updating:
            self.admin(["firewall", service, "on" if row.get_active() else "off"],
                       f"{row.get_title()}: {'on' if row.get_active() else 'off'}.")

    def admin(self, args, done_text):
        """A firewall change as administrator (asks for the password); the page shows what really happened."""
        def done(rc):
            self.toast(done_text if rc == 0 else "Nothing changed.")
            self.refresh()
        if not spawn(ADMIN + args, done):
            self.toast("Nothing changed.")
            self.refresh()

    def sharing_page(self, page):
        """Whether sharing is on and working here, the sharing password, and the folders shared."""
        box = Gtk.Box(spacing=20, css_classes=["ek-banner"])
        box.append(Gtk.Image(icon_name="folder-remote-symbolic", pixel_size=40))
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, hexpand=True, valign=Gtk.Align.CENTER)
        self.share_title = Gtk.Label(xalign=0, wrap=True, css_classes=["title-2"], label="Checking sharing…")
        self.share_sub = Gtk.Label(xalign=0, wrap=True, css_classes=["ek-sub"])
        text.append(self.share_title)
        text.append(self.share_sub)
        box.append(text)
        self.share_banner = box
        g = Adw.PreferencesGroup()
        g.add(box)
        page.add(g)
        g = Adw.PreferencesGroup(title="Sharing", description="For everyone on this computer, on Home networks "
                                 "only, never on Work or a Public place. Changes ask for an administrator password.")
        self.share_switch = Adw.SwitchRow(title="Share folders on Home networks", sensitive=False)
        self.share_switch.connect("notify::active", self.on_share_switch)
        g.add(self.share_switch)
        self.share_pw = Adw.ActionRow(title="Sharing password")
        self.share_pw_button = Gtk.Button(label="Set", valign=Gtk.Align.CENTER)
        self.share_pw_button.connect("clicked", lambda *_: self.ask_share_password(False))
        self.share_pw.add_suffix(self.share_pw_button)
        g.add(self.share_pw)
        page.add(g)
        self.share_list = Adw.PreferencesGroup(title="Folders", description="Other computers open these as you, "
                                               "so whatever they save belongs to you.")
        add = Gtk.Button(label="Add a folder", valign=Gtk.Align.CENTER)
        add.connect("clicked", lambda *_: self.pick_share_folder())
        self.share_list.set_header_suffix(add)
        page.add(self.share_list)
        self.share_rows = []
        self.share_state = sharing.load()
        self.share_updating = False

    def show_sharing(self, state, nets, ready, running):
        self.share_updating = True
        self.share_state = state
        user = GLib.get_user_name()
        has_pw = user in state["passwords"]
        home = [n for n in nets if n.device and n.zone == net.HOME]
        shared = any(f["owner"] in state["passwords"] for f in state["folders"])
        title, sub, warn = self.sharing_banner(state, nets, ready, running, home, shared)
        self.share_title.set_label(title)
        self.share_sub.set_label(sub)
        self.share_banner.remove_css_class("ek-warn")
        if warn:
            self.share_banner.add_css_class("ek-warn")
        self.share_switch.set_sensitive(ready or state["on"])      # off works even where smb.conf was replaced
        self.share_switch.set_active(state["on"])
        self.share_pw.set_subtitle(f"Other computers ask for your user name, {user}, and this password. It isn't "
                                   "your login password." + ("" if has_pw else " Not set yet."))
        self.share_pw_button.set_label("Change" if has_pw else "Set")
        for row in self.share_rows:
            self.share_list.remove(row)
        self.share_rows = []
        home_dir = GLib.get_home_dir()
        for f in (f for f in state["folders"] if f["owner"] == user):
            where = "~" + f["path"][len(home_dir):] if f["path"].startswith(home_dir + "/") else f["path"]
            row = Adw.ActionRow(title=f["name"], subtitle=where if os.path.isdir(f["path"]) else
                                f"{where}. Folder not found: it was moved or deleted.")
            mode = Gtk.DropDown.new_from_strings(list(sharing.MODES.values()))
            mode.set_valign(Gtk.Align.CENTER)
            mode.set_selected(list(sharing.MODES).index(f["mode"]))
            mode.connect("notify::selected", self.on_share_mode, f)
            row.add_suffix(mode)
            remove = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Stop sharing it",
                                valign=Gtk.Align.CENTER, css_classes=["flat"])
            remove.update_property([Gtk.AccessibleProperty.LABEL], [f"Stop sharing {f['name']}"])
            remove.connect("clicked", lambda *_, f=f: self.admin_reply(["sharing", "remove", f["path"]],
                                                                       f"{f['name']} isn't shared now."))
            row.add_suffix(remove)
            self.share_list.add(row)
            self.share_rows.append(row)
        if not self.share_rows:
            row = Adw.ActionRow(title="No folders shared yet", subtitle="Add a folder from your home folder.")
            self.share_list.add(row)
            self.share_rows.append(row)
        self.share_updating = False

    @staticmethod
    def sharing_banner(state, nets, ready, running, home, shared):
        """The banner's title, its line, and whether it needs attention."""
        if not ready:
            return ("Shared folders can't start", f"{sharing.SMB_CONF} was changed on this computer. Put back the "
                    "EvenKeelOS version to use Shared folders.", True)
        if not state["on"]:
            return ("Sharing is off", "Turn it on below, and computers on your Home network can open the folders "
                    "you pick.", False)
        if not home:
            on = next((n for n in nets if n.device), None)
            place = {net.PUBLIC: "a Public place", net.WORK: "a Work network"}.get(on.zone or net.PUBLIC,
                                                                              "not a Home network") if on else ""
            return ("Sharing waits for a Home network", (f"{on.name} is {place}, so nothing is shared here. " if on
                    else "Not connected. ") + "Sharing starts by itself on a Home network.", False)
        if not shared:
            return ("Nothing is shared yet", "Add a folder and set the sharing password below.", False)
        if not running:
            return ("Sharing didn't start", "Turn sharing off and on again. If this stays, use Save problem details "
                    "in Get help.", True)
        wired = any(n.kind == "Wired" for n in home)
        return (f"Sharing on {', '.join(n.name for n in home)}",
                f"Other computers find this one as {socket.gethostname()}: in Files under Other Locations on Linux, "
                "in Finder under Network on a Mac, and under Network in File Explorer on Windows." +
                (" A wired network is set to Home, so this happens on any cable you plug in." if wired else ""),
                wired)

    def on_share_switch(self, row, _param):
        if self.share_updating:
            return
        if row.get_active() and GLib.get_user_name() not in self.share_state["passwords"]:
            self.share_updating = True
            row.set_active(False)
            self.share_updating = False
            self.ask_share_password(True)
            return
        self.admin_reply(["sharing", "on" if row.get_active() else "off"],
                         "Sharing is on." if row.get_active() else "Sharing is off.")

    def on_share_mode(self, drop, _param, folder):
        if self.share_updating:
            return
        mode = list(sharing.MODES)[drop.get_selected()]
        self.admin_reply(["sharing", "mode", folder["path"], mode], f"{folder['name']}: {sharing.MODES[mode]}.")

    def pick_share_folder(self):
        dialog = Gtk.FileDialog(title="Pick a folder to share", initial_folder=Gio.File.new_for_path(
            GLib.get_home_dir()))

        def picked(d, result):
            try:
                path = d.select_folder_finish(result).get_path()
            except GLib.Error:
                return
            if path:
                self.admin_reply(["sharing", "add", path, "ro"],
                                 f"{os.path.basename(path)} is shared, read only. Change it in the list.")
        dialog.select_folder(self, None, picked)

    def ask_share_password(self, then_on):
        user = GLib.get_user_name()
        d = Adw.AlertDialog(heading="Sharing password",
                            body=f"Other computers ask for your user name, {user}, and this password. Use at least "
                                 f"{sharing.MIN_PASSWORD} characters. Your login password doesn't change.")
        rows = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        first, again = Adw.PasswordEntryRow(title="Password"), Adw.PasswordEntryRow(title="Type it again")
        rows.append(first)
        rows.append(again)
        d.set_extra_child(rows)
        d.add_response("cancel", "Cancel")
        d.add_response("save", "Save")
        d.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        d.set_response_enabled("save", False)

        def typed(*_):
            pw = first.get_text()
            d.set_response_enabled("save", pw == again.get_text() and
                                   sharing.MIN_PASSWORD <= len(pw) <= 127 and sharing.clean(pw))
        first.connect("changed", typed)
        again.connect("changed", typed)

        def answered(_dialog, response):
            if response != "save":
                return
            after = (lambda: self.admin_reply(["sharing", "on"], "Sharing is on.")) if then_on else None
            self.admin_reply(["sharing", "password"], "Sharing password saved.", first.get_text(), after)
        d.connect("response", answered)
        d.present(self)

    def admin_reply(self, args, done_text, text=None, after=None, program=ADMIN, after_any=None):
        """A change as administrator (Shared folders, Boot options); the helper's own words when it refuses."""
        flags = Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE
        if text is not None:
            flags |= Gio.SubprocessFlags.STDIN_PIPE
        try:
            proc = Gio.Subprocess.new(program + args, flags)
        except GLib.Error:
            self.toast("Nothing changed.")
            if after_any:
                after_any()
            return

        def finished(p, result):
            try:
                _ok, out, _err = p.communicate_utf8_finish(result)
            except GLib.Error:
                out = ""
            rc = p.get_exit_status() if p.get_if_exited() else 1
            lines = (out or "").strip().splitlines()
            self.toast(done_text if rc == 0 else lines[-1] if rc in (1, 3, 4) and lines else "Nothing changed.")
            if rc == 0 and after:
                after()
            if after_any:
                after_any()
            self.refresh()
            GLib.timeout_add_seconds(4, self.refresh)        # Samba starts in the background: look again
        proc.communicate_utf8_async(text, None, finished)

    def boot_section(self, page):
        """Common fixes as switches, your own settings, and whether a restart is needed."""
        g = Adw.PreferencesGroup(title="Boot options", description="Settings the computer starts with. Each change "
                                 "makes a new version, and the one before stays as the fallback. Changes ask for an "
                                 "administrator password and start at the next restart.")
        self.boot_status = Adw.ActionRow(title="Checking…")
        self.boot_button = Gtk.Button(label="Restart now", valign=Gtk.Align.CENTER, visible=False)
        self.boot_button.connect("clicked", self.on_boot_button)
        self.boot_status.add_suffix(self.boot_button)
        g.add(self.boot_status)
        page.add(g)
        g = Adw.PreferencesGroup(title="Common fixes", description="Fixes many people use. Each one can cost a "
                                 "little battery, so turn one on only for a problem you have.")
        self.boot_switches = []
        for settings, title, about in bootopts.COMMON:
            row = Adw.SwitchRow(title=title, subtitle=f"{about}. {' '.join(settings)}", sensitive=False)
            row.connect("notify::active", self.on_boot_switch, settings)
            self.boot_switches.append((row, settings))
            g.add(row)
        page.add(g)
        self.boot_own = Adw.PreferencesGroup(title="Your own settings")
        self.boot_entry = Adw.EntryRow(title="Add a setting, like amdgpu.abmlevel=0", show_apply_button=True)
        self.boot_entry.connect("apply", self.on_boot_add)
        self.boot_own.add(self.boot_entry)
        page.add(self.boot_own)
        self.boot_rows = []
        self.boot_on = []
        self.boot_busy = False
        self.boot_updating = False

    def show_boot(self, upcoming, running):
        """upcoming: the settings the next start uses (None: unreadable); running: the ones this start used."""
        self.boot_updating = True
        readable = upcoming is not None
        upcoming = upcoming or []
        common = [s for s in upcoming if s in bootopts.COMMON_SETTINGS]
        self.boot_on = bootopts.merged(common, [s for s in bootopts.added() if s in upcoming])   # typed ones win
        for row, settings in self.boot_switches:
            row.set_sensitive(readable and not self.boot_busy)
            row.set_active(all(s in upcoming for s in settings))
        self.boot_entry.set_sensitive(readable and not self.boot_busy)
        for row in self.boot_rows:
            self.boot_own.remove(row)
        self.boot_rows = []
        for s in (s for s in self.boot_on if s not in bootopts.COMMON_SETTINGS):
            row = Adw.ActionRow(title=s, subtitle=bootopts.risk(s) or "Added by you")
            remove = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Take it out", valign=Gtk.Align.CENTER,
                                css_classes=["flat"], sensitive=not self.boot_busy)
            remove.update_property([Gtk.AccessibleProperty.LABEL], [f"Take out {s}"])
            remove.connect("clicked", lambda *_, s=s: self.boot_apply([x for x in self.boot_on if x != s],
                                                                      f"{s} is taken out from the next restart."))
            row.add_suffix(remove)
            self.boot_own.add(row)
            self.boot_rows.append(row)
        self.boot_button.set_visible(False)
        if not readable:
            self.boot_status.set_title("The boot options can't be read right now")
            self.boot_status.set_subtitle("Try again in a minute. If this stays, use Save problem details in Get help.")
        elif bootopts.same(upcoming, running):
            self.boot_status.set_title("In use" if self.boot_on else "No boot options added")
            self.boot_status.set_subtitle(" ".join(self.boot_on) or "The computer starts with the usual settings.")
        else:
            self.boot_status.set_title("Restart to use the changes")
            self.boot_status.set_subtitle("The next start uses: " + (" ".join(self.boot_on) or "no boot options"))
            self.boot_button.set_label("Restart now")
            self.boot_button.set_visible(True)
        self.boot_updating = False

    def on_boot_button(self, _button):
        spawn(["gnome-session-quit", "--reboot"])

    def on_boot_switch(self, row, _param, settings):
        if self.boot_updating or self.boot_busy:
            return
        if row.get_active():
            self.boot_apply(bootopts.merged(self.boot_on, list(settings)), f"{row.get_title()}: on from the next "
                            "restart.")
        else:
            self.boot_apply([s for s in self.boot_on if s not in settings],
                            f"{row.get_title()}: off from the next restart.")

    def on_boot_add(self, entry):
        if self.boot_busy:
            return
        settings = entry.get_text().split()
        problems = [bootopts.problem(s) for s in settings if bootopts.problem(s)]
        if not settings or problems:
            self.toast(problems[0] if problems else "Type a setting first.")
            return
        risky = [(s, bootopts.risk(s)) for s in settings if bootopts.risk(s)]
        new = bootopts.merged(self.boot_on, settings)
        done = f"{' '.join(settings)} is added from the next restart."
        if not risky:
            entry.set_text("")
            self.boot_apply(new, done)
            return
        d = Adw.AlertDialog(heading="This setting is risky",
                            body="\n\n".join(f"{s}: {why}" for s, why in risky) + "\n\nAdd it only if you know you "
                            "need it. If the computer then won't start, automatic rollback goes back to the version "
                            "before.")
        d.add_response("cancel", "Cancel")
        d.add_response("add", "Add anyway")
        d.set_response_appearance("add", Adw.ResponseAppearance.DESTRUCTIVE)
        d.set_default_response("cancel")
        d.set_close_response("cancel")

        def answered(_dialog, response):
            if response == "add":
                entry.set_text("")
                self.boot_apply(new, done)
        d.connect("response", answered)
        d.present(self)

    def boot_apply(self, settings, done_text):
        """One change at a time: the section waits until the helper has finished."""
        self.boot_busy = True
        for row, _ in self.boot_switches:
            row.set_sensitive(False)
        self.boot_entry.set_sensitive(False)
        for row in self.boot_rows:
            row.set_sensitive(False)
        self.admin_reply(["set", *settings], done_text, program=BOOT_OPTIONS, after_any=self.boot_done)

    def boot_done(self):
        self.boot_busy = False

    def terminal_list(self):
        g = Adw.PreferencesGroup(title="Prefer the terminal?", description="Every tool here has a command. The copy "
                                 "button puts it on the clipboard, to paste in a terminal.")
        seen = set()
        for tool in self.tools:
            if tool.command and tool.command not in seen:
                seen.add(tool.command)
                r = Adw.ActionRow(title=tool.command, subtitle=tool.title, css_classes=["property"])
                r.set_subtitle_selectable(True)
                copy = Gtk.Button(icon_name="edit-copy-symbolic", tooltip_text="Copy the command",
                                  valign=Gtk.Align.CENTER, css_classes=["flat"])
                copy.update_property([Gtk.AccessibleProperty.LABEL], [f"Copy {tool.command}"])
                copy.connect("clicked", self.copy_command, tool.command)
                r.add_suffix(copy)
                g.add(r)
        return g

    def copy_command(self, _button, command):
        self.get_clipboard().set(command)
        self.toast(f"Copied: {command}")

    # ------------------------------------------------------------ state

    def refresh(self, *_):
        threading.Thread(target=self.read_state, daemon=True).start()
        threading.Thread(target=self.read_network, daemon=True).start()
        threading.Thread(target=self.read_boot, daemon=True).start()
        return False

    def read_network(self):
        services = net.let_in(net.HOME)
        if services is not None:      # a switch is on only when the service runs and the firewall lets it in
            services = {s for s in self.net_switches if s in services and net.running(s)}
        nets = net.networks()
        GLib.idle_add(self.show_network, nets, net.default_zone(), services)
        GLib.idle_add(self.show_sharing, sharing.load(), nets, sharing.set_up(), sharing.running())

    def read_boot(self):
        GLib.idle_add(self.show_boot, bootopts.next_start(), bootopts.running())

    def read_state(self):
        on = self.t.updates_on()
        state = {"on": on, "paused": on and self.t.paused_until(), "unlock": self.t.DISK_UNLOCK_ON.exists(),
                 "disk": shutil.disk_usage("/var/home" if os.path.isdir("/var/home") else str(Path.home())),
                 "chrome": bool(zoom.chrome_command()), "usual": zoom_usual_browser()}
        ds = self.t.deployments() or []
        state["staged"] = next((d for d in ds if d.get("staged")), None)
        booted = next((d for d in ds if d.get("booted")), None)
        state["since"] = self.t.when(booted) if booted else ""
        state["certs"] = len(self.t.cert_alerts() or [])
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
        elif s["certs"]:
            n = s["certs"]
            title, sub, button, warn = ("A certificate needs attention" if n == 1 else
                                        f"{n} certificates need attention",
                                        "A security certificate expired, expires within 30 days, or was removed.",
                                        "Details", True)
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
        elif tool.run in ("network", "sharing"):
            self.show(tool.run)
        elif tool.run == "bootopts":
            self.show("disk")
        elif tool.run == "guide":
            self.open_guide()
        elif isinstance(tool.run, str) and tool.run.startswith("guide-"):
            self.go(tool.run)
        elif tool.run == "codecs-remove":
            self.remove_codecs()
        elif tool.run[0] in OURS:
            self.run_tool(tool.title, tool.run)
        elif not spawn(tool.run):
            self.toast(f"{tool.title} didn't start.")

    def busy(self):
        """The tool that is open: the one started here, or one it started that is still asking something."""
        if self.current:
            return self.current
        return (self.dialogs.open[-1].req.get("title") or "A tool") if self.dialogs.open else None

    def run_tool(self, title, argv, after=None):
        """Run one of our tools with its windows on the tool page; after(exit code) once it has ended."""
        busy = self.busy()
        if busy:
            if argv != self.current_argv:
                self.toast(f"{busy} is still open. Finish it first.")
            self.show_tool()
            return
        if not spawn(argv, lambda rc: self.tool_done(rc, after), self.dialogs.path):
            self.toast(f"{title} didn't start.")
            return
        self.current, self.current_argv = title, argv
        self.show_tool()

    def tool_done(self, rc, after):
        self.current = self.current_argv = None
        self.on_dialogs()
        if after:
            after(rc)
        self.refresh()

    def show_tool(self):
        if self.stack.get_visible_child_name() != "tool":
            self.before = self.stack.get_visible_child_name()
        self.dialogs.show(self.busy())
        self.stack.set_visible_child_name("tool")
        self.content_title.set_title(self.busy() or "System Tools")
        self.back.set_visible(True)
        self.waiting.set_revealed(False)
        self.split.set_show_content(True)

    def on_dialogs(self):
        """A tool asked something: show it. Nothing left open and no tool running: back to the page."""
        if self.dialogs.open:
            self.show_tool()
        elif not self.current and self.stack.get_visible_child_name() == "tool":
            self.go_back()
        elif self.stack.get_visible_child_name() != "tool":
            self.show_waiting()

    def show_waiting(self):
        """On another page while a tool is open: a bar at the top says so, with a button back to it."""
        busy = self.busy()
        if busy:
            self.waiting.set_title(f"{busy} is waiting for an answer." if self.dialogs.open else
                                   f"{busy} is still working.")
        self.waiting.set_revealed(bool(busy))

    def go_back(self):
        """Back one page. From the tool page, a tool that is open stays open, behind the bar at the top."""
        name = self.before if self.stack.get_visible_child_name() == "tool" else \
            self.trail.pop() if self.trail else self.before
        self.stack.set_visible_child_name(name)
        self.content_title.set_title(self.page_title(name))
        self.back.set_visible(bool(self.trail))
        self.show_waiting()

    def on_close(self, _window):
        busy = self.busy()
        if busy:
            self.toast(f"{busy} is still open. Close System Tools once it's done.")
            self.show_tool()
            return True
        self.dialogs.close()
        return False

    def remove_codecs(self):
        d = Adw.AlertDialog(heading="Remove the media codecs?",
                            body="Video and audio that need them stop playing. Needs your password and a restart.")
        d.add_response("cancel", "Cancel")
        d.add_response("remove", "Remove")
        d.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)

        def answered(dialog, response):
            if response == "remove":
                self.run_tool("Remove media codecs", ["/usr/bin/evenkeel-os-codecs", "remove"],
                              lambda rc: self.toast("The codecs are removed. Restart to finish." if rc == 0 else
                                                    "The codecs weren't removed."))
        d.connect("response", answered)
        d.present(self)

    def on_banner_button(self, button):
        label = button.get_label()
        if label == "Restart now":
            spawn(["gnome-session-quit", "--reboot"])
        elif label in ("Resume now", "Turn on"):
            self.run_tool("Automatic updates", [TOOLS, "updates"])
        elif label == "Details":
            self.run_tool("Certificate alerts", [TOOLS, "certificates"])
        else:
            self.activate_tool(next(t for t in self.tools if t.title == "System Update"))

    def on_page(self, box, row):
        if row is None:
            return
        self.search.set_text("")
        self.trail.clear()
        self.back.set_visible(False)
        self.stack.set_visible_child_name(row.key)
        self.show_waiting()
        self.content_title.set_title(dict((k, n) for k, n, _ in PAGES)[row.key])
        self.split.set_show_content(True)

    def on_search(self, entry):
        words = entry.get_text().lower().split()
        if not words:
            row = self.sidebar.get_selected_row()
            self.back.set_visible(False)
            self.stack.set_visible_child_name(row.key if row else "overview")
            self.show_waiting()
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
        self.back.set_visible(False)
        self.stack.set_visible_child_name("search")
        self.show_waiting()
        self.content_title.set_title("Search")
        if not self.split.get_collapsed():      # narrow window: the results show on Enter, keeping the box in view
            self.split.set_show_content(True)

    def on_drop(self, _target, value, _x, _y, box):
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
                self.run_tool("Install a package file", [PACKAGES, "install", f])
            elif low.endswith(WINDOWS_TYPES):
                self.run_tool("Windows programs", [PACKAGES, "windows", f])
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
            self.run_tool("Windows programs", [PACKAGES, "windows", path])
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

    def show(self, page, at_login=False):
        if page == "guide":
            self.open_guide(at_login)
            return
        keys = [k for k, _, _ in PAGES]
        self.sidebar.select_row(self.sidebar.get_row_at_index(keys.index(page) if page in keys else 0))
        self.present()
        self.sidebar.get_selected_row().grab_focus()      # not the search box, so its hint stays readable


def run(tools_module, page="overview", first_login=False):
    """Open the window (or bring it to the front, on the page asked for). first_login: the guide at login, with
    its "Don't show this again" box."""
    app = Adw.Application(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS)

    def command_line(a, cl):
        args = cl.get_arguments()[1:]
        want = next((x.split("=", 1)[1] for x in args if x.startswith("--page=")), page)
        at_login = "--first-login" in args
        win = a.get_active_window()
        if win is None:
            Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider,
                                                      Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            win = Window(a, tools_module)
        win.show(want, at_login)
        return 0
    app.connect("command-line", command_line)
    return app.run([TOOLS, f"--page={page}"] + (["--first-login"] if first_login else []))
