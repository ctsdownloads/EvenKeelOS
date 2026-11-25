"""Network safety in Wheelhouse: the apps and ports each place lets in, with Let an app in and Open a port."""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402
import evenkeel_os_letin as letin  # noqa: E402
import evenkeel_os_network as net  # noqa: E402

KEYS = {net.HOME: "home", net.WORK: "work", net.PUBLIC: "public"}
ON_A = {net.HOME: "on Home", net.WORK: "on Work", net.PUBLIC: "on a Public place"}
PROTOCOLS = (("TCP", ("tcp",)), ("UDP", ("udp",)), ("Both", ("tcp", "udp")))
SOURCES = {"checked": "Checked against its own docs", "firewalld": "Fedora's firewall list", "IANA": "IANA port list"}


class LetIn:
    """The section; window is Wheelhouse's window (admin_reply, toast, and the parent of the dialogs)."""

    def __init__(self, window):
        self.window = window
        self.state, self.rows, self.followed, self.everything = {}, [], None, None
        self.group = Adw.PreferencesGroup(title="Apps and ports let in",
                                          description="On top of what the place itself lets in. Each change asks "
                                                      "for your password.")
        buttons = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        for text, action in (("Let an app in", self.pick_app), ("Open a port", self.ask_port)):
            b = Gtk.Button(label=text)
            b.connect("clicked", lambda *_, a=action: a())
            buttons.append(b)
        self.group.set_header_suffix(buttons)
        self.place = Adw.ComboRow(title="Place")
        self.place.set_model(Gtk.StringList.new(list(net.PLACES.values())))
        self.place.connect("notify::selected", lambda *_: self.show_rows())
        self.group.add(self.place)

    def zone(self):
        return list(net.PLACES)[self.place.get_selected()]

    def show(self, state, connected_zone):
        """New list; the place follows the network you're on whenever that changes."""
        self.state = state
        if connected_zone in net.PLACES and connected_zone != self.followed:
            self.followed = connected_zone
            self.place.set_selected(list(net.PLACES).index(connected_zone))
        self.show_rows()

    def show_rows(self):
        for row in self.rows:
            self.group.remove(row)
        self.rows = []
        zone = self.zone()
        for e in self.state.get(zone, []):
            row = Adw.ActionRow(title=e["label"], subtitle=", ".join(e["ports"]) or f"Fedora's {e['service']} app",
                                use_markup=False)
            remove = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Close it again",
                                valign=Gtk.Align.CENTER, css_classes=["flat"])
            remove.update_property([Gtk.AccessibleProperty.LABEL], [f"Close {e['label']} again"])
            remove.connect("clicked", lambda *_, e=e: self.window.admin_reply(
                ["let-in", KEYS[zone], "remove", e["id"]], f"{e['label']} is closed again {ON_A[zone]}."))
            row.add_suffix(remove)
            self.group.add(row)
            self.rows.append(row)
        if not self.rows:
            row = Adw.ActionRow(title=f"Nothing extra {ON_A[zone]}",
                                subtitle=net.LETS_IN.get(zone, ""))
            self.group.add(row)
            self.rows.append(row)

    def pick_app(self):
        """A searchable list: checked apps and Fedora's list at first, IANA's port list as you type."""
        if self.everything is None:
            self.everything = letin.apps()
        zone = self.zone()
        d = Adw.Dialog(title=f"Let an app in {ON_A[zone]}", content_width=480, content_height=560)
        search = Gtk.SearchEntry(placeholder_text="App, game or port number", margin_start=12, margin_end=12,
                                 margin_top=6, margin_bottom=6)
        shown = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE, margin_start=12,
                            margin_end=12, margin_bottom=12)
        scroll = Gtk.ScrolledWindow(vexpand=True, child=shown)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(search)
        box.append(scroll)
        view = Adw.ToolbarView(content=box)
        view.add_top_bar(Adw.HeaderBar())
        d.set_child(view)

        def fill(*_):
            shown.remove_all()
            text = search.get_text().strip()
            found = letin.find(text, self.everything) if text else \
                [a for a in self.everything if a["source"] != "IANA"]
            for a in found:
                where = ", ".join(a["ports"]) or "No ports of its own"
                row = Adw.ActionRow(title=a["name"], activatable=True, title_lines=2, subtitle_lines=2,
                                    subtitle=f"{where}. {SOURCES[a['source']]}", use_markup=False)
                row.connect("activated", lambda *_, a=a: (d.close(), self.choose(zone, a)))
                shown.append(row)
            if not found:
                shown.append(Adw.ActionRow(title="Nothing matches", subtitle="Use Open a port with its number."))
        search.connect("search-changed", fill)
        fill()
        d.present(self.window)

    def choose(self, zone, app):
        if app["service"]:
            args = ["let-in", KEYS[zone], "app", app["service"]]
        else:
            args = ["let-in", KEYS[zone], "ports", app["name"], *app["ports"]]
        self.confirm(zone, app["name"], args)

    def ask_port(self):
        zone = self.zone()
        d = Adw.AlertDialog(heading=f"Open a port {ON_A[zone]}",
                            body="Use the number the app's own instructions give.")
        rows = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        number = Adw.EntryRow(title="Port, like 8080, or a range, like 2456-2458")
        kind = Adw.ComboRow(title="Protocol", subtitle="The app's instructions say TCP, UDP or both")
        kind.set_model(Gtk.StringList.new([p for p, _ in PROTOCOLS]))
        name = Adw.EntryRow(title="Name, so you know what it's for")
        for r in (number, kind, name):
            rows.append(r)
        d.set_extra_child(rows)
        d.add_response("cancel", "Cancel")
        d.add_response("open", "Open")
        d.set_response_appearance("open", Adw.ResponseAppearance.SUGGESTED)
        d.set_response_enabled("open", False)

        def specs():
            return [f"{number.get_text().strip()}/{p}" for p in PROTOCOLS[kind.get_selected()][1]]

        def typed(*_):
            d.set_response_enabled("open", letin.ports(specs()) is not None and bool(letin.label(name.get_text())))
        for w in (number, name):
            w.connect("changed", typed)
        kind.connect("notify::selected", typed)

        def answered(_dialog, response):
            if response == "open":
                self.confirm(zone, letin.label(name.get_text()),
                             ["let-in", KEYS[zone], "ports", letin.label(name.get_text()), *letin.ports(specs())])
        d.connect("response", answered)
        d.present(self.window)

    def confirm(self, zone, name, args):
        """On a Public place, strangers come first: say so before letting anything in."""
        if zone != net.PUBLIC:
            self.window.admin_reply(args, f"{name} is let in {ON_A[zone]}.")
            return
        d = Adw.AlertDialog(heading=f"Let {name} in on a Public place?", heading_use_markup=False,
                            body="Strangers on the same network, in a café, hotel or airport, could reach it too. "
                                 "Only do this if you need it here, and close it again when you're done.")
        d.add_response("cancel", "Cancel")
        d.add_response("open", "Let it in")
        d.set_response_appearance("open", Adw.ResponseAppearance.DESTRUCTIVE)
        d.set_default_response("cancel")
        d.connect("response", lambda _d, r: r == "open" and self.window.admin_reply(args, f"{name} is let in "
                                                                                          f"{ON_A[zone]}."))
        d.present(self.window)
