"""Installer steps for language, keyboards, network, time zone, date and clock."""
import calendar
import re
import sys

from gi.repository import Adw, Gio, GLib, Gtk

import data
import i18n
import screens
from i18n import _, N_

sys.path.insert(0, "/usr/lib/evenkeel-os")
import evenkeel_os_network as net  # noqa: E402

MONTHS = [N_("January"), N_("February"), N_("March"), N_("April"), N_("May"), N_("June"), N_("July"),
          N_("August"), N_("September"), N_("October"), N_("November"), N_("December")]


def time_text(t):
    """A date and time as "5 March 2027, 14:30", the month in the installer's language."""
    return _("{day} {month} {year}, {time}").format(day=t.day, month=_(MONTHS[t.month - 1]), year=t.year,
                                                    time=t.strftime("%H:%M"))


class LanguageScreen(screens.ListScreen):
    title = N_("Language")
    step = N_("Language")
    first_stage = "language"

    @property
    def back(self):
        return self.stage == "locale"

    def build(self):
        super().build()
        self.langs = data.languages()
        self.lang = "en"
        self.stage = "language"

    @property
    def intro(self):
        if self.stage == "language":
            return _("Which language should EvenKeelOS use?")
        return _("Which one? Back goes to the list of languages.")

    def items(self):
        if self.stage == "language":
            self.langs.sort(key=lambda x: i18n.language(x[0]).lower())
            rows = [(i18n.language(lang), native, lang == self.lang) for lang, _eng, native in self.langs]
        else:
            rows = [(i18n.language(loc), native, loc == self.c.locale) for loc, _eng, native in data.locales(self.lang)]
        return [(name, native if native != name else "", chosen) for name, native, chosen in rows]

    def pick(self, i):
        if self.stage == "language":
            self.lang = self.langs[i][0]
            options = data.locales(self.lang)
            if len(options) == 1:
                self.c.locale = options[0][0]
            else:
                self.stage = "locale"
                if not self.c.locale.startswith(self.lang + "_"):
                    self.c.locale = options[0][0]
                i18n.use(self.c.locale)
                self.choose(to_chosen=True)
                return
        else:
            self.c.locale = data.locales(self.lang)[i][0]
        i18n.use(self.c.locale)
        self.choose()

    def status(self):
        return _("Chosen: {name}.").format(name=language_name(self.c.locale))


def language_name(loc):
    return i18n.language(loc)


# ---------------------------------------------------------------------------------------------------- 2 Keyboard

class KeyboardScreen(screens.ListScreen):
    title = N_("Keyboard layout")
    step = N_("Keyboard")

    @property
    def intro(self):
        return _("Which keyboard layouts do you use? Click one to add it, or click it again to take it off. "
                 "The first one is used unless you switch.")

    def build(self):
        super().build()
        self.all = data.keyboards()

    def enter(self):
        self.suggested = [k for k in data.suggested_keyboards(self.c.locale) if k in self.all]
        if not self.c.layouts_chosen_by_hand:
            self.c.layouts = self.suggested[:1]
        rest = sorted((k for k in self.all if k not in self.suggested), key=lambda k: self.name(k).lower())
        self.order = self.suggested + rest
        super().enter()

    def items(self):
        return [(self.name(k), _("Suggested") if k in self.suggested else "", k in self.c.layouts)
                for k in self.order]

    def name(self, k):
        return i18n.keyboard(self.all[k])

    def pick(self, i):
        k = self.order[i]
        if k in self.c.layouts:
            if len(self.c.layouts) > 1:
                self.c.layouts.remove(k)
        else:
            self.c.layouts.append(k)
        self.c.layouts_chosen_by_hand = True
        self.choose()

    def status(self):
        return _("Chosen: {names}.").format(names=", ".join(self.name(k) for k in self.c.layouts))


# ------------------------------------------------------------------------------------- 3 Keyboard at start

class BootKeyboardScreen(screens.ListScreen):
    """Layouts the text console has, for typing the disk password."""
    title = N_("Keyboard for the disk password")
    step = N_("Keyboard at start")

    @property
    def intro(self):
        return _("If the disk is encrypted, its password is typed when the computer starts, before EvenKeelOS "
                 "loads. Which keyboard layout is used then?")

    def build(self):
        super().build()
        self.all = data.keyboards()
        self.offered = [k for k in self.all if data.has_console_keymap(k)]

    def name(self, k):
        return i18n.keyboard(self.all[k])

    def same_offered(self):
        return self.c.layouts[0] in self.offered

    def enter(self):
        if self.c.boot_layout is None and not self.same_offered():
            self.c.boot_layout = "us"
        self.order = sorted(self.offered, key=lambda k: self.name(k).lower())
        super().enter()

    def items(self):
        first = self.name(self.c.layouts[0])
        same = [(_("Same as above"), first, self.c.boot_layout is None)] if self.same_offered() else []
        return same + [(self.name(k), "", self.c.boot_layout == k) for k in self.order]

    def pick(self, i):
        if self.same_offered():
            self.c.boot_layout = None if i == 0 else self.order[i - 1]
        else:
            self.c.boot_layout = self.order[i]
        self.choose()

    def status(self):
        k = self.c.boot_layout or self.c.layouts[0]
        first = self.name(self.c.layouts[0])
        missing = "" if self.same_offered() else _("{layout} can't be used before EvenKeelOS loads.").format(
            layout=first) + " "
        return missing + _("Chosen: {name}.").format(name=self.name(k))


# ---------------------------------------------------------------------------------------------------- 4 Network

PLACE_CHOICES = [(net.HOME, N_("Your own home network")),
                 (net.WORK, N_("An office. Nothing gets in, and your folders aren't shared.")),
                 (net.PUBLIC, N_("A café, hotel, airport, or anywhere else. Nothing gets in."))]


class NetworkScreen(screens.ListScreen):
    title = N_("Network")
    step = N_("Network")

    def build(self):
        super().build()
        self.password = Adw.PasswordEntryRow()
        self.password.connect("entry-activated", lambda *_: self.connect_wifi())
        self.password_box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"],
                                        visible=False)
        self.password_box.append(self.password)
        self.body.append(self.password_box)
        self.wired, self.wifi, self.chosen, self.busy = False, [], None, ""
        self.placing = None      # the password Wi-Fi just joined: Home, Work or a Public place?

    def relabel(self):
        self.password.set_title(_("Wi-Fi password"))

    @property
    def intro(self):
        if self.placing:
            return _("Where is {network}? This sets what other devices on it can reach once EvenKeelOS "
                     "is installed. Pick Public place anywhere you're not sure.").format(network=self.placing.name)
        if self.chosen and self.chosen["secured"]:
            return _("Type the password for {network}, then click Connect. Back goes to the list.").format(
                network=self.chosen["ssid"])
        return _("A network is only needed for automatic time and time zone. To use Wi-Fi, click a network. "
                 "Or click Next to go on without it.")

    def enter(self):
        self.wired, self.wifi = data.network()
        super().enter()

    def items(self):
        if self.placing:
            return [(_(net.PLACES[z]), _(about), z == net.PUBLIC) for z, about in PLACE_CHOICES]
        if self.chosen and self.chosen["secured"]:
            return []
        return [(w["ssid"], (_("Signal {percent}%, password needed") if w["secured"] else
                             _("Signal {percent}%")).format(percent=w["signal"]), False) for w in self.wifi]

    def refresh(self, to_chosen=True):
        super().refresh(to_chosen)
        asking = bool(self.chosen and self.chosen["secured"])
        self.list.set_visible(not asking)
        self.password_box.set_visible(asking)

    def pick(self, i):
        if self.placing:
            zone, network = PLACE_CHOICES[i][0], self.placing
            saved = net.set_place(network, zone)
            place = _(net.PLACES[zone])
            self.busy = (_("{network} is saved as {place}.").format(network=network.name, place=place) if saved else
                         _("{network} couldn't be saved as {place}. EvenKeelOS asks again at the "
                           "first login.").format(network=network.name, place=place))
            self.placing = None
            self.choose()
            return
        self.chosen = self.wifi[i]
        if self.chosen["secured"]:
            self.password.set_text("")
            self.choose()
            self.password.grab_focus()
        else:
            self.connect_wifi()

    def actions(self):
        if self.placing:
            return []
        if self.chosen and self.chosen["secured"]:
            return [(_("Connect"), self.connect_wifi)]
        return [(_("Refresh"), self.enter)]

    def connect_wifi(self):
        ssid = self.chosen["ssid"]
        args = ["nmcli", "device", "wifi", "connect", ssid]
        if self.chosen["secured"]:
            args += ["password", self.password.get_text()]
        self.busy = _("Connecting to {network}...").format(network=ssid)
        self.choose()
        proc = Gio.Subprocess.new(args, Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE)
        proc.wait_check_async(None, self._connected, ssid)

    def _connected(self, proc, result, ssid):
        try:
            ok = proc.wait_check_finish(result)
        except GLib.Error:
            ok = False
        self.busy = (_("Connected to {network}.") if ok else
                     _("Could not connect to {network}. Check the password.")).format(network=ssid)
        if ok:
            if self.chosen["secured"]:
                joined = [n for n in net.networks() if n.needs_asking]
                self.placing = next((n for n in joined if n.name == ssid), joined[0] if joined else None)
            self.chosen = None
        self.wired, self.wifi = data.network()
        self.choose()

    def ready(self):
        return not self.placing      # pick a place, or Back to leave it for the first login

    def go_back(self):
        if self.placing:       # not answered here: the installed system asks at the first login
            self.placing = None
            self.choose()
            return True
        if self.chosen:
            self.chosen, self.busy = None, ""
            self.choose()
            return True
        return False

    def status(self):
        if self.busy:
            return self.busy
        if self.wired:
            return _("Wired network: connected.")
        return _("Wired network: not connected.") + ("" if self.wifi else " " + _("No Wi-Fi networks found."))


# ---------------------------------------------------------------------------------------------------- 5 Time zone

class TimeZoneScreen(screens.ListScreen):
    title = N_("Time zone")
    step = N_("Time zone")

    def build(self):
        super().build()
        self.zones = data.timezones()
        self.regions = list(self.zones)
        self.region = None

    @property
    def intro(self):
        if self.region:
            return _("Which city in {region} has your time? Back goes to the regions.").format(
                region=i18n.place(self.region))
        return _("Set the time zone automatically, or pick a region, then a city.")

    def items(self):
        if self.region:
            return [(self.city(tz), "", tz == self.c.timezone) for tz in self.cities()]
        self.regions.sort(key=lambda r: i18n.place(r).lower())
        return ([(_("Automatic"), _("From the computer's location (recommended)"), self.c.timezone is None)] +
                [(i18n.place(r), "", bool(self.c.timezone) and self.c.timezone.startswith(r + "/"))
                 for r in self.regions])

    @staticmethod
    def city(tz):
        """ "America/Argentina/Buenos_Aires" as "Argentina, Buenos Aires", in the installer's language."""
        return ", ".join(i18n.place(tz).split("/")[1:]) or tz

    def cities(self):
        return sorted((tz for tz, _city in self.zones[self.region]), key=self.city)

    def pick(self, i):
        if self.region:
            self.c.timezone = self.cities()[i]
        elif i == 0:
            self.c.timezone = None
        else:
            self.region = self.regions[i - 1]
            self.choose(to_chosen=True)
            return
        self.choose()

    def go_back(self):
        if self.region:
            self.region = None
            self.choose(to_chosen=True)
            return True
        return False

    def status(self):
        return _("Chosen: {name}.").format(name=i18n.place(self.c.timezone) if self.c.timezone else
                                           _("Automatic"))


# ---------------------------------------------------------------------------------------------------- 6 Date and time

class DateTimeScreen(screens.ListScreen):
    title = N_("Date and time")
    step = N_("Date and time")
    first_stage = "main"
    FIELDS = ["Year", "Month", "Day", "Hour", "Minute"]         # also the stage names; shown through FIELD_NAMES
    FIELD_NAMES = {"Year": N_("Year"), "Month": N_("Month"), "Day": N_("Day"), "Hour": N_("Hour"),
                   "Minute": N_("Minute")}
    FIELD_INTROS = {"Year": N_("Pick the year. Back keeps it as it is."),
                    "Month": N_("Pick the month. Back keeps it as it is."),
                    "Day": N_("Pick the day. Back keeps it as it is."),
                    "Hour": N_("Pick the hour. Back keeps it as it is."),
                    "Minute": N_("Pick the minute. Back keeps it as it is.")}

    def build(self):
        self.server = Adw.EntryRow()
        self.server.connect("entry-activated", lambda *_: self.add_server())
        self.server_box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"],
                                      visible=False)
        self.server_box.append(self.server)
        self.body.append(self.server_box)
        super().build()
        self.stage = "main"                 # main, a field name, or servers

    def relabel(self):
        self.server.set_title(_("Time server name"))

    @property
    def intro(self):
        if self.stage == "servers":
            return _("Time servers to use instead of Fedora's. Type a name and click Add. Click a server to take it "
                     "off. Click Back when done.")
        if self.stage in self.FIELDS:
            return _(self.FIELD_INTROS[self.stage])
        return _("Keep the clock right automatically, or set the date and time yourself.")

    def values(self):
        t = self.c.manual_time
        if self.stage == "Year":
            return [str(y) for y in range(t.year - 1, t.year + 5)]
        if self.stage == "Month":
            return MONTHS
        if self.stage == "Day":
            return [str(d) for d in range(1, calendar.monthrange(t.year, t.month)[1] + 1)]
        if self.stage == "Hour":
            return [f"{h:02d}" for h in range(24)]
        return [f"{m:02d}" for m in range(60)]

    def items(self):
        t = self.c.manual_time
        if self.stage == "servers":
            return [(s, "", False) for s in self.c.time_servers]
        if self.stage in self.FIELDS:
            now = {"Year": str(t.year), "Month": MONTHS[t.month - 1], "Day": str(t.day), "Hour": f"{t.hour:02d}",
                   "Minute": f"{t.minute:02d}"}[self.stage]
            return [(_(v) if self.stage == "Month" else v, "", v == now) for v in self.values()]
        out = [(_("Automatic"), _("From time servers on the internet (recommended)"), self.c.time_automatic),
               (_("Set it myself"), "", not self.c.time_automatic)]
        if not self.c.time_automatic:
            out += [(_(self.FIELD_NAMES["Year"]), str(t.year), False),
                    (_(self.FIELD_NAMES["Month"]), _(MONTHS[t.month - 1]), False),
                    (_(self.FIELD_NAMES["Day"]), str(t.day), False),
                    (_(self.FIELD_NAMES["Hour"]), f"{t.hour:02d}", False),
                    (_(self.FIELD_NAMES["Minute"]), f"{t.minute:02d}", False)]
        return out

    def refresh(self, to_chosen=True):
        super().refresh(to_chosen)
        self.server_box.set_visible(self.stage == "servers")

    def pick(self, i):
        t = self.c.manual_time
        if self.stage == "servers":
            del self.c.time_servers[i]
        elif self.stage in self.FIELDS:
            v = self.values()[i]
            if self.stage in ("Year", "Month"):         # the day is kept, or made the month's last day
                year, month = (int(v), t.month) if self.stage == "Year" else (t.year, i + 1)
                t = t.replace(year=year, month=month, day=min(t.day, calendar.monthrange(year, month)[1]))
            elif self.stage == "Day":
                t = t.replace(day=int(v))
            elif self.stage == "Hour":
                t = t.replace(hour=int(v))
            else:
                t = t.replace(minute=int(v))
            self.c.manual_time = t
            self.stage = "main"
        elif i < 2:
            self.c.time_automatic = i == 0
        else:
            self.stage = self.FIELDS[i - 2]
        self.choose(to_chosen=self.stage != "main")

    def actions(self):
        if self.stage == "servers":
            return [(_("Add"), self.add_server)]
        if self.stage == "main" and self.c.time_automatic:
            return [(_("Time servers"), self.open_servers)]
        return []

    def open_servers(self):
        self.stage = "servers"
        self.choose(to_chosen=True)
        self.server.grab_focus()

    def add_server(self):
        name = self.server.get_text().strip().lower().replace(" ", "")
        if re.fullmatch(r"[a-z0-9.-]+", name) and name not in self.c.time_servers:
            self.c.time_servers.append(name)
            self.server.set_text("")
        self.choose()

    def ready(self):
        return self.stage == "main"

    def status(self):
        if self.c.time_automatic:
            servers = ", ".join(self.c.time_servers) or _("Fedora's time servers")
            return _("Chosen: automatic, from {servers}.").format(servers=servers)
        return _("Chosen: {time}.").format(time=time_text(self.c.manual_time))


# ---------------------------------------------------------------------------------------------------- 7 Clock

class ClockScreen(screens.ListScreen):
    title = N_("Clock")
    step = N_("Clock")

    @property
    def intro(self):
        return _("How should the clock show the time?")

    def items(self):
        h24 = self.c.clock_24 if self.c.clock_24 is not None else not data.uses_12_hour(self.c.locale)
        return [(_("12 hour"), "3:30 PM", not h24), (_("24 hour"), "15:30", h24)]

    def pick(self, i):
        self.c.clock_24 = i == 1
        self.choose()

    def status(self):
        return _("Chosen: {name}.").format(name=next(t for t, _x, chosen in self.items() if chosen))
