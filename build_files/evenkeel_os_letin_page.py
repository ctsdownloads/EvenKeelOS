"""Network safety in Wheelhouse: the apps and ports each place lets in, with Let an app in and Open a port."""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402
import evenkeel_os_letin as letin  # noqa: E402
import evenkeel_os_network as net  # noqa: E402
from evenkeel_os_ui import _, N_, icon_button  # noqa: E402

KEYS = {net.HOME: "home", net.WORK: "work", net.PUBLIC: "public"}
# Translators: Home, Work and Public place are the names of kinds of network place; one whole sentence for each.
CLOSED_AGAIN = {net.HOME: N_("{name} is closed again on Home."), net.WORK: N_("{name} is closed again on Work."),
                net.PUBLIC: N_("{name} is closed again on a Public place.")}
NOTHING_EXTRA = {net.HOME: N_("Nothing extra on Home"), net.WORK: N_("Nothing extra on Work"),
                 net.PUBLIC: N_("Nothing extra on a Public place")}
LET_APP_IN = {net.HOME: N_("Let an app in on Home"), net.WORK: N_("Let an app in on Work"),
              net.PUBLIC: N_("Let an app in on a Public place")}
OPEN_PORT = {net.HOME: N_("Open a port on Home"), net.WORK: N_("Open a port on Work"),
             net.PUBLIC: N_("Open a port on a Public place")}
LET_IN_DONE = {net.HOME: N_("{name} is let in on Home."), net.WORK: N_("{name} is let in on Work."),
               net.PUBLIC: N_("{name} is let in on a Public place.")}
PROTOCOLS = (("TCP", ("tcp",)), ("UDP", ("udp",)), (N_("Both"), ("tcp", "udp")))
SOURCES = {"checked": N_("Checked against its own docs"), "firewalld": N_("Fedora's firewall list"),
           "IANA": N_("IANA port list")}


class LetIn:
    """The section; window is Wheelhouse's window (admin_reply, toast, and the parent of the dialogs)."""

    def __init__(self, window):
        self.window = window
        self.state, self.rows, self.followed, self.everything = {}, [], None, None
        self.group = Adw.PreferencesGroup(title=_("Apps and ports let in"),
                                          description=_("On top of what the place itself lets in. Each change asks "
                                                        "for your password."))
        buttons = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        for text, action in ((N_("Let an app in"), self.pick_app), (N_("Open a port"), self.ask_port)):
            b = Gtk.Button(label=_(text))
            b.connect("clicked", lambda *_args, a=action: a())
            buttons.append(b)
        self.group.set_header_suffix(buttons)
        self.place = Adw.ComboRow(title=_("Place"))
        self.place.set_model(Gtk.StringList.new([_(v) for v in net.PLACES.values()]))
        self.place.connect("notify::selected", lambda *_args: self.show_rows())
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
            ports = ", ".join(e["ports"]) or _("Fedora's {service} app").format(service=e["service"])
            row = Adw.ActionRow(title=e["label"], subtitle=ports, use_markup=False)
            row.add_suffix(icon_button(
                "user-trash-symbolic", _("Close it again"), _("Close {name} again").format(name=e["label"]),
                lambda e=e: self.window.admin_reply(["let-in", KEYS[zone], "remove", e["id"]],
                                                    _(CLOSED_AGAIN[zone]).format(name=e["label"]))))
            self.group.add(row)
            self.rows.append(row)
        if not self.rows:
            row = Adw.ActionRow(title=_(NOTHING_EXTRA[zone]),
                                subtitle=_(net.LETS_IN[zone]) if zone in net.LETS_IN else "")
            self.group.add(row)
            self.rows.append(row)

    def pick_app(self):
        """A searchable list: checked apps and Fedora's list at first, IANA's port list as you type."""
        if self.everything is None:
            self.everything = letin.apps()
        zone = self.zone()
        d = Adw.Dialog(title=_(LET_APP_IN[zone]), content_width=480, content_height=560)
        search = Gtk.SearchEntry(placeholder_text=_("App, game or port number"), margin_start=12, margin_end=12,
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

        def fill(*_args):
            shown.remove_all()
            text = search.get_text().strip()
            found = letin.find(text, self.everything) if text else \
                [a for a in self.everything if a["source"] != "IANA"]
            for a in found:
                where = ", ".join(a["ports"]) or _("No ports of its own")
                row = Adw.ActionRow(title=a["name"], activatable=True, title_lines=2, subtitle_lines=2,
                                    subtitle=_("{ports}. {source}").format(ports=where,
                                                                           source=_(SOURCES[a["source"]])),
                                    use_markup=False)
                row.connect("activated", lambda *_args, a=a: (d.close(), self.choose(zone, a)))
                shown.append(row)
            if not found:
                shown.append(Adw.ActionRow(title=_("Nothing matches"), subtitle=_("Use Open a port with its number.")))
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
        d = Adw.AlertDialog(heading=_(OPEN_PORT[zone]),
                            body=_("Use the number the app's own instructions give."))
        rows = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        number = Adw.EntryRow(title=_("Port, like 8080, or a range, like 2456-2458"))
        kind = Adw.ComboRow(title=_("Protocol"), subtitle=_("The app's instructions say TCP, UDP or both"))
        kind.set_model(Gtk.StringList.new([_(p) for p, _protocols in PROTOCOLS]))
        name = Adw.EntryRow(title=_("Name, so you know what it's for"))
        for r in (number, kind, name):
            rows.append(r)
        d.set_extra_child(rows)
        d.add_response("cancel", _("Cancel"))
        d.add_response("open", _("Open"))
        d.set_response_appearance("open", Adw.ResponseAppearance.SUGGESTED)
        d.set_response_enabled("open", False)

        def specs():
            return [f"{number.get_text().strip()}/{p}" for p in PROTOCOLS[kind.get_selected()][1]]

        def typed(*_args):
            d.set_response_enabled("open", letin.ports(specs()) is not None and bool(letin.label(name.get_text())))
        for w in (number, name):
            w.connect("changed", typed)
        kind.connect("notify::selected", typed)

        def answered(_dialog, response):
            if response == "open":
                label = letin.label(name.get_text())
                self.confirm(zone, label, ["let-in", KEYS[zone], "ports", label, *letin.ports(specs())])
        d.connect("response", answered)
        d.present(self.window)

    def confirm(self, zone, name, args):
        """On a Public place, strangers come first: say so before letting anything in."""
        if zone != net.PUBLIC:
            self.window.admin_reply(args, _(LET_IN_DONE[zone]).format(name=name))
            return
        d = Adw.AlertDialog(heading=_("Let {name} in on a Public place?").format(name=name), heading_use_markup=False,
                            body=_("Strangers on the same network, in a café, hotel or airport, could reach it too. "
                                   "Only do this if you need it here, and close it again when you're done."))
        d.add_response("cancel", _("Cancel"))
        d.add_response("open", _("Let it in"))
        d.set_response_appearance("open", Adw.ResponseAppearance.DESTRUCTIVE)
        d.set_default_response("cancel")
        d.connect("response", lambda _d, r: r == "open" and self.window.admin_reply(
            args, _(LET_IN_DONE[zone]).format(name=name)))
        d.present(self.window)
