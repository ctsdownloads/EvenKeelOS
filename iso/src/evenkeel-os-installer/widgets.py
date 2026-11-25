"""Installer building blocks: a list to pick from, and a typed password with its strength."""
import pwquality
from gi.repository import Adw, GLib, Gtk

from i18n import _, N_


class ChoiceList(Gtk.ScrolledWindow):
    """A scrolling list; clicking a line picks it."""

    def __init__(self, on_pick):
        super().__init__(vexpand=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.on_pick = on_pick
        self.titles = []
        self.rows = []
        self.picked = None
        self.box = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"],
                               valign=Gtk.Align.START, margin_bottom=6)
        self.box.connect("row-activated", lambda _b, row: self.select(row.get_index()))
        self.set_child(self.box)

    def select(self, i):
        """Pick line i."""
        self.picked = i
        self.on_pick(i)

    def show_lines(self, lines, to_chosen=True):
        """Show (title, subtitle, chosen) lines, updating in place."""
        kept = self.get_vadjustment().get_value()
        titles = [title for title, _s, _c in lines]
        if titles != self.titles:
            self.box.remove_all()
            self.rows = []
            for title in titles:
                row = Adw.ActionRow(title=GLib.markup_escape_text(title), activatable=True)
                mark = Gtk.Image(icon_name="object-select-symbolic", css_classes=["chosen-mark"])
                row.add_suffix(mark)
                self.box.append(row)
                self.rows.append((row, mark))
            self.titles = titles
        first = None
        for (row, mark), (_t, subtitle, chosen) in zip(self.rows, lines):
            row.set_subtitle(GLib.markup_escape_text(subtitle))
            mark.set_visible(chosen)
            (row.add_css_class if chosen else row.remove_css_class)("chosen")
            first = first or (row if chosen else None)
        if to_chosen and first:
            GLib.idle_add(self._scroll_to, first)
        elif not to_chosen:
            GLib.idle_add(self._keep, kept, self.picked)
        self.picked = None

    def _keep(self, kept, picked):
        """Stay where the list was, unless the line just picked is off screen."""
        adj = self.get_vadjustment()
        adj.set_value(kept)
        row = self.box.get_row_at_index(picked) if picked is not None else None
        if row:
            ok, bounds = row.compute_bounds(self.box)
            top, bottom = bounds.get_y(), bounds.get_y() + bounds.get_height()
            if ok and not (kept <= top and bottom <= kept + adj.get_page_size()):
                self._scroll_to(row)
        return False

    def _scroll_to(self, row):
        ok, bounds = row.compute_bounds(self.box)
        if ok:
            adj = self.get_vadjustment()
            adj.set_value(max(0, bounds.get_y() - adj.get_page_size() / 3))
        return False


class PasswordPair(Gtk.Box):
    """A password typed twice, with a strength meter. ready() when both match and it isn't empty."""

    # Translators: how strong a typed password is, from worst to best
    WORDS = [N_("Too weak"), N_("Weak"), N_("Fair"), N_("Good"), N_("Strong")]

    def __init__(self, what, on_change):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.on_change = on_change
        self.what = what
        rows = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"])
        self.first = Adw.PasswordEntryRow()
        self.second = Adw.PasswordEntryRow()
        for entry in (self.first, self.second):
            entry.connect("changed", self._changed)
            rows.append(entry)
        self.append(rows)
        self.meter = Gtk.LevelBar(min_value=0, max_value=4, mode=Gtk.LevelBarMode.DISCRETE)
        self.note = Gtk.Label(xalign=0, css_classes=["dim-label"], wrap=True)
        self.append(self.meter)
        self.append(self.note)
        self.refresh()

    def text(self):
        return self.first.get_text()

    def ready(self):
        return bool(self.text()) and self.text() == self.second.get_text()

    def focus(self):
        self.first.grab_focus()

    def strength(self):
        """0 to 4, and what is wrong with it if anything."""
        pw = self.text()
        if not pw:
            return 0, ""
        try:
            return min(4, 1 + pwquality.PWQSettings().check(pw) // 25), ""
        except pwquality.PWQError as e:
            return 0, e.args[1] if len(e.args) > 1 else ""

    def _changed(self, *_):
        self.refresh()
        self.on_change()

    def refresh(self):
        """The titles, the meter and the note under it, for what is typed now and the language now."""
        self.first.set_title(_(self.what))
        self.second.set_title(_("{password}, again").format(password=_(self.what)))
        level, problem = self.strength()
        self.meter.set_value(level)
        if not self.text():
            self.note.set_text(_("Type it, then type it again below."))
        elif self.second.get_text() and self.second.get_text() != self.text():
            self.note.set_text(_("The two don't match yet."))
        else:
            self.note.set_text(_("Strength: {strength}.").format(strength=_(self.WORDS[level]))
                               + (f" {problem}." if problem else ""))
