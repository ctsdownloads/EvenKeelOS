"""The installer's screen building blocks and what the person chose."""
import datetime

from gi.repository import Gtk

from widgets import ChoiceList, PasswordPair


class Choices:
    """Everything the person chose, filled in screen by screen. Passwords stay only in memory."""

    def __init__(self):
        self.locale = "en_US.UTF-8"
        self.layouts = ["us"]
        self.layouts_chosen_by_hand = False
        self.boot_layout = None                    # None: the first layout above
        self.timezone = None                       # None: automatic, from the computer's location
        self.time_automatic = True
        self.manual_time = datetime.datetime.now().replace(second=0, microsecond=0)
        self.time_servers = []                     # empty: Fedora's own pool
        self.clock_24 = None                       # None: as the language writes times
        self.disk = None
        self.encrypt = True
        self.disk_password = ""
        self.root_enabled = False
        self.root_password = ""
        self.full_name = ""
        self.username = ""
        self.username_by_hand = False
        self.admin = True
        self.user_password = ""
        self.hostname = ""
        self.hostname_by_hand = False


class Screen:
    title = ""
    step = ""                      # the name in the step line ("Step 3 of 14: Keyboard"); empty: not a step
    intro = ""
    back = True
    next_label = "Next"            # None: no Next button
    main = None                    # the action button shown as the main one
    danger = None                  # the action button shown in red

    def __init__(self, win):
        self.win = win
        self.c = win.choices
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, vexpand=True)
        self.build()

    def build(self):
        pass

    def enter(self):
        """Called each time the screen is shown."""
        self.refresh()

    def refresh(self):
        pass

    def pick(self, i):
        pass

    def actions(self):
        """[(button name, what it does)], shown before Next."""
        return []

    def ready(self):
        return True

    def status(self):
        return ""

    def go_back(self):
        """Back inside the screen (a sub-list); False when Back should leave the screen."""
        return False

    def changed(self):
        self.win.update()


class ListScreen(Screen):
    """One list screen: items are (title, subtitle, chosen)."""
    first_stage = None          # for a screen with sub-lists: the stage Back returns to

    def build(self):
        self.list = ChoiceList(self.pick)
        self.body.append(self.list)

    def items(self):
        return []

    def refresh(self, to_chosen=True):
        self.list.show_lines(self.items(), to_chosen)

    def go_back(self):
        if self.first_stage is None or self.stage == self.first_stage:
            return False
        self.stage = self.first_stage
        self.choose(to_chosen=True)
        return True

    def choose(self, to_chosen=False):
        """After a pick the list stays where it is; to_chosen when it shows a different list (a sub-list)."""
        self.refresh(to_chosen)
        self.changed()


class PasswordChoiceScreen(ListScreen):
    """Two choices, the second (or first) asking for a password typed twice."""
    what = ""

    def build(self):
        super().build()
        self.list.set_vexpand(False)
        self.list.set_propagate_natural_height(True)
        self.pair = PasswordPair(self.what, self._typed)
        self.body.append(self.pair)

    def _typed(self):
        self.keep(self.pair.text() if self.pair.ready() else "")
        self.changed()

    def keep(self, password):
        """Store the typed password in the choices ("" until both match)."""

    def wants_password(self):
        return False

    def refresh(self, to_chosen=True):
        super().refresh(to_chosen)
        self.pair.set_visible(self.wants_password())

    def choose(self, to_chosen=False):
        super().choose(to_chosen)
        if self.wants_password():
            self.pair.focus()

    def ready(self):
        return not self.wants_password() or self.pair.ready()
