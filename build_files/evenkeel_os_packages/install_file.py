"""Install Package File: picking a file and installing it."""
import os
import platform
import tarfile

from evenkeel_os_ui import GUI, _, ask, choose, notify, say, short_home, user_folder, zenity
from evenkeel_os_packages import (
    app_list, boxes, common, flathub, installed, printers, reading, sources, targets, update_notes, vpn,
)


def plain_list(items):
    return "\n".join("  - " + _(i) for i in items)


def pick_file():
    found = []
    for d in (user_folder("DOWNLOAD"), user_folder("DESKTOP"), common.HOME):
        if d.is_dir():
            found += [p for p in d.iterdir() if p.is_file() and p.suffix.lower() in (".rpm", ".deb")]
    found = sorted(set(found), key=lambda p: p.stat().st_mtime, reverse=True)[:30]
    rows = [[p.name, short_home(p.parent)] for p in found]
    if not rows:
        if GUI:
            r = zenity("--file-selection", "--file-filter=" + _("Packages (.rpm, .deb)") + " | *.rpm *.deb")
            return r.stdout.strip() if r.returncode == 0 else None
        say(_("No .rpm or .deb files in Downloads. Give the file's path:  evenkeel-os-packages install FILE"))
        return None
    i = choose(_("Which file do you want to install?"), [_("File"), _("Folder")], rows)
    return str(found[i]) if i is not None else None


def install(path):
    if not path:
        path = pick_file()
        if not path:
            return 1
    path = os.path.abspath(path)
    try:
        pkg = reading.read_package(path)
    except (OSError, ValueError, tarfile.TarError, EOFError) as e:
        say(_("This file can't be installed. It may be damaged or not fully downloaded. Download it again and "
              "retry.\n\n(Details: {details})").format(details=e), "error")
        return 1
    info = reading.classify(pkg)
    title = info["title"]

    machine = platform.machine()
    fits = {"x86_64": {"rpm": {"x86_64", "noarch", "i686"}, "deb": {"amd64", "all"}},
            "aarch64": {"rpm": {"aarch64", "noarch"}, "deb": {"arm64", "all"}}}.get(machine, {})
    if fits and pkg.arch not in fits[pkg.kind]:
        if pkg.arch in ("i386", "i686"):
            say(_("This is the 32-bit version of {title}, for older computers. Download the 64-bit version instead "
                  "(often called amd64 or x86_64).").format(title=title), "warning")
        else:
            say(_("This {title} file is for a different kind of computer. Download the version for this one "
                  "(often called {names}).").format(title=title, names="amd64 or x86_64" if machine == "x86_64"
                                                    else machine), "warning")
        return 1

    company = vpn.for_package(pkg.name)
    if company:         # a VPN: from its company's own download source, so it keeps updating
        return vpn.offer_for_file(company, pkg)

    if info["needs_root"]:
        say(_("{title} can't be installed. It needs full control of the system to run, which downloaded apps don't "
              "get here.\n\nNothing was installed.").format(title=title), "warning")
        return 1

    if info["source_only"]:        # (opened again: offers its apps again, rather than "already installed")
        return sources.install_source(pkg, info)

    go_on, mode, code = installed.already_installed(pkg, info, title)
    if not go_on:
        return code
    if mode == "system-update":
        return targets.install_system(pkg, title, "a printer driver" in info["blocking"], update=True)
    if mode != "install":
        return targets.box_install(pkg, info, title, mode=mode)

    # (not for an app just chosen from a download source: the person picked that source on purpose)
    match = None if info["rules_only"] or pkg.name in sources.SOURCED else flathub.flathub_match(pkg, info)
    if match and installed.flatpak_installed(match[0]):
        app_id, name = match
        a = installed.from_bazaar(pkg, info, name, {"where": "flathub", "package": app_id, "title": name})
        if a == "ok":
            return 0
        if a != "extra":
            return 1
        match = None
    if match:
        app_id, name = match
        answer = ask(_("{name} is in Bazaar, the app store (Flathub).\n\nRecommended: Use Flathub. It updates by "
                       "itself and is made for this kind of system.\n\nOr Use the file: installs your download.")
                     .format(name=name) + " " + update_notes.file_note(pkg, info),
                     ok=_("Use Flathub"), cancel=_("Cancel"), extra=_("Use the file"))
        if answer is None:
            return 1
        if answer == "ok":
            return flathub.install(app_id, name)

    if info["rules_only"]:
        if ask(_("{title} only lets your account use a device.\n\nAdd it: needs your password.").format(title=title),
               ok=_("Add it")) != "ok":
            return 1
        ok, out = update_notes.add_rules(pkg, info)
        if not ok:
            say(_("The device rule wasn't added, so the device may not work.\n\n{details}").format(details=out),
                "error")
            return 1
        app_list.remember({"title": title, "package": pkg.name, "where": "rules", "rules": True})
        notify(_("{title} is installed.").format(title=title))
        say(_("{title} is installed. Unplug the device and plug it back in.").format(title=title))
        return 0

    if info["blocking"]:
        reasons = plain_list(info["blocking"])
        printer = "a printer driver" in info["blocking"]
        if printer:
            choice = printers.try_driverless(title, pkg.kind)
            if choice != "driver":
                return 0 if choice == "printers" else 1
        if pkg.kind == "deb" and printer:
            who = printers.maker(pkg)
            site = _("{maker}'s support site").format(maker=who) if who else _("the printer maker's support site")
            if ask(_("{title} is a printer driver made for Ubuntu and Debian (.deb). This system takes printer "
                     "drivers only as .rpm files.\n\nWhat to do:\n  1. Go to {site} and find the driver for your "
                     "printer.\n  2. When it asks for your system, choose the .rpm version (it may be called "
                     "Fedora, Red Hat or RPM).\n  3. Open that .rpm file here.\n\nOr try your printer without a "
                     "driver first.").format(title=title, site=site),
                   ok=_("Open Printers"), cancel=_("Close")) == "ok":
                printers.open_printers()
            return 1
        if pkg.kind == "deb":
            say(_("{title} can't be installed from this file. It has:\n{reasons}\n\n"
                  "These have to go on the system, and the system only takes .rpm files. "
                  "Look for {title} as an .rpm for Fedora {version}, or in Bazaar, the app store.")
                .format(title=title, reasons=reasons, version=common.fedora_version()), "warning")
            return 1
        if ask(_("{title} has to go on the system. It has:\n{reasons}\nThese can't work in a box.\n\n"
                 "Add to the system: everything works. Needs your password and a restart. You can remove it any "
                 "time in Wheelhouse, Apps, Remove apps.").format(title=title, reasons=reasons),
               ok=_("Add to the system")) != "ok":
            return 1
        return targets.install_system(pkg, title, printer, services=info["turns_on"])

    box = common.BOXES[pkg.kind]
    new_box = not boxes.box_exists(box["name"])
    size, first = None, ""
    if new_box:
        first, size = boxes.first_time(pkg.kind)
        first = " " + first
    setup = _("Set up and install") if new_box else _("Install")
    rule = "\n\n" + _("It also has a device rule. That goes on the system, so you will be asked for your password.") \
        if info["safe_rules"] else ""
    if info["notes"] and pkg.kind == "rpm":
        # parts of it would not work in a box: the system is the recommended choice
        answer = ask(_("Install {title}\n\nRecommended: Add to the system. In a box, these parts of {title} won't "
                       "work:\n{notes}\nOn the system, everything works. Needs your password and a "
                       "restart.\n\nOr {setup}: puts it in a separate box. It's easier to remove, but those parts "
                       "won't work.").format(title=title, notes=plain_list(info["notes"]), setup=setup) + first + rule,
                     ok=_("Add to the system"), extra=setup)
        if answer == "ok":
            return targets.install_system(pkg, title, services=info["turns_on"])
        if answer != "extra":
            return 1
    elif info["notes"]:
        # a .deb cannot go on the system: the box is the only choice, said plainly
        if ask(_("Install {title}\n\nIn a box, these parts of {title} won't work:\n{notes}\n"
                 "A .deb file can't go on the system. For everything to work, look for {title} as an .rpm file or in "
                 "Bazaar, the app store.\n\n{setup}: puts it in a box anyway, without those parts.")
               .format(title=title, notes=plain_list(info["notes"]), setup=setup) + first + rule,
               ok=setup) != "ok":
            return 1
    elif ask(_("Install {title}\n\n{setup}: puts it in a separate box. Your system isn't changed, and Remove Apps "
               "takes it out cleanly.").format(title=title, setup=setup) + first + rule, ok=setup) != "ok":
        return 1
    file_mb = pkg.path.stat().st_size // 1_000_000
    if new_box:
        if not boxes.room_for(boxes.setup_need(size) + 3 * file_mb):
            return 1
        if not boxes.setup_box(pkg.kind, size):
            return 1
    elif not boxes.room_for(3 * file_mb + 500):
        return 1
    return targets.box_install(pkg, info, title)
