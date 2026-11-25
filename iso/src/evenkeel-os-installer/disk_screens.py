"""Installer steps for the disk, encryption, accounts, computer name, experience, desktop layout and the review."""
import os
import re

from gi.repository import Adw, Gtk

import data
import fitcheck
from widgets import PasswordPair
import locale_screens
import screens

HERE = os.path.dirname(os.path.realpath(__file__))


class DiskScreen(screens.ListScreen):
    title = "Disk"
    step = "Disk"
    intro = ("Which disk should EvenKeelOS go on? Everything on it will be erased. "
             "The USB stick this runs from is not listed.")

    def enter(self):
        self.disks = data.disks()
        self.raid = fitcheck.raid_hidden()
        if self.c.disk not in self.disks:            # gone, or another disk now has its name
            self.c.disk = None
        super().enter()

    def items(self):
        return [(f"{d['model']}, {d['size']}",
                 d["path"] + (", has encrypted data" if d["encrypted"] else ""),
                 bool(self.c.disk) and self.c.disk["path"] == d["path"]) for d in self.disks]

    def pick(self, i):
        self.c.disk = self.disks[i]
        self.choose()

    def actions(self):
        return [("Refresh", self.enter)]

    def ready(self):
        return self.c.disk is not None

    def status(self):
        advice = f" {fitcheck.RAID_ADVICE}" if self.raid else ""
        if not self.disks:
            return ("No disk was found. Connect one and click Refresh." if not advice else
                    "A disk is hidden." + advice)
        return (f"Chosen: {self.c.disk['model']}, {self.c.disk['size']}." if self.c.disk else
                "No disk chosen yet.") + advice


# ---------------------------------------------------------------------------------------------------- 9 Erase warning

class EraseScreen(screens.Screen):
    title = "Erase the disk?"
    step = "Erase"
    next_label = None
    danger = "Erase and install"
    intro = "To go on, click Erase and install. To pick another disk, click Back."

    def build(self):
        self.warning = Gtk.Label(wrap=True, xalign=0, css_classes=["title-2", "erase-warning"])
        self.body.append(self.warning)

    def refresh(self):
        self.warning.set_text(self.status())

    def actions(self):
        return [("Erase and install", self.win.go_next)]

    def status(self):
        d = self.c.disk
        return (f"Everything on {d['model']}, {d['size']} will be erased" +
                (", including encrypted data." if d["encrypted"] else "."))


# ---------------------------------------------------------------------------------------------------- 10 Encryption


class EncryptionScreen(screens.PasswordChoiceScreen):
    title = "Encryption"
    step = "Encryption"
    what = "Disk password"

    @property
    def intro(self):
        return ("Encrypting keeps the files on this disk private if the computer is lost or stolen. "
                "The disk password is typed at every start, until automatic unlock is turned on in Wheelhouse.")

    def items(self):
        return [("Encrypt the disk", "Recommended", self.c.encrypt),
                ("Don't encrypt", "", not self.c.encrypt)]

    def pick(self, i):
        self.c.encrypt = i == 0
        self.choose()

    def keep(self, password):
        self.c.disk_password = password

    def wants_password(self):
        return self.c.encrypt

    def status(self):
        if not self.c.encrypt:
            return "Chosen: don't encrypt."
        return "Chosen: encrypt. " + ("The password is typed and matches." if self.pair.ready() else
                                      "Type the disk password twice.")


# ---------------------------------------------------------------------------------------------------- 11 Root

class RootScreen(screens.PasswordChoiceScreen):
    title = "Administrator account (root)"
    step = "Root"
    what = "Root password"
    intro = ("The root account is the system's own administrator. Most people never need it: "
             "your own account can be an administrator instead.")

    def items(self):
        return [("Locked", "Recommended", not self.c.root_enabled),
                ("Enabled, with a password", "", self.c.root_enabled)]

    def pick(self, i):
        self.c.root_enabled = i == 1
        self.choose()

    def keep(self, password):
        self.c.root_password = password

    def wants_password(self):
        return self.c.root_enabled

    def status(self):
        return "Chosen: " + ("enabled." if self.c.root_enabled else "locked.")


# ---------------------------------------------------------------------------------------------------- 12 User

def system_names():
    """The user and group names the system already has: the installed system is the one this USB stick runs."""
    names = set()
    for path in ("/etc/passwd", "/usr/lib/passwd", "/etc/group", "/usr/lib/group"):
        if os.path.exists(path):
            with open(path) as f:
                names |= {line.split(":")[0] for line in f if ":" in line}
    return names


class UserScreen(screens.ListScreen):
    title = "Your account"
    step = "Account"
    intro = "Type your full name. Your user name is made from it; type over it to change it."

    def build(self):
        names = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"])
        self.full = Adw.EntryRow(title="Full name")
        self.user = Adw.EntryRow(title="User name")
        self.full.connect("changed", self._full_changed)
        self.user.connect("changed", self._user_changed)
        names.append(self.full)
        names.append(self.user)
        self.body.append(names)
        super().build()
        self.list.set_vexpand(False)
        self.list.set_propagate_natural_height(True)
        self.pair = PasswordPair("Password", self._typed)
        self.body.append(self.pair)
        self.setting = False
        self.taken = system_names()

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
            return "The user name is empty."
        if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", u):
            return "A user name uses small letters, digits, - and _, and starts with a letter."
        if u in self.taken:
            return f"{u} is used by the system. Choose another user name."
        return ""

    def full_name_problem(self):
        if not self.c.full_name:
            return "The full name is empty."
        if ":" in self.c.full_name or "," in self.c.full_name:
            return "A full name can't have : or , in it."
        return ""

    def items(self):
        return [("Administrator", "Can install software and change system settings. "
                 "Click to turn it " + ("off" if self.c.admin else "on") + ".", self.c.admin)]

    def pick(self, i):
        self.c.admin = not self.c.admin
        self.choose()

    def ready(self):
        return not self.full_name_problem() and not self.username_problem() and self.pair.ready()

    def status(self):
        name = self.c.full_name or "not set yet"
        problems = [p for p in (self.full_name_problem() if self.c.full_name else "",
                                self.username_problem() if self.c.username else "") if p]
        return (f"Full name: {name}. User name: {self.c.username or 'not set yet'}. "
                + "".join(p + " " for p in problems)
                + f"Administrator: {'yes' if self.c.admin else 'no'}. "
                + ("The password is typed and matches." if self.pair.ready() else "Type the password twice."))


# ---------------------------------------------------------------------------------------------------- 13 Computer name

class ComputerNameScreen(screens.Screen):
    title = "Computer name"
    step = "Computer name"
    intro = "This is how the computer shows up on your network. Keep the suggestion, or type a new one."

    def build(self):
        box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"])
        self.entry = Adw.EntryRow(title="Computer name")
        self.entry.connect("changed", self._changed)
        box.append(self.entry)
        self.body.append(box)
        self.setting = False

    def enter(self):
        if not self.c.hostname_by_hand:
            self.setting = True
            self.entry.set_text(f"{self.c.username or 'evenkeel'}-computer")
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
        return f"Computer name: {self.c.hostname}." + ("" if self.ready() else
                                                       " Use letters, digits and -, not at the start or end.")


# ---------------------------------------------------------------------------------------------------- 14 Experience

class ExperienceScreen(screens.ListScreen):
    title = "Coming from Windows?"
    step = "Experience"
    intro = ("This sets what you see at first. The next step suggests a desktop layout to match, and the guide is in "
             "Wheelhouse, Get help, either way.")
    CHOICES = [("windows", "Coming from Windows", "New to EvenKeelOS? opens at login, with the Windows-style desktop"),
               ("linux", "I already use Linux", "No guide at login, with the Standard desktop")]

    def items(self):
        return [(name, about, key == self.c.experience) for key, name, about in self.CHOICES]

    def pick(self, i):
        self.c.experience = self.CHOICES[i][0]
        if not self.c.layout_chosen_by_hand:
            self.c.layout = "windows" if self.c.experience == "windows" else "current"
        self.choose()

    def ready(self):
        return self.c.experience is not None

    def status(self):
        return "Chosen: " + experience_name(self.c.experience) + "." if self.c.experience else "Pick one."


def experience_name(key):
    return next(name for k, name, _a in ExperienceScreen.CHOICES if k == key)


# ---------------------------------------------------------------------------------------------------- 15 Desktop layout

class LayoutScreen(screens.Screen):
    title = "Desktop layout"
    step = "Desktop layout"
    intro = "How should the desktop look? Click one. You can switch later in Wheelhouse."
    CHOICES = [("current", "Standard", "A top bar, with the logo menu at the top left"),
               ("windows", "Windows-style", "A bottom bar, with a start menu on the logo")]

    def build(self):
        row = Gtk.Box(spacing=18, homogeneous=True)
        self.cards = {}
        for key, name, about in self.CHOICES:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=6, margin_bottom=6)
            picture = Gtk.Picture.new_for_filename(os.path.join(HERE, f"layout-{key}.png"))
            picture.set_size_request(320, 213)
            card.append(picture)
            card.append(Gtk.Label(label=name, css_classes=["title-4"]))
            card.append(Gtk.Label(label=about, wrap=True, justify=Gtk.Justification.CENTER, css_classes=["dim-label"]))
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
        return "Chosen: " + layout_name(self.c.layout) + "."


def layout_name(key):
    return next(name for k, name, _a in LayoutScreen.CHOICES if k == key)


# ---------------------------------------------------------------------------------------------------- 16 Review

class ReviewScreen(screens.ListScreen):
    title = "Review"
    step = "Review"
    next_label = None
    main = "Install"
    intro = "Check everything. Click a line to change it, or click Install to put EvenKeelOS on the disk."

    def summary(self):
        c, kb = self.c, data.keyboards()
        clock = "24 hour" if (c.clock_24 if c.clock_24 is not None else not data.uses_12_hour(c.locale)) else "12 hour"
        user = f"{c.full_name} ({c.username})" + (", administrator" if c.admin else "")
        return [
            ("Language", locale_screens.language_name(c.locale), locale_screens.LanguageScreen),
            ("Keyboard", ", ".join(kb[k] for k in c.layouts), locale_screens.KeyboardScreen),
            ("Keyboard at start", kb[c.boot_layout or c.layouts[0]], locale_screens.BootKeyboardScreen),
            ("Time zone", c.timezone.replace("_", " ") if c.timezone else "Automatic", locale_screens.TimeZoneScreen),
            ("Date and time", "Automatic" if c.time_automatic else c.manual_time.strftime("%-d %B %Y, %H:%M"),
             locale_screens.DateTimeScreen),
            ("Clock", clock, locale_screens.ClockScreen),
            ("Disk", f"{c.disk['model']}, {c.disk['size']}, erased" if c.disk else "Not chosen", DiskScreen),
            ("Encryption", "Encrypted" if c.encrypt else "Not encrypted", EncryptionScreen),
            ("Root", "Enabled" if c.root_enabled else "Locked", RootScreen),
            ("Account", user, UserScreen),
            ("Computer name", c.hostname, ComputerNameScreen),
            ("Experience", experience_name(c.experience), ExperienceScreen),
            ("Desktop layout", layout_name(c.layout), LayoutScreen),
        ]

    def items(self):
        return [(name, value, False) for name, value, _s in self.summary()]

    def pick(self, i):
        self.win.change(self.summary()[i][2])

    def actions(self):
        return [("Install", self.win.install)]

    def status(self):
        return " ".join(f"{name}: {value}." for name, value, _s in self.summary())
