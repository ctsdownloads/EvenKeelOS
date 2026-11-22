#!/usr/bin/python3 -I
"""Build check: tools started from System Tools show their windows inside it.

1. No tool runs zenity itself: every window goes through evenkeel_os_ui.DIALOGS or the scripts' $zenity, which
   become evenkeel-os-dialog when System Tools starts the tool.
2. evenkeel-os-dialog answers like zenity (exit code and output) for each kind of window, against a stand-in for the
   System Tools window.

Usage: check-dialogs.py BUILD_FILES_FOLDER DIALOG_PROGRAM
"""
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

folder, program = Path(sys.argv[1]), sys.argv[2]
problems = []

# 1. zenity only through DIALOGS / $zenity
ALLOWED = re.compile(r'shutil\.which\("zenity"\)|else "zenity"|^zenity=zenity;|command -v zenity|HELPERS|'
                     r'HELPER_CHECK|^\s*#|"""|zenity\'s|^from evenkeel_os_ui import')
files = [folder / "evenkeel_os_ui.py", folder / "evenkeel-os-tools", folder / "evenkeel-os-update",
         folder / "evenkeel-os-codecs", *sorted((folder / "evenkeel_os_packages").glob("*.py"))]
for f in files:
    for n, line in enumerate(f.read_text().splitlines(), 1):
        if re.search(r'(?<![\w$"-])zenity(?![\w=(\'])|"zenity"', line) and not ALLOWED.search(line):
            problems.append(f"{f.name}:{n} runs zenity directly, so its window would open outside System Tools")

# 2. answers, with a stand-in window that answers each request as told
answers = []


def serve(server):
    while True:
        try:
            conn, _ = server.accept()
        except OSError:
            return
        with conn, conn.makefile("rw", encoding="utf-8") as f:
            req = json.loads(f.readline())
            answer = answers.pop(0)
            if req["kind"] == "progress":
                lines = []
                while not lines or not lines[-1].get("end"):
                    lines.append(json.loads(f.readline() or '{"end": true}'))
                answer = answer(req, lines) if callable(answer) else answer
            elif callable(answer):
                answer = answer(req, [])
            f.write(json.dumps(answer) + "\n")
            f.flush()


def ask(args, answer, stdin=""):
    answers.append(answer)
    r = subprocess.run([program, *args], input=stdin, capture_output=True, text=True,
                       env={**os.environ, "EVENKEEL_OS_PANEL": sock}, timeout=20)
    return r.returncode, r.stdout


with tempfile.TemporaryDirectory() as tmp:
    sock = os.path.join(tmp, "dialogs")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock)
    server.listen(4)
    threading.Thread(target=serve, args=(server,), daemon=True).start()
    q = ["--question", "--title=T", "--ok-label=Go", "--cancel-label=Stop", "--extra-button=More", r"--text=a\nb"]
    seen = {}

    def keep(req, _lines):
        seen.update(req)
        return {"button": "ok"}
    def progress(_req, lines):
        return {"button": "ok"} if lines == [{"line": "# Step one"}, {"line": "50"}, {"end": True}] else {}
    checks = [
        ("question, OK", ask(q, keep), (0, "")),
        ("question, Cancel", ask(q, {"button": "cancel"}), (1, "")),
        ("question, extra button", ask(q, {"button": "extra"}), (1, "More\n")),
        ("message", ask(["--warning", "--no-markup", "--text=x"], {"button": "ok"}), (0, "")),
        ("list, a row picked", ask(["--list", "--print-column=1", "--hide-column=1", "--column=n", "--column=Name",
                                    "--column=Where"], {"button": "ok", "row": 1}, "0\nA\nhere\n1\nB\nthere\n"),
         (0, "1\n")),
        ("list, cancelled", ask(["--list", "--column=n", "--column=Name"], {"button": "cancel"}, "0\nA\n"), (1, "")),
        ("password", ask(["--password", "--text=Type it"], {"button": "ok", "value": "s3cret"}), (0, "s3cret\n")),
        ("file", ask(["--file-selection", "--file-filter=Packages | *.rpm"], {"button": "ok", "value": "~/a.rpm"}),
         (0, "~/a.rpm\n")),
        ("progress, to the end", ask(["--progress", "--pulsate", "--auto-close", "--no-cancel", "--text=Working"],
                                     progress, "# Step one\n50\n"), (0, "")),
        ("unknown option", ask(["--question", "--timeout=5"], {"button": "ok"}), (2, "")),
    ]
    answers.clear()
    # System Tools closed: the tool gets a window of its own from zenity, as before
    Path(tmp, "zenity").write_text('#!/bin/sh\necho "zenity $*"\n')
    Path(tmp, "zenity").chmod(0o755)
    r = subprocess.run([program, "--info", "--text=x"], capture_output=True, text=True, timeout=20,
                       env={**os.environ, "EVENKEEL_OS_PANEL": os.path.join(tmp, "gone"),
                            "PATH": f"{tmp}:{os.environ.get('PATH', '')}"})
    checks.append(("System Tools closed", (r.returncode, r.stdout), (0, "zenity --info --text=x\n")))
    for name, got, want in checks:
        if got != want:
            problems.append(f"evenkeel-os-dialog, {name}: exit code and output {got}, not {want}")
    if seen.get("text") != "a\nb" or seen.get("ok-label") != "Go" or seen.get("title") != "T":
        problems.append(f"evenkeel-os-dialog sent the window the wrong question: {seen}")
    server.close()

if problems:
    print("ERROR: tool windows would not show inside System Tools:", *problems, sep="\n  ")
    sys.exit(1)
print(f"Tool windows show inside System Tools: {len(files)} files checked, {len(checks)} answers right")
