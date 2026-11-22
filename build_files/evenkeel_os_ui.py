"""Windows, notices and disk sizes shared by System Tools and Install Package File."""

import math
import os
import shutil
import subprocess
from pathlib import Path

GUI = bool(shutil.which("zenity")) and bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))
# Started from System Tools: windows show inside it, through the same options and answers as zenity's.
IN_PANEL = bool(os.environ.get("EVENKEEL_OS_PANEL"))
DIALOGS = "/usr/libexec/evenkeel-os-dialog" if IN_PANEL else "zenity"
# For apps and file windows a tool opens: what they start later opens its own windows, not System Tools'.
LAUNCH_ENV = {k: v for k, v in os.environ.items() if k != "EVENKEEL_OS_PANEL"}

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


def ask(text, ok="Yes", cancel="Cancel", extra=None, title=None):
    """'ok', 'extra' or None."""
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
    text += "\n\nRecommended: Restart now. Or Later, if you're in the middle of something."
    if rest:
        text += "\n\n" + rest
    if ask(text, ok="Restart now", cancel="Later") == "ok":
        subprocess.run(["systemctl", "reboot"])


def human(mb):
    """'450 MB' or '1.2 GB'."""
    return f"{mb / 1000:.1f} GB" if mb >= 1000 else f"{math.ceil(mb)} MB"


def free_mb(where=None):
    try:
        return shutil.disk_usage(where or Path.home()).free // 1_000_000
    except OSError:
        return None
