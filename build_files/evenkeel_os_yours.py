"""Make it yours, in Wheelhouse: light and dark on a schedule, a wallpaper slideshow, and fonts and text size."""
import datetime

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk, Pango  # noqa: E402
import evenkeel_os_appearance as appearance  # noqa: E402
from evenkeel_os_ui import _, N_, ngettext, short_home, time_format  # noqa: E402

TIMES = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
FONTS = tuple(zip(appearance.FONT_NAMES, (N_("Menus and windows"), N_("Documents"), N_("Code and terminal"))))


def combo(title, names, selected):
    """A drop-down row; the list is set before the choice, which GTK needs in that order."""
    row = Adw.ComboRow(title=title)
    row.set_model(Gtk.StringList.new(names))
    row.set_selected(selected)
    return row


class Yours:
    """The three sections; window is Wheelhouse's window (its toasts, and the parent of the folder picker)."""

    def __init__(self, window):
        self.window = window
        self.state = appearance.load()
        self.ui = Gio.Settings(schema_id="org.gnome.desktop.interface")
        self.time_format = time_format()

    def groups(self):
        return [self.schedule_group(), self.slideshow_group(), self.fonts_group()]

    def clock(self, t):
        return t.strftime(self.time_format)

    def fresh(self):
        """The settings as saved now: the timer may have moved on since this page opened."""
        self.state = appearance.load()
        return self.state

    def save_and_apply(self):
        appearance.apply(self.state)
        appearance.save(self.state)

    def schedule_group(self):
        g = Adw.PreferencesGroup(title=_("Light and dark"),
                                 description=_("Switches the dark style for you. Night Light in Settings only warms "
                                               "the colors. You can still switch it yourself any time."))
        keys = list(appearance.SCHEDULES)
        self.mode = combo(_("Dark style"), [_(v) for v in appearance.SCHEDULES.values()],
                          keys.index(self.state["schedule"]))
        self.mode.connect("notify::selected", self.on_mode)
        g.add(self.mode)
        labels = [self.clock(datetime.time.fromisoformat(t)) for t in TIMES]
        self.dark_from = self.time_row(_("Dark from"), "dark_from", labels)
        self.light_from = self.time_row(_("Light from"), "light_from", labels)
        g.add(self.dark_from)
        g.add(self.light_from)
        self.show_schedule()
        return g

    def time_row(self, title, key, labels):
        at = self.state[key] if self.state[key] in TIMES else TIMES[0]
        row = combo(title, labels, TIMES.index(at))
        row.connect("notify::selected", self.on_time, key)
        return row

    def show_schedule(self):
        custom = self.state["schedule"] == "custom"
        self.dark_from.set_visible(custom)
        self.light_from.set_visible(custom)
        now = datetime.datetime.now().astimezone()
        hours = appearance.dark_hours(self.state, now)
        if self.state["schedule"] == "off":
            text = _("Switch between light and dark yourself, in Settings or the quick settings menu.")
        elif hours is None and appearance.place(appearance.time_zone()):
            up = appearance.sun_up(*appearance.place(appearance.time_zone()), now)
            text = (_("The sun doesn't set or rise here today, so it's light until it sets.") if up else
                    _("The sun doesn't set or rise here today, so it's dark until it rises."))
        elif hours is None:
            text = _("Sunset and sunrise can't be worked out for this time zone. Use Custom times.")
        elif self.state["schedule"] == "sun":
            city = (appearance.listed_zone(appearance.time_zone()) or "").rsplit("/", 1)[-1].replace("_", " ")
            # Translators: {city} is the city of the person's time zone.
            text = _("Dark from {start} to {end} today, worked out for {city} (your time zone's city).").format(
                start=self.clock(hours[0]), end=self.clock(hours[1]), city=city)
        else:
            text = _("Dark from {start} to {end}.").format(start=self.clock(hours[0]), end=self.clock(hours[1]))
        self.mode.set_subtitle(text)

    def on_mode(self, row, _param):
        self.fresh()["schedule"] = list(appearance.SCHEDULES)[row.get_selected()]
        self.state.pop("period", None)              # applies at once, not at the next sunset
        self.save_and_apply()
        self.show_schedule()

    def on_time(self, row, _param, key):
        self.fresh()[key] = TIMES[row.get_selected()]
        self.state.pop("period", None)
        self.save_and_apply()
        self.show_schedule()

    def slideshow_group(self):
        g = Adw.PreferencesGroup(title=_("Wallpaper slideshow"),
                                 description=_("The wallpaper changes to the next picture in a folder of yours."))
        self.slides = Adw.SwitchRow(title=_("Slideshow"), active=bool(self.state["slideshow"]))
        self.slides.connect("notify::active", self.on_slides)
        g.add(self.slides)
        self.folder = Adw.ActionRow(title=_("Folder"))
        pick = Gtk.Button(label=_("Choose"), valign=Gtk.Align.CENTER)
        pick.connect("clicked", lambda *_args: self.pick_folder())
        self.folder.add_suffix(pick)
        g.add(self.folder)
        keys = list(appearance.EVERY)
        every = combo(_("Change it"), [_(v) for v in appearance.EVERY.values()], keys.index(self.state["every"]))
        every.connect("notify::selected", self.on_every)
        g.add(every)
        self.show_folder()
        return g

    def show_folder(self):
        folder = self.state.get("folder", "")
        count = len(appearance.pictures(folder)) if folder else 0
        self.folder.set_subtitle(ngettext("{where}, {count} picture", "{where}, {count} pictures", count).format(
            where=short_home(folder), count=count) if folder else _("None picked yet."))

    def on_slides(self, row, _param):
        if row.get_active() and not self.fresh().get("folder"):
            self.pick_folder()
            return
        self.fresh()["slideshow"] = self.state.get("folder", "") if row.get_active() else ""
        self.state.pop("slot", None)
        self.save_and_apply()

    def pick_folder(self):
        Gtk.FileDialog(title=_("Pick a folder of pictures")).select_folder(self.window, None, self.on_folder)

    def on_folder(self, dialog, result):
        try:
            path = dialog.select_folder_finish(result).get_path()
        except GLib.Error:
            path = None
        if path and not appearance.pictures(path):
            self.window.toast(_("That folder has no pictures in it (JPEG, PNG or WebP)."))
            path = None
        if path:
            self.fresh()["folder"] = path
            if self.slides.get_active():
                self.state["slideshow"] = path
                self.state.pop("slot", None)
            self.save_and_apply()
            self.show_folder()
        if not self.state.get("folder"):
            self.slides.set_active(False)
        elif path and not self.slides.get_active():
            self.slides.set_active(True)

    def on_every(self, row, _param):
        self.fresh()["every"] = list(appearance.EVERY)[row.get_selected()]
        self.state.pop("slot", None)
        self.save_and_apply()

    def fonts_group(self):
        g = Adw.PreferencesGroup(title=_("Fonts and text"))
        back = Gtk.Button(label=_("Back to the original"), valign=Gtk.Align.CENTER)
        back.connect("clicked", self.on_back)
        g.set_header_suffix(back)
        self.font_buttons = {}
        for key, title in FONTS:
            row = Adw.ActionRow(title=_(title))
            b = Gtk.FontDialogButton(dialog=Gtk.FontDialog(title=_(title)), valign=Gtk.Align.CENTER)
            b.set_font_desc(Pango.FontDescription.from_string(self.ui.get_string(key)))
            b.connect("notify::font-desc", self.on_font, key)
            row.add_suffix(b)
            g.add(row)
            self.font_buttons[key] = b
        size = Adw.SpinRow.new_with_range(0.8, 2.0, 0.05)
        size.set_title(_("Text size"))
        size.set_subtitle(_("1.00 is the normal size. Large text in Settings, Accessibility sets 1.25."))
        size.set_digits(2)
        self.ui.bind("text-scaling-factor", size, "value", Gio.SettingsBindFlags.DEFAULT)
        g.add(size)
        return g

    def on_font(self, button, _param, key):
        desc = button.get_font_desc()
        if desc and desc.to_string() != self.ui.get_string(key):
            self.ui.set_string(key, desc.to_string())

    def on_back(self, _button):
        for key in appearance.FONT_KEYS:
            self.ui.reset(key)
        for key, b in self.font_buttons.items():
            b.set_font_desc(Pango.FontDescription.from_string(self.ui.get_string(key)))
        self.window.toast(_("Fonts and text size are back to EvenKeelOS's own."))
