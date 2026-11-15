"""Installing into a box or onto the system."""
import json
import platform
import shlex
import shutil
import subprocess

from evenkeel_os_ui import ask, notify, offer_restart, say
from evenkeel_os_packages import (
    after_restart, app_list, boxes, common, hwrules, install_file, installed, launchers, sources,
    update_notes, windows,
)


def staged_copy(pkg):
    common.CACHE.mkdir(parents=True, exist_ok=True)
    dest = common.CACHE / pkg.path.name
    if pkg.path.resolve() != dest.resolve():
        shutil.copyfile(pkg.path, dest)
    return dest


def box_install(pkg, info, title, quiet=False, mode="install"):
    """Install into the existing box; mode is install, reinstall, update or older."""
    label = common.BOXES[pkg.kind]["label"]
    box = common.BOXES[pkg.kind]["name"]
    f = str(staged_copy(pkg))
    boxes.ensure_helpers(pkg.kind, quiet=quiet)      # boxes made before the helpers were part of the setup
    rules_before = hwrules.box_rules(box)
    repos_before = update_notes.box_repos(box, pkg.kind)
    doing = {"reinstall": "Reinstalling", "update": "Updating", "older": "Installing the older version of"
             }.get(mode, "Installing")
    if pkg.kind == "rpm":
        verb = {"reinstall": "reinstall", "older": "downgrade"}.get(mode, "install")
        steps = [(f"{doing} {title}", boxes.in_box(box, "sudo", "dnf", "-y", verb, f))]
    else:
        extra = {"reinstall": ["--reinstall"], "older": ["--allow-downgrades"]}.get(mode, [])
        steps = [("Getting Ubuntu's list of packages", boxes.in_box(box, "sudo", "apt-get", "update")),
                 (f"{doing} {title}",
                  boxes.in_box(box, "sudo", "env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y", *extra, f))]
    if not windows.run_steps(f"{doing} {title} in the {label}.", steps):
        if quiet:
            return 1
        if not boxes.box_works(box):
            def repair_then_install():
                if boxes.repair(pkg.kind, confirm=False) != 0:
                    return 1
                return box_install(pkg, info, title)
            return windows.failed(f"Installing {title}", offer=("Repair the box", repair_then_install),
                          reason=f"The {label} isn't working.\n\nRecommended: Repair the box. It rebuilds the box, "
                                 f"puts your apps back, then installs {title}. Your files aren't touched.")
        return windows.failed(f"Installing {title}")
    apps, bins = launchers.export(box, info)
    hwrules.new_box_rules(box, rules_before, info)
    old = next((r for r in app_list.load() if r["where"] == box and r["package"] == pkg.name), {})
    # Updates: the package (or its install script, as Chrome's and VS Code's do) added a download source
    updates = update_notes.adds_source(pkg) or bool(set(update_notes.box_repos(box, pkg.kind)) - set(repos_before)) or \
        bool(old.get("updates")) or pkg.name in sources.SOURCED
    entry = {"title": title, "package": pkg.name, "where": box, "apps": apps, "bins": bins,
             "rules": bool(old.get("rules")), "file": f, "version": pkg.evr, "updates": updates}
    if info.get("source_only"):
        entry["source"] = True
    app_list.remember(entry)
    extra = ""
    if quiet:
        return 0
    if info["safe_rules"]:
        ok, out = update_notes.add_rules(pkg, info)
        if ok:
            entry["rules"] = True
            app_list.remember(entry)
            extra = "\n\nUnplug the device and plug it back in so it works."
        else:
            extra = f"\n\nThe device rule wasn't added, so the device may not work.\n{out}"
    if info["notes"]:
        extra += "\n\nIn the box, these won't work:\n" + install_file.plain_list(info["notes"])
    if apps:
        where = "Find it in Show Apps."
    elif bins:
        where = "It is a command-line tool, so it has no window in Show Apps."
    else:
        where = "It has no app of its own; other apps in the box use it."
    done = {"reinstall": "is reinstalled", "update": f"is updated to version {installed.plain_version(pkg.evr)}",
            "older": f"is now version {installed.plain_version(pkg.evr)}"}.get(mode, "is installed")
    notify(f"{title} {done}.")
    say(f"{title} {done}. {where}{extra}\n\n{update_notes.UPDATES_YES if updates else update_notes.UPDATES_NO}")
    return 0


def staged_system():
    r = subprocess.run(["rpm-ostree", "status", "--json"], capture_output=True, text=True)
    try:
        return any(d.get("staged") for d in json.loads(r.stdout)["deployments"])
    except (ValueError, KeyError):
        return False


def fedora_package_version(name):
    """Version of `name` in Fedora's own repos, or '' if absent or unknown."""
    dnf = shutil.which("dnf5") or shutil.which("dnf")
    if not dnf:
        return ""
    out = common.CACHE / "fedora-query.txt"
    out.unlink(missing_ok=True)
    query = (f"{shlex.quote(dnf)} -q repoquery --repo=fedora,updates --latest-limit=1 "
             f"--arch={platform.machine()},noarch --queryformat='%{{version}}-%{{release}}\\n' "
             f"{shlex.quote(name)} > {shlex.quote(str(out))}")
    if not windows.run_steps(f"Checking whether Fedora has {name}.", [["timeout", "180", "sh", "-c", query]]):
        return ""
    try:
        return next((l.strip() for l in out.read_text().splitlines() if l.strip()), "")
    except OSError:
        return ""


def install_from_fedora(pkg, title, printer, version):
    """Add the package to the system from Fedora's repos by name, so System Update keeps it up to date."""
    what = f"Adding {title} to the system from Fedora. This can take a few minutes."
    notify(f"Adding {title} to the system from Fedora. A progress window shows it.")
    if not windows.run_steps(what, [["rpm-ostree", "install", "--idempotent", pkg.name]]):
        windows.failed(f"Adding {title} to the system")
        return 1
    app_list.remember({"title": title, "package": pkg.name, "where": "system", "from_fedora": True,
              "version": version})
    after_restart.save_pending([e for e in after_restart.pending() if e["package"] != pkg.name] + [{"title": title, "package": pkg.name,
                                                                  "printer": printer}])
    after = "After the restart, you will be asked to add your printer." if printer else \
        "After the restart, you'll get a message when it's ready."
    notify(f"{title} is installed. Restart to use it.")
    offer_restart(f"{title} is installed. Restart to start using it.", f"{after}\n\nUpdates: {update_notes.UPDATES_FEDORA}")
    return 0


def install_system(pkg, title, printer=False, update=False):
    if not update and pkg.kind == "rpm":
        version = fedora_package_version(pkg.name)
        if version:
            newer = "\n\nYour file is newer than Fedora's. Use the file only if you need that newer version now." \
                if installed.compare("rpm", pkg.evr, version) > 0 else ""
            answer = ask(f"Fedora has {title}.\n\nRecommended: Install from Fedora. System Update keeps it up to "
                         f"date.\n\nOr Use the file: installs your download. It never updates.{newer}",
                         ok="Install from Fedora", cancel="Cancel", extra="Use the file")
            if answer == "ok":
                return install_from_fedora(pkg, title, printer, version)
            if answer != "extra":
                return 1
    f = str(staged_copy(pkg))
    if update:      # the layered file is swapped for the newer one in one step
        old = next((r for r in app_list.load() if r["where"] == "system" and r["package"] == pkg.name), {})
        cmd = ["rpm-ostree", "uninstall", old.get("nevra") or pkg.name, "--install", f]
        what = f"Updating {title} on the system. This can take a few minutes."
    else:
        cmd = ["rpm-ostree", "install", "--idempotent", f]
        what = f"Adding {title} to the system. This can take a few minutes."
    notify(f"{what.split('.')[0]}. A progress window shows it.")
    if not windows.run_steps(what, [cmd]):
        windows.failed(f"{'Updating' if update else 'Adding'} {title} {'on' if update else 'to'} the system")
        return 1
    app_list.remember({"title": title, "package": pkg.name, "nevra": pkg.nevra, "where": "system", "version": pkg.evr})
    # checked once at the next login: is it really there, and for a printer driver, add the printer
    after_restart.save_pending([e for e in after_restart.pending() if e["package"] != pkg.name] + [{"title": title, "package": pkg.name,
                                                                  "printer": printer and not update,
                                                                  "version": pkg.evr}])
    after = "After the restart, you will be asked to add your printer." if printer and not update else \
        "After the restart, you'll get a message when it's ready."
    if update:
        notify(f"{title} is updated. Restart to use the new version.")
        offer_restart(f"{title} is updated. Restart to use the new version.")
    else:
        notify(f"{title} is installed. Restart to use it.")
        offer_restart(f"{title} is installed. Restart to start using it.", f"{after}\n\nUpdates: {update_notes.UPDATES_SYSTEM}")
    return 0
