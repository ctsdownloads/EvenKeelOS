"""Progress windows, running steps, and explaining failures."""
import html
import os
import re
import signal
import subprocess
import time

import evenkeel_os_ui as ui
from evenkeel_os_ui import GUI, _, ask, notify, say
from evenkeel_os_packages import common


CANCELLED = False      # set by run_steps when the person pressed Cancel
BUSY = common.CACHE / ".busy"   # what this run is doing, for a second window that has to wait for it


def mark_busy(text):
    BUSY.write_text(text)


def run_steps(text, steps, cancel=False):
    """Run (label, command) steps with a progress window; True if all worked. Output goes to the log."""
    global CANCELLED
    CANCELLED = False
    steps = [st if isinstance(st, tuple) else (text, st) for st in steps]
    common.CACHE.mkdir(parents=True, exist_ok=True)
    if common.LOG.exists() and common.LOG.stat().st_size > 2_000_000:     # keep the log from growing without end
        common.LOG.write_bytes(common.LOG.read_bytes()[-500_000:])
    log = open(common.LOG, "a")
    log.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} {text}\n")
    mark_busy(text)
    bar = None
    if GUI:
        mode = ["--pulsate"] if len(steps) == 1 else []
        bar = subprocess.Popen([ui.DIALOGS, f"--title={ui.TITLE}", "--width=520",
                                "--progress", *mode, "--auto-close",
                                *([] if cancel else ["--no-cancel"]), f"--text={html.escape(text)}"],
                               stdin=subprocess.PIPE, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print(text)

    def show(*lines):
        if bar:
            ui.feed(bar, *lines)

    ok = True
    for i, (label, cmd) in enumerate(steps):
        show(*([str(int(100 * i / len(steps)))] if len(steps) > 1 else []), "# " + html.escape(label))
        if not bar:
            print("  " + label)
        log.write("$ " + " ".join(cmd) + "\n")
        log.flush()
        try:
            # English output, in any language: explain() reads the log for the usual reasons a step fails.
            proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                    start_new_session=True, env={**os.environ, "LC_ALL": "C.UTF-8"})
        except OSError as e:
            log.write(f"{e}\n")
            ok = False
            break
        began, shown = time.time(), 0
        while proc.poll() is None:
            time.sleep(1)
            if bar and bar.poll() is not None:          # the window was closed: Cancel
                if cancel:
                    CANCELLED = True
                    if proc.poll() is None:
                        os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait()
                    break
                bar = None
            mins = int(time.time() - began) // 60
            if mins > shown:
                shown = mins
                show("# " + html.escape(_("{label}  ({mins} min so far)").format(label=label, mins=mins)))
        if CANCELLED or proc.returncode != 0:
            ok = False
            break
    log.close()
    if bar:
        ui.finish(bar)
    return ok


def log_tail(n=4000):
    try:
        with open(common.LOG, errors="replace") as f:
            text = f.read()
        return text[text.rfind("\n=== "):][-n:] if "\n=== " in text else text[-n:]
    except OSError:
        return ""


def explain(log):
    """The usual reasons an install fails, in plain words, or ''."""
    low = log.lower()
    m = re.search(r"nothing provides ([^\s]+)", low)
    if m:
        return _("It needs {name}, which Fedora {version} does not have. "
                 "It may be made for a different Fedora version.").format(name=m.group(1),
                                                                          version=common.fedora_version())
    m = re.search(r"depends: ([^\s]+)[^\n]*but (it is not installable|it is not going to be installed|[^\n]*is to be "
                  r"installed)", low)
    if m or "unmet dependencies" in low:
        if m:
            return _("It needs {name}, which the Ubuntu box (Ubuntu 24.04) does not have. "
                     "It may be made for a newer or older Ubuntu.").format(name=m.group(1))
        return _("It needs parts that the Ubuntu box (Ubuntu 24.04) does not have. "
                 "It may be made for a newer or older Ubuntu.")
    if "no space left on device" in low:
        return _("The disk is full. Free some space, then try again.")
    if re.search(r"could not resolve|temporary failure resolving|name or service not known|network is unreachable|"
                 r"connection timed out|curl error|failed to download|cannot download|tls handshake", low):
        return _("It could not reach the internet. Check the connection, then try again.")
    if re.search(r"conflicts with file from package|file [^\n]* conflicts", low):
        return _("It would replace a file that belongs to the system, so it was not added.")
    if re.search(r"different architecture|wrong architecture|incompatible architecture", low):
        return _("It is made for a different kind of processor than this computer has.")
    if re.search(r"not authorized|accessdenied|authentication (failed|dismissed)|request dismissed", low):
        return _("The administrator password was not given, so nothing was changed.")
    if re.search(r"no such container|error: container .* does not exist|cannot find container", low):
        return _("The box is missing or broken.")
    return ""


def failed(what, offer=None, reason=""):
    """Say that something did not work, in plain words when the reason is a usual one. offer: (button, action)."""
    log = log_tail()
    reason = reason or explain(log)
    if not reason:
        lines = [line for line in log.splitlines() if line.strip() and not line.startswith(("===", "$ "))]
        reason = _("The last lines of the log:") + "\n" + "\n".join(lines[-4:]) if lines else ""
    notify(_("{what} did not work.").format(what=what))
    text = _("{what} did not work.\n\n{reason}\n\nThe full details are in {log}").format(
        what=what, reason=reason, log=common.LOG)
    if offer:
        if ask(text, ok=offer[0], cancel=_("Close")) == "ok":
            return offer[1]()
        return 1
    say(text, "error")
    return 1
