"""Installer steps for language, keyboards, network, time zone, date and clock."""
import calendar
import re

from gi.repository import Adw, Gio, GLib, Gtk

import data
import screens

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


class LanguageScreen(screens.ListScreen):
    title = "Language"
    step = "Language"
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
            return "Which language should EvenKeelOS use?"
        return "Which one? Back goes to the list of languages."

    def items(self):
        if self.stage == "language":
            return [(eng, native if native != eng else "", lang == self.lang)
                    for lang, eng, native in self.langs]
        return [(eng, native if native != eng else "", loc == self.c.locale)
                for loc, eng, native in data.locales(self.lang)]

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
                self.choose(to_chosen=True)
                return
        else:
            self.c.locale = data.locales(self.lang)[i][0]
        self.choose()

    def status(self):
        return f"Chosen: {language_name(self.c.locale)}."


def language_name(loc):
    return next((eng for code, eng, _n in data.locales(loc.split("_")[0].split(".")[0]) if code == loc), loc)


# ---------------------------------------------------------------------------------------------------- 2 Keyboard

class KeyboardScreen(screens.ListScreen):
    title = "Keyboard layout"
    step = "Keyboard"
    intro = ("Which keyboard layouts do you use? Click one to add it, or click it again to take it off. "
             "The first one is used unless you switch.")

    def build(self):
        super().build()
        self.all = data.keyboards()

    def enter(self):
        self.suggested = [k for k in data.suggested_keyboards(self.c.locale) if k in self.all]
        if not self.c.layouts_chosen_by_hand:
            self.c.layouts = self.suggested[:1]
        rest = sorted((k for k in self.all if k not in self.suggested), key=lambda k: self.all[k].lower())
        self.order = self.suggested + rest
        super().enter()

    def items(self):
        return [(self.all[k], "Suggested" if k in self.suggested else "", k in self.c.layouts)
                for k in self.order]

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
        return "Chosen: " + ", ".join(self.all[k] for k in self.c.layouts) + "."


# ------------------------------------------------------------------------------------- 3 Keyboard at start

class BootKeyboardScreen(screens.ListScreen):
    """Layouts the text console has, for typing the disk password."""
    title = "Keyboard for the disk password"
    step = "Keyboard at start"
    intro = ("If the disk is encrypted, its password is typed when the computer starts, before EvenKeelOS loads. "
             "Which keyboard layout is used then?")

    def build(self):
        super().build()
        self.all = data.keyboards()
        self.order = sorted((k for k in self.all if data.has_console_keymap(k)), key=lambda k: self.all[k].lower())

    def same_offered(self):
        return self.c.layouts[0] in self.order

    def enter(self):
        if self.c.boot_layout is None and not self.same_offered():
            self.c.boot_layout = "us"
        super().enter()

    def items(self):
        first = self.all[self.c.layouts[0]]
        same = [("Same as above", first, self.c.boot_layout is None)] if self.same_offered() else []
        return same + [(self.all[k], "", self.c.boot_layout == k) for k in self.order]

    def pick(self, i):
        if self.same_offered():
            self.c.boot_layout = None if i == 0 else self.order[i - 1]
        else:
            self.c.boot_layout = self.order[i]
        self.choose()

    def status(self):
        k = self.c.boot_layout or self.c.layouts[0]
        first = self.all[self.c.layouts[0]]
        missing = "" if self.same_offered() else f"{first} can't be used before EvenKeelOS loads. "
        return f"{missing}Chosen: {self.all[k]}."


# ---------------------------------------------------------------------------------------------------- 4 Network

class NetworkScreen(screens.ListScreen):
    title = "Network"
    step = "Network"

    def build(self):
        super().build()
        self.password = Adw.PasswordEntryRow(title="Wi-Fi password")
        self.password.connect("entry-activated", lambda *_: self.connect_wifi())
        self.password_box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"],
                                        visible=False)
        self.password_box.append(self.password)
        self.body.append(self.password_box)
        self.wired, self.wifi, self.chosen, self.busy = False, [], None, ""

    @property
    def intro(self):
        if self.chosen and self.chosen["secured"]:
            return f"Type the password for {self.chosen['ssid']}, then click Connect. Back goes to the list."
        return ("A network is only needed for automatic time and time zone. To use Wi-Fi, click a network. "
                "Or click Next to go on without it.")

    def enter(self):
        self.wired, self.wifi = data.network()
        super().enter()

    def items(self):
        if self.chosen and self.chosen["secured"]:
            return []
        return [(w["ssid"], f"Signal {w['signal']}%" + (", password needed" if w["secured"] else ""),
                 False) for w in self.wifi]

    def refresh(self, to_chosen=True):
        super().refresh(to_chosen)
        asking = bool(self.chosen and self.chosen["secured"])
        self.list.set_visible(not asking)
        self.password_box.set_visible(asking)

    def pick(self, i):
        self.chosen = self.wifi[i]
        if self.chosen["secured"]:
            self.password.set_text("")
            self.choose()
            self.password.grab_focus()
        else:
            self.connect_wifi()

    def actions(self):
        if self.chosen and self.chosen["secured"]:
            return [("Connect", self.connect_wifi)]
        return [("Refresh", self.enter)]

    def connect_wifi(self):
        ssid = self.chosen["ssid"]
        args = ["nmcli", "device", "wifi", "connect", ssid]
        if self.chosen["secured"]:
            args += ["password", self.password.get_text()]
        self.busy = f"Connecting to {ssid}..."
        self.choose()
        proc = Gio.Subprocess.new(args, Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE)
        proc.wait_check_async(None, self._connected, ssid)

    def _connected(self, proc, result, ssid):
        try:
            ok = proc.wait_check_finish(result)
        except GLib.Error:
            ok = False
        self.busy = f"Connected to {ssid}." if ok else f"Could not connect to {ssid}. Check the password."
        if ok:
            self.chosen = None
        self.wired, self.wifi = data.network()
        self.choose()

    def go_back(self):
        if self.chosen:
            self.chosen, self.busy = None, ""
            self.choose()
            return True
        return False

    def status(self):
        return self.busy or ("Wired network: connected." if self.wired else
                             "Wired network: not connected." + ("" if self.wifi else " No Wi-Fi networks found."))


# ---------------------------------------------------------------------------------------------------- 5 Time zone

class TimeZoneScreen(screens.ListScreen):
    title = "Time zone"
    step = "Time zone"

    def build(self):
        super().build()
        self.zones = data.timezones()
        self.regions = list(self.zones)
        self.region = None

    @property
    def intro(self):
        if self.region:
            return f"Which city in {self.region} has your time? Back goes to the regions."
        return "Set the time zone automatically, or pick a region, then a city."

    def items(self):
        if self.region:
            return [(city, "", tz == self.c.timezone) for tz, city in self.zones[self.region]]
        return ([("Automatic", "From the computer's location (recommended)", self.c.timezone is None)] +
                [(r, "", bool(self.c.timezone) and self.c.timezone.startswith(r + "/")) for r in self.regions])

    def pick(self, i):
        if self.region:
            self.c.timezone = self.zones[self.region][i][0]
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
        return f"Chosen: {self.c.timezone.replace('_', ' ') if self.c.timezone else 'Automatic'}."


# ---------------------------------------------------------------------------------------------------- 6 Date and time

class DateTimeScreen(screens.ListScreen):
    title = "Date and time"
    step = "Date and time"
    first_stage = "main"
    FIELDS = ["Year", "Month", "Day", "Hour", "Minute"]

    def build(self):
        self.server = Adw.EntryRow(title="Time server name")
        self.server.connect("entry-activated", lambda *_: self.add_server())
        self.server_box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"],
                                      visible=False)
        self.server_box.append(self.server)
        self.body.append(self.server_box)
        super().build()
        self.stage = "main"                 # main, a field name, or servers

    @property
    def intro(self):
        if self.stage == "servers":
            return ("Time servers to use instead of Fedora's. Type a name and click Add. Click a server to take it "
                    "off. Click Back when done.")
        if self.stage in self.FIELDS:
            return f"Pick the {self.stage.lower()}. Back keeps it as it is."
        return "Keep the clock right automatically, or set the date and time yourself."

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
            return [(v, "", v == now) for v in self.values()]
        out = [("Automatic", "From time servers on the internet (recommended)", self.c.time_automatic),
               ("Set it myself", "", not self.c.time_automatic)]
        if not self.c.time_automatic:
            out += [("Year", str(t.year), False), ("Month", MONTHS[t.month - 1], False),
                    ("Day", str(t.day), False), ("Hour", f"{t.hour:02d}", False),
                    ("Minute", f"{t.minute:02d}", False)]
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
            return [("Add", self.add_server)]
        if self.stage == "main" and self.c.time_automatic:
            return [("Time servers", self.open_servers)]
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
            servers = ", ".join(self.c.time_servers) or "Fedora's time servers"
            return f"Chosen: automatic, from {servers}."
        return f"Chosen: {self.c.manual_time.strftime('%-d %B %Y, %H:%M')}."


# ---------------------------------------------------------------------------------------------------- 7 Clock

class ClockScreen(screens.ListScreen):
    title = "Clock"
    step = "Clock"
    intro = "How should the clock show the time?"

    def items(self):
        h24 = self.c.clock_24 if self.c.clock_24 is not None else not data.uses_12_hour(self.c.locale)
        return [("12 hour", "3:30 PM", not h24), ("24 hour", "15:30", h24)]

    def pick(self, i):
        self.c.clock_24 = i == 1
        self.choose()

    def status(self):
        return "Chosen: " + next(t for t, _x, chosen in self.items() if chosen) + "."
