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
import evenkeel_os_network as net  # noqa: E402
from evenkeel_os_dialogs import Dialogs  # noqa: E402
from evenkeel_os_packages import zoom  # noqa: E402

APP_ID = "io.github.ctsdownloads.evenkeel-os.Tools"
TOOLS = "/usr/bin/evenkeel-os-tools"
ADMIN = ["pkexec", "/usr/libexec/evenkeel-os-tools-admin"]
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
        for tool in self.tools:
            if tool.page != key or tool.run in ("layout", "network"):     # these pages are the tool; search finds it
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

    def read_network(self):
        services = net.let_in(net.HOME)
        if services is not None:      # a switch is on only when the service runs and the firewall lets it in
            services = {s for s in self.net_switches if s in services and net.running(s)}
        GLib.idle_add(self.show_network, net.networks(), net.default_zone(), services)

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
        elif tool.run == "network":
            self.show("network")
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
        """Leave the tool page; a tool that is open stays open, behind the bar at the top."""
        self.back.set_visible(False)
        self.stack.set_visible_child_name(self.before)
        self.content_title.set_title(dict((k, n) for k, n, _ in PAGES).get(self.before, "Search"))
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
