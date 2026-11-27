"""Installer steps for the disk, encryption, accounts, computer name, experience, desktop layout and the review."""
import os
import re

from gi.repository import Adw, Gtk

import data
import i18n
import fitcheck
from widgets import PasswordPair
import locale_screens
import screens
from i18n import _, N_

HERE = os.path.dirname(os.path.realpath(__file__))


def disk_name(disk):
    return f"{disk['model']}, {disk['size']}"


class DiskScreen(screens.ListScreen):
    title = N_("Disk")
    step = N_("Disk")

    @property
    def intro(self):
        return _("Which disk should EvenKeelOS go on? Everything on it will be erased. "
                 "The USB stick this runs from is not listed.")

    def enter(self):
        self.disks = data.disks()
        self.raid = fitcheck.raid_hidden()
        if self.c.disk not in self.disks:            # gone, or another disk now has its name
            self.c.disk = None
        super().enter()

    def items(self):
        return [(disk_name(d),
                 (_("{path}, has encrypted data").format(path=d["path"]) if d["encrypted"] else d["path"]),
                 bool(self.c.disk) and self.c.disk["path"] == d["path"]) for d in self.disks]

    def pick(self, i):
        self.c.disk = self.disks[i]
        self.choose()

    def actions(self):
        return [(_("Refresh"), self.enter)]

    def ready(self):
        return self.c.disk is not None

    def status(self):
        advice = " " + _(fitcheck.RAID_ADVICE) if self.raid else ""
        if not self.disks:
            return (_("No disk was found. Connect one and click Refresh.") if not advice else
                    _("A disk is hidden.") + advice)
        return (_("Chosen: {disk}.").format(disk=disk_name(self.c.disk)) if self.c.disk else
                _("No disk chosen yet.")) + advice


# 9 Erase warning

class EraseScreen(screens.Screen):
    title = N_("Erase the disk?")
    step = N_("Erase")
    next_label = None
    danger = N_("Erase and install")

    @property
    def intro(self):
        return _("To go on, click Erase and install. To pick another disk, click Back.")

    def build(self):
        self.warning = Gtk.Label(wrap=True, xalign=0, css_classes=["title-2", "erase-warning"])
        self.body.append(self.warning)

    def refresh(self):
        self.warning.set_text(self.status())

    def actions(self):
        return [(_("Erase and install"), self.win.go_next)]

    def status(self):
        return (_("Everything on {disk} will be erased, including encrypted data.") if self.c.disk["encrypted"] else
                _("Everything on {disk} will be erased.")).format(disk=disk_name(self.c.disk))


# 10 Encryption


class EncryptionScreen(screens.PasswordChoiceScreen):
    title = N_("Encryption")
    step = N_("Encryption")
    what = N_("Disk password")

    @property
    def intro(self):
        return _("Encrypting keeps the files on this disk private if the computer is lost or stolen. "
                 "The disk password is typed at every start, until automatic unlock is turned on in Wheelhouse.")

    def items(self):
        return [(_("Encrypt the disk"), _("Recommended"), self.c.encrypt),
                (_("Don't encrypt"), "", not self.c.encrypt)]

    def pick(self, i):
        self.c.encrypt = i == 0
        self.choose()

    def keep(self, password):
        self.c.disk_password = password

    def wants_password(self):
        return self.c.encrypt

    def status(self):
        if not self.c.encrypt:
            return _("Chosen: don't encrypt.")
        return _("Chosen: encrypt.") + " " + (_("The password is typed and matches.") if self.pair.ready() else
                                              _("Type the disk password twice."))


# 11 Root

class RootScreen(screens.PasswordChoiceScreen):
    title = N_("Administrator account (root)")
    step = N_("Root")
    what = N_("Root password")

    @property
    def intro(self):
        return _("The root account is the system's own administrator. Most people never need it: "
                 "your own account can be an administrator instead.")

    def items(self):
        return [(_("Locked"), _("Recommended"), not self.c.root_enabled),
                (_("Enabled, with a password"), "", self.c.root_enabled)]

    def pick(self, i):
        self.c.root_enabled = i == 1
        self.choose()

    def keep(self, password):
        self.c.root_password = password

    def wants_password(self):
        return self.c.root_enabled

    def status(self):
        return _("Chosen: enabled.") if self.c.root_enabled else _("Chosen: locked.")


# 12 User

def system_names():
    """The user and group names the system already has: the installed system is the one this USB stick runs."""
    names = set()
    for path in ("/etc/passwd", "/usr/lib/passwd", "/etc/group", "/usr/lib/group"):
        if os.path.exists(path):
            with open(path) as f:
                names |= {line.split(":")[0] for line in f if ":" in line}
    return names


class UserScreen(screens.ListScreen):
    title = N_("Your account")
    step = N_("Account")

    @property
    def intro(self):
        return _("Type your full name. Your user name is made from it; type over it to change it.")

    def build(self):
        names = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"])
        self.full = Adw.EntryRow()
        self.user = Adw.EntryRow()
        self.full.connect("changed", self._full_changed)
        self.user.connect("changed", self._user_changed)
        names.append(self.full)
        names.append(self.user)
        self.body.append(names)
        super().build()
        self.list.set_vexpand(False)
        self.list.set_propagate_natural_height(True)
        self.pair = PasswordPair(N_("Password"), self._typed)
        self.body.append(self.pair)
        self.setting = False
        self.taken = system_names()

    def relabel(self):
        self.full.set_title(_("Full name"))
        self.user.set_title(_("User name"))
        self.pair.refresh()

    def _typed(self):
        self.c.user_password = self.pair.text() if self.pair.ready() else ""
        self.changed()

    def enter(self):
        super().enter()
        self.full.grab_focus()

    def _full_changed(self, *_):
        self.c.full_name = " ".join(self.full.get_text().split())
        if not self.c.username_by_hand:
            first = re.sub(r"[^a-z0-9]", "", (self.c.full_name.split() or [""])[0].lower())
            self.setting = True
            self.user.set_text(first if first and first[0].isalpha() else "")
            self.setting = False
        self.changed()

    def _user_changed(self, *_):
        self.c.username = self.user.get_text().strip()
        if not self.setting:
            self.c.username_by_hand = True
        self.changed()

    def username_problem(self):
        u = self.c.username
        if not u:
            return _("The user name is empty.")
        if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", u):
            return _("A user name uses small letters, digits, - and _, and starts with a letter.")
        if u in self.taken:
            return _("{name} is used by the system. Choose another user name.").format(name=u)
        return ""

    def full_name_problem(self):
        if not self.c.full_name:
            return _("The full name is empty.")
        if ":" in self.c.full_name or "," in self.c.full_name:
            return _("A full name can't have : or , in it.")
        return ""

    def items(self):
        about = (_("Can install software and change system settings. Click to turn it off.") if self.c.admin else
                 _("Can install software and change system settings. Click to turn it on."))
        return [(_("Administrator"), about, self.c.admin)]

    def pick(self, i):
        self.c.admin = not self.c.admin
        self.choose()

    def ready(self):
        return not self.full_name_problem() and not self.username_problem() and self.pair.ready()

    def status(self):
        name = self.c.full_name or _("not set yet")
        problems = [p for p in (self.full_name_problem() if self.c.full_name else "",
                                self.username_problem() if self.c.username else "") if p]
        return (_("Full name: {name}. User name: {username}.").format(name=name,
                                                                      username=self.c.username or _("not set yet"))
                + " " + "".join(p + " " for p in problems)
                + (_("Administrator: yes.") if self.c.admin else _("Administrator: no.")) + " "
                + (_("The password is typed and matches.") if self.pair.ready() else _("Type the password twice.")))


# 13 Computer name

class ComputerNameScreen(screens.Screen):
    title = N_("Computer name")
    step = N_("Computer name")

    @property
    def intro(self):
        return _("This is how the computer shows up on your network. Keep the suggestion, or type a new one.")

    def relabel(self):
        self.entry.set_title(_("Computer name"))

    def build(self):
        box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"])
        self.entry = Adw.EntryRow()
        self.entry.connect("changed", self._changed)
        box.append(self.entry)
        self.body.append(box)
        self.setting = False

    def enter(self):
        if not self.c.hostname_by_hand:
            self.setting = True
            suggestion = f"{self.c.username or 'evenkeel'}-computer"      # a host name, not translated
            self.entry.set_text(suggestion)
            self.setting = False
        self.entry.grab_focus()

    def _changed(self, *_):
        self.c.hostname = self.entry.get_text().strip().lower()
        if not self.setting:
            self.c.hostname_by_hand = True
        self.changed()

    def ready(self):
        return bool(re.fullmatch(r"[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?", self.c.hostname))

    def status(self):
        return _("Computer name: {name}.").format(name=self.c.hostname) + (
            "" if self.ready() else " " + _("Use letters, digits and -, not at the start or end."))


# 14 Experience

class ExperienceScreen(screens.ListScreen):
    title = N_("Coming from Windows?")
    step = N_("Experience")
    CHOICES = [("windows", N_("Coming from Windows"),
                N_("New to EvenKeelOS? opens at login, with the Windows-style desktop")),
               ("linux", N_("I already use Linux"), N_("No guide at login, with the Standard desktop"))]

    @property
    def intro(self):
        return _("This sets what you see at first. The next step suggests a desktop layout to match, and the guide "
                 "is in Wheelhouse, Get help, either way.")

    def items(self):
        return [(_(name), _(about), key == self.c.experience) for key, name, about in self.CHOICES]

    def pick(self, i):
        self.c.experience = self.CHOICES[i][0]
        if not self.c.layout_chosen_by_hand:
            self.c.layout = "windows" if self.c.experience == "windows" else "current"
        self.choose()

    def ready(self):
        return self.c.experience is not None

    def status(self):
        if not self.c.experience:
            return _("Pick one.")
        return _("Chosen: {name}.").format(name=choice_name(ExperienceScreen.CHOICES, self.c.experience))


# 15 Desktop layout

class LayoutScreen(screens.Screen):
    title = N_("Desktop layout")
    step = N_("Desktop layout")
    CHOICES = [("current", N_("Standard"), N_("A top bar, with the logo menu at the top left")),
               ("windows", N_("Windows-style"), N_("A bottom bar, with a start menu on the logo"))]

    @property
    def intro(self):
        return _("How should the desktop look? Click one. You can switch later in Wheelhouse.")

    def relabel(self):
        for key, name, about in self.CHOICES:
            self.names[key].set_label(_(name))
            self.abouts[key].set_label(_(about))

    def build(self):
        row = Gtk.Box(spacing=18, homogeneous=True)
        self.cards, self.names, self.abouts = {}, {}, {}
        for key, name, about in self.CHOICES:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=6, margin_bottom=6)
            picture = Gtk.Picture.new_for_filename(os.path.join(HERE, f"layout-{key}.png"))
            picture.set_size_request(320, 213)
            card.append(picture)
            self.names[key] = Gtk.Label(css_classes=["title-4"])
            self.abouts[key] = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER, css_classes=["dim-label"])
            card.append(self.names[key])
            card.append(self.abouts[key])
            button = Gtk.Button(child=card, css_classes=["layout-card"])
            button.connect("clicked", self._clicked, key)
            row.append(button)
            self.cards[key] = button
        self.body.append(row)

    def _clicked(self, _button, key):
        self.c.layout = key
        self.c.layout_chosen_by_hand = True
        self.refresh()
        self.changed()

    def refresh(self):
        for key, button in self.cards.items():
            (button.add_css_class if key == self.c.layout else button.remove_css_class)("chosen")

    def status(self):
        return _("Chosen: {name}.").format(name=choice_name(LayoutScreen.CHOICES, self.c.layout))


def choice_name(choices, key):
    """The shown name of a key in a screen's CHOICES."""
    return _(next(name for k, name, _a in choices if k == key))


# 16 Review

class ReviewScreen(screens.ListScreen):
    title = N_("Review")
    step = N_("Review")
    next_label = None
    main = N_("Install")

    @property
    def intro(self):
        return _("Check everything. Click a line to change it, or click Install to put EvenKeelOS on the disk.")

    def summary(self):
        c, kb = self.c, data.keyboards()
        clock = _("24 hour") if c.uses_24_hour() else _("12 hour")
        user = (_("{name} ({username}), administrator") if c.admin else _("{name} ({username})")).format(
            name=c.full_name, username=c.username)
        return [
            (_("Language"), i18n.language(c.locale), locale_screens.LanguageScreen),
            (_("Keyboard"), ", ".join(i18n.keyboard(kb[k]) for k in c.layouts), locale_screens.KeyboardScreen),
            (_("Keyboard at start"), i18n.keyboard(kb[c.boot_layout or c.layouts[0]]),
             locale_screens.BootKeyboardScreen),
            (_("Time zone"), i18n.place(c.timezone) if c.timezone else _("Automatic"),
             locale_screens.TimeZoneScreen),
            (_("Date and time"), _("Automatic") if c.time_automatic else locale_screens.time_text(c.manual_time),
             locale_screens.DateTimeScreen),
            (_("Clock"), clock, locale_screens.ClockScreen),
            (_("Disk"), _("{disk}, erased").format(disk=disk_name(c.disk)) if c.disk else
             _("Not chosen"), DiskScreen),
            (_("Encryption"), _("Encrypted") if c.encrypt else _("Not encrypted"), EncryptionScreen),
            (_("Root"), _("Enabled") if c.root_enabled else _("Locked"), RootScreen),
            (_("Account"), user, UserScreen),
            (_("Computer name"), c.hostname, ComputerNameScreen),
            (_("Experience"), choice_name(ExperienceScreen.CHOICES, c.experience), ExperienceScreen),
            (_("Desktop layout"), choice_name(LayoutScreen.CHOICES, c.layout), LayoutScreen),
        ]

    def items(self):
        return [(name, value, False) for name, value, _s in self.summary()]

    def pick(self, i):
        self.win.change(self.summary()[i][2])

    def actions(self):
        return [(_("Install"), self.win.install)]

    def status(self):
        return " ".join(_("{name}: {value}.").format(name=name, value=value) for name, value, _s in self.summary())
