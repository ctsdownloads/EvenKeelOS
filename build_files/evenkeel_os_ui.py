"""Windows, notices and disk sizes shared by Wheelhouse and Install Package File."""

import gettext
import locale
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

GUI = bool(shutil.which("zenity")) and bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))
# Started from Wheelhouse: windows show inside it, through the same options and answers as zenity's.
IN_PANEL = bool(os.environ.get("EVENKEEL_OS_PANEL"))
DIALOGS = "/usr/libexec/evenkeel-os-dialog" if IN_PANEL else "zenity"
# For apps and file windows a tool opens: what they start later opens its own windows, not Wheelhouse's.
LAUNCH_ENV = {k: v for k, v in os.environ.items() if k != "EVENKEEL_OS_PANEL"}

_translation = gettext.translation("evenkeel-os", fallback=True)
_ = _translation.gettext
ngettext = _translation.ngettext


try:
    TIME_LOCALE = locale.setlocale(locale.LC_TIME, "")
except locale.Error:
    TIME_LOCALE = locale.setlocale(locale.LC_TIME, "C")     # a region the system has no data for: English
# Date patterns follow the Formats region in Settings, like the month and day names they hold.
_dates = gettext.translation("evenkeel-os", languages=[TIME_LOCALE], fallback=True).gettext
HAS_AM_PM = bool(time.strftime("%p", time.struct_time((2000, 1, 1, 13, 0, 0, 5, 1, -1))))


def clock_24h():
    """Whether the clock in Settings is set to 24-hour (as the top bar shows it)."""
    try:
        r = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "clock-format"],
                           capture_output=True, text=True)
    except OSError:
        return True
    return r.stdout.strip() != "'12h'"


def date_text(t, with_time=False):
    """A date (a time.struct_time) in the person's language and order, with the time if asked."""
    if not with_time:
        # Translators: a date: month and day ("November 26"). Uses strftime codes.
        fmt = _dates("%B %-d")
    elif clock_24h() or not HAS_AM_PM:     # a region with no AM/PM words writes times as 24-hour
        # Translators: a date and a 24-hour time ("November 26, 19:02"). Uses strftime codes.
        fmt = _dates("%B %-d, %H:%M")
    else:
        # Translators: a date and a 12-hour time ("November 26, 7:02 PM"). Uses strftime codes.
        fmt = _dates("%B %-d, %-I:%M %p")
    return time.strftime(fmt, t)


def day_text(t):
    """A day (a time.struct_time) with its weekday, in the person's language and order."""
    # Translators: a weekday and date ("Thursday, November 26"). Uses strftime codes.
    return time.strftime(_dates("%A, %B %-d"), t)


def N_(text):
    """Marks text to translate where it is written down; _() translates it where it is shown."""
    return text


TITLE = ""      # set by each program
ICON = ""


def zenity(*args, stdin=None, title=None, width=520):
    return subprocess.run([DIALOGS, f"--title={title or TITLE}", f"--width={width}", *args], input=stdin,
                          capture_output=True, text=True)


def notify(text):
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", f"--app-name={TITLE}", f"--icon={ICON}", TITLE, text], capture_output=True)


def say(text, kind="info", title=None):
    if GUI:
        zenity(f"--{kind}", "--no-markup", f"--text={text}", title=title)
    else:
        print(text)


def ask(text, ok=None, cancel=None, extra=None, title=None):
    """'ok', 'extra' or None."""
    ok, cancel = ok or _("Yes"), cancel or _("Cancel")
    if GUI:
        args = ["--question", "--no-markup", f"--text={text}", f"--ok-label={ok}", f"--cancel-label={cancel}"]
        if extra:
            args.append(f"--extra-button={extra}")
        r = zenity(*args, title=title)
        if r.returncode == 0:
            return "ok"
        return "extra" if extra and r.stdout.strip() == extra else None
    print(text)
    print(f"  1) {ok}" + (f"\n  2) {extra}" if extra else "") + f"\n  Enter) {cancel}")
    try:
        return {"1": "ok", "2": "extra" if extra else None}.get(input("> ").strip())
    except EOFError:
        return None


def feed(bar, *lines):
    """Send lines to a zenity progress window; False once the person has closed it."""
    try:
        bar.stdin.write("".join(line + "\n" for line in lines))
        bar.stdin.flush()
        return True
    except BrokenPipeError:
        return False


def finish(bar):
    """Fill a zenity progress window and wait for it to close."""
    if bar.poll() is None and feed(bar, "100"):
        bar.stdin.close()
    bar.wait()


def choose(text, columns, rows, width=520, height=420):
    """Pick one row; its index or None."""
    if not rows:
        return None
    if GUI:
        # column 1 (hidden) is the row's index, printed back when it is picked
        args = ["--list", f"--text={text}", f"--height={height}", "--print-column=1", "--hide-column=1",
                "--column=n", *[f"--column={c}" for c in columns]]
        cells = []
        for i, row in enumerate(rows):
            cells += [str(i), *row]
        r = zenity(*args, stdin="\n".join(cells) + "\n", width=width)
        out = r.stdout.strip().split("|")[0]
        return int(out) if r.returncode == 0 and out.isdigit() else None
    print(text)
    for i, row in enumerate(rows, 1):
        print(f"  {i}) " + "   ".join(row))
    try:
        n = input("> ").strip()
    except EOFError:
        return None
    return int(n) - 1 if n.isdigit() and 0 < int(n) <= len(rows) else None


def offer_restart(text, rest=""):
    """text: what happened; rest: what comes after the restart."""
    text += "\n\n" + _("Recommended: Restart now. Or Later, if you're in the middle of something.")
    if rest:
        text += "\n\n" + rest
    if ask(text, ok=_("Restart now"), cancel=_("Later")) == "ok":
        subprocess.run(["systemctl", "reboot"])


def human(mb):
    """'450 MB' or '1.2 GB'."""
    return f"{mb / 1000:.1f} GB" if mb >= 1000 else f"{math.ceil(mb)} MB"


def free_mb(where=None):
    try:
        return shutil.disk_usage(where or Path.home()).free // 1_000_000
    except OSError:
        return None
