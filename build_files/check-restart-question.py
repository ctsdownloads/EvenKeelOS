#!/usr/bin/python3 -I
"""Build check: the window before an automatic restart gives each answer the startup check expects.

Runs Wheelhouse's restart-question against a made-up zenity and pkexec: no window opens and nothing restarts.
"""
import importlib.machinery
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = sys.argv[1] if len(sys.argv) > 1 else "/usr/bin/evenkeel-os-tools"
LIB = sys.argv[2] if len(sys.argv) > 2 else "/usr/lib/evenkeel-os"
os.environ["WAYLAND_DISPLAY"] = "wayland-0"     # a desktop, so the window is shown (to the made-up zenity)
sys.path.insert(0, LIB)
import evenkeel_os_health as health  # noqa: E402

loader = importlib.machinery.SourceFileLoader("tools", TOOLS)
spec = importlib.util.spec_from_loader("tools", loader)
tools = importlib.util.module_from_spec(spec)
loader.exec_module(tools)
real_run = subprocess.run
if str(tools.RESTART_QUESTION) != health.QUESTION:
    sys.exit(f"ERROR: restart question: the window reads {tools.RESTART_QUESTION}, the check writes {health.QUESTION}")
tools.RESTART_QUESTION = Path(tempfile.mkdtemp(), "restart-question")


class Fake:
    """zenity answers in turn (exit codes) and pkexec's exit codes; what each window was given."""

    def __init__(self, answers, passwords=()):
        self.answers = list(answers)
        self.passwords = list(passwords)
        self.windows = []
        self.asked = 0

    def zenity(self, *args, title=None, **_):
        self.windows.append(dict(a[2:].split("=", 1) for a in args if "=" in a) | {"title": title})
        if not self.answers:
            sys.exit(f"ERROR: restart question: the window opened again after the last answer: {self.windows[-1]}")
        return subprocess.CompletedProcess(args, self.answers.pop(0), "", "")

    def run(self, cmd, *args, **kw):
        if cmd[0] == "pkexec":
            if cmd[1:] != [tools.ADMIN, "keep-update"]:
                sys.exit(f"ERROR: restart question: Keep runs {cmd}")
            self.asked += 1
            if not 60 <= kw.get("timeout", 0) <= 120:
                sys.exit(f"ERROR: restart question: the password window gets {kw.get('timeout')} seconds")
            rc = self.passwords.pop(0)
            if rc == "slow":
                raise subprocess.TimeoutExpired(cmd, kw["timeout"])
            return subprocess.CompletedProcess(cmd, rc)
        return real_run(cmd, *args, **kw)


def ask(kind, start, answers, passwords=(), names=("Sound (snd_hda_intel)",)):
    f = Fake(answers, passwords)
    tools.ui.zenity = f.zenity
    tools.subprocess.run = f.run
    tools.notify = lambda text: None
    tools.RESTART_QUESTION.write_text("".join(f"{n}\n" for n in ("b00t", *names)))
    try:
        rc = tools.restart_question(kind, start)
    finally:
        tools.subprocess.run = real_run
    if f.answers or f.passwords:
        sys.exit(f"ERROR: restart question {kind} {start}: answers left over {f.answers} {f.passwords}")
    return rc, f


def die(msg):
    sys.exit(f"ERROR: restart question: {msg}")


if tools.RESTART_WAIT != health.COUNTDOWN:
    die(f"the window counts down {tools.RESTART_WAIT} seconds, the startup check {health.COUNTDOWN}")
if set(tools.AFTER_LOGIN_TESTS) != set(health.TRIAL_TESTS):
    die(f"Wheelhouse's after-login tests {tools.AFTER_LOGIN_TESTS} aren't the trial's {health.TRIAL_TESTS}")
# Every after-login test: its own name, what broke, Restart now or Not yet, no countdown but for Graphics.
for kind, name, _ in tools.ROLLBACK_TESTS:
    if kind not in tools.AFTER_LOGIN_TESTS:
        if ask(kind, "first", [])[0] != 1:
            die(f"{kind} breaks the start before the desktop, but has a window")
        continue
    for start in ("first", "last"):
        rc, f = ask(kind, start, [0])
        w = f.windows[0]
        if rc != 0 or (w["ok-label"], w["cancel-label"]) != ("Restart now", "Not yet"):
            die(f"{kind} {start}: exit {rc}, buttons {w['ok-label']!r} {w['cancel-label']!r}")
        if not w["text"].startswith(f"{name}: the test is working.") or "• Sound (snd_hda_intel)" not in w["text"]:
            die(f"{kind} {start}: the window doesn't name the test or what broke: {w['text']!r}")
        if ("timeout" in w) != (kind == "graphics"):
            die(f"{kind} {start}: countdown {w.get('timeout')!r}")
        if ("back on this version, and the test copy is removed" in w["text"]) != (start == "last"):
            die(f"{kind} {start}: the window says the wrong next step")
# Not yet holds the restart: no countdown after it, even for Graphics; Esc opens the window again.
for kind in ("sound", "graphics"):
    rc, f = ask(kind, "first", [4, 9, 4, 0])
    if rc != 0 or len(f.windows) != 4 or any("timeout" in w for w in f.windows[1:]):
        die(f"{kind}: Not yet, Esc, Not yet, Restart now gave exit {rc}, windows {f.windows}")
    if not all(w["text"].startswith("Restart now is waiting") for w in f.windows[1:]):
        die(f"{kind}: after Not yet the window doesn't say Restart now is waiting")
    if f.windows[1]["text"].count("Restart now is waiting") != 1 or f.windows[3]["text"] != f.windows[1]["text"]:
        die(f"{kind}: Not yet twice says Restart now is waiting twice")
# Real problems: Restart now (or Go back now), Keep with the password, the countdown.
for kind, other in (("update", "Keep this update"), ("boot-options", "Keep these options")):
    for start, ok in (("first", "Restart now"), ("last", "Go back now")):
        rc, f = ask(kind, start, [0])
        w = f.windows[0]
        if rc != 0 or (w["ok-label"], w["cancel-label"]) != (ok, other) or not 0 < int(w["timeout"]) <= 120:
            die(f"{kind} {start}: exit {rc}, buttons {w['ok-label']!r} {w['cancel-label']!r}, "
                f"timeout {w.get('timeout')}")
        if "• Sound (snd_hda_intel)" not in w["text"] or "No answer in 2 minutes" not in w["text"]:
            die(f"{kind} {start}: the window doesn't list what broke or the countdown: {w['text']!r}")
    rc, f = ask(kind, "first", [5])
    if rc != 0:
        die(f"{kind}: no answer in time gave exit {rc}, not a restart")
    rc, f = ask(kind, "last", [4, 4], passwords=[126, 0])
    if rc != 3 or f.asked != 2 or not 0 < int(f.windows[1]["timeout"]) <= int(f.windows[0]["timeout"]):
        die(f"{kind}: Keep, password refused, Keep, password given gave exit {rc} ({f.asked} password asks)")
    rc, f = ask(kind, "first", [4, 0], passwords=[127])
    if rc != 0:
        die(f"{kind}: Keep without the password, then Restart now, gave exit {rc}")
    rc, f = ask(kind, "first", [4], passwords=["slow"])
    if rc != 0:
        die(f"{kind}: the password window left open past the countdown gave exit {rc}, not a restart")
# Any other way the window ends counts as no window: the startup check restarts as before.
for answers, what in (([9, 9, 9], "closing at once three times"), ([1], "no screen to open on"),
                      ([255], "zenity failing")):
    if ask("update", "first", answers)[0] != 1:
        die(f"{what} isn't taken as a window that can't show")
if ask("no-such-kind", "first", [])[0] != 1:
    die("an unknown kind gets a window")
many = [f"Thing {i}" for i in range(20)]
w = ask("update", "first", [0], names=many)[1].windows[0]
if "Thing 11" not in w["text"] or "Thing 12" in w["text"] or "and 8 more" not in w["text"]:
    die("a long list of what broke isn't cut to 12 and a count")
print("Restart question: every after-login test and real problem gives its answer; Not yet holds, Keep asks for "
      "the password, no answer in 2 minutes restarts")
