#!/usr/bin/python3 -I
"""Build check for the System Tools window: every tool is in it, on a real page, with an icon this image has and a
command that exists. Runs in the image build; opens no window."""
import importlib.machinery
import importlib.util
import shutil
import sys
from pathlib import Path

sys.path.insert(0, "/usr/lib/evenkeel-os")
import evenkeel_os_dialogs as dialogs  # noqa: E402
import evenkeel_os_guide as guide  # noqa: E402
import evenkeel_os_panel as panel  # noqa: E402

ICONS = [Path("/usr/share/icons/Adwaita"), Path("/usr/share/icons/hicolor")]
problems = []
tools = panel.tool_list()
pages = {k for k, _, _ in panel.PAGES}
icons = {t.icon for t in tools} | {i for _, _, i in panel.PAGES} | {"object-select-symbolic",
                                                                    "emblem-important-symbolic", "go-next-symbolic",
                                                                    "document-send-symbolic", "view-refresh-symbolic",
                                                                    "edit-copy-symbolic", "go-previous-symbolic"}
icons |= set(dialogs.ICONS.values()) | {"help-about-symbolic"}
for i in sorted(icons):
    if not any(next(d.rglob(f"{i}.svg"), None) for d in ICONS):
        problems.append(f"icon {i} is not in this image")
topics = {t[0] for t in guide.TOPICS}
for _, title, _, _, articles in guide.TOPICS:
    for heading, steps in articles:
        for text, show in steps:
            kind, _, key = show.partition(":")
            panel_file = Path(f"/usr/share/applications/gnome-{key}-panel.desktop")
            if show and not ((kind == "page" and key in pages) or (kind == "topic" and key in topics) or
                             (kind == "settings" and panel_file.exists())):
                problems.append(f"Guide, {title}, {heading}: {text[:40]!r} shows something that isn't there: {show}")
for t in tools:
    if t.page not in pages:
        problems.append(f"{t.title} is on a page that doesn't exist: {t.page}")
    if isinstance(t.run, list) and not shutil.which(t.run[0]):
        problems.append(f"{t.title} runs {t.run[0]}, which isn't in this image")
# Every System Tools job and every Install Package File job has a row in the window.
loader = importlib.machinery.SourceFileLoader("tools", "/usr/bin/evenkeel-os-tools")
spec = importlib.util.spec_from_loader(loader.name, loader)
tools_module = importlib.util.module_from_spec(spec)
loader.exec_module(tools_module)
jobs = {key for key, _, _, _ in tools_module.TOOLS} - {"layout", "vpn"}     # layout: its picker; vpn: Get a VPN
runs = {" ".join(t.run[:2]) for t in tools if isinstance(t.run, list)}
for job in sorted(jobs):
    if f"/usr/bin/evenkeel-os-tools {job}" not in runs:
        problems.append(f"evenkeel-os-tools {job} has no row in the window")
for job in ("install", "remove", "login", "repair", "vpn"):
    if f"/usr/bin/evenkeel-os-packages {job}" not in runs:
        problems.append(f"evenkeel-os-packages {job} has no row in the window")
for special in ("windows", "zoom"):
    if not any(t.run == special for t in tools):
        problems.append(f"the window has no {special} row")
if problems:
    print("ERROR: System Tools window check failed:")
    for p in problems:
        print(f"  - {p}")
    sys.exit(1)
print(f"System Tools window: {len(tools)} rows on {len(pages)} pages, every icon and command present")
