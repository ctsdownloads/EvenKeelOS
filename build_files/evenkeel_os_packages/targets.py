"""Installing into a box or onto the system."""
import json
import platform
import shlex
import shutil
import subprocess

from evenkeel_os_ui import _, N_, ask, notify, offer_restart, say
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
    label = _(common.BOXES[pkg.kind]["label"])
    box = common.BOXES[pkg.kind]["name"]
    f = str(staged_copy(pkg))
    boxes.ensure_helpers(pkg.kind, quiet=quiet)      # boxes made before the helpers were part of the setup
    rules_before = hwrules.box_rules(box)
    repos_before = update_notes.box_repos(box, pkg.kind)
    doing = {"reinstall": N_("Reinstalling {title}"), "update": N_("Updating {title}"),
             "older": N_("Installing the older version of {title}")}.get(mode, N_("Installing {title}"))
    doing_in_box = {"reinstall": N_("Reinstalling {title} in the {label}."),
                    "update": N_("Updating {title} in the {label}."),
                    "older": N_("Installing the older version of {title} in the {label}.")
                    }.get(mode, N_("Installing {title} in the {label}."))
    steps = boxes.install_steps(pkg.kind, title, f, doing,
                                dnf_verb={"reinstall": "reinstall", "older": "downgrade"}.get(mode, "install"),
                                apt_extra={"reinstall": ["--reinstall"], "older": ["--allow-downgrades"]}.get(mode, []))
    if not windows.run_steps(_(doing_in_box).format(title=title, label=label), steps):
        if quiet:
            return 1
        if not boxes.box_works(box):
            def repair_then_install():
                if boxes.repair(pkg.kind, confirm=False) != 0:
                    return 1
                return box_install(pkg, info, title)
            return windows.failed(_("Installing {title}").format(title=title),
                                  offer=(_("Repair the box"), repair_then_install),
                                  reason=_("The {label} isn't working.\n\nRecommended: Repair the box. It rebuilds "
                                           "the box, puts your apps back, then installs {title}. Your files aren't "
                                           "touched.").format(label=label, title=title))
        return windows.failed(_("Installing {title}").format(title=title))
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
            extra = "\n\n" + _("Unplug the device and plug it back in so it works.")
        else:
            extra = "\n\n" + _("The device rule wasn't added, so the device may not work.\n{details}").format(
                details=out)
    if info["notes"]:
        extra += "\n\n" + _("In the box, these won't work:") + "\n" + install_file.plain_list(info["notes"])
    if apps:
        where = _("Find it in Show Apps.")
    elif bins:
        where = _("It is a command-line tool, so it has no window in Show Apps.")
    else:
        where = _("It has no app of its own; other apps in the box use it.")
    done = {"reinstall": N_("{title} is reinstalled."), "update": N_("{title} is updated to version {version}."),
            "older": N_("{title} is now version {version}.")}.get(mode, N_("{title} is installed."))
    done = _(done).format(title=title, version=installed.plain_version(pkg.evr))
    notify(done)
    say(done + " " + where + extra + "\n\n" + _(update_notes.UPDATES_YES if updates else update_notes.UPDATES_NO))
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
    if not windows.run_steps(_("Checking whether Fedora has {name}.").format(name=name),
                             [["timeout", "180", "sh", "-c", query]]):
        return ""
    try:
        return next((line.strip() for line in out.read_text().splitlines() if line.strip()), "")
    except OSError:
        return ""


def install_from_fedora(pkg, title, printer, version, services=False):
    """Add the package to the system from Fedora's repos by name, so System Update keeps it up to date."""
    what = _("Adding {title} to the system from Fedora. This can take a few minutes.").format(title=title)
    notify(_("Adding {title} to the system from Fedora. A progress window shows it.").format(title=title))
    if not windows.run_steps(what, [["rpm-ostree", "install", "--idempotent", pkg.name]]):
        windows.failed(_("Adding {title} to the system").format(title=title))
        return 1
    app_list.remember({"title": title, "package": pkg.name, "where": "system", "from_fedora": True,
                       "version": version})
    after_restart.add_pending({"title": title, "package": pkg.name, "printer": printer, "services": services})
    after = _("After the restart, you will be asked to add your printer.") if printer else \
        _("After the restart, you'll get a message when it's ready.")
    notify(_("{title} is installed. Restart to use it.").format(title=title))
    offer_restart(_("{title} is installed. Restart to start using it.").format(title=title),
                  after + "\n\n" + _("Updates: {how}").format(how=_(update_notes.UPDATES_FEDORA)))
    return 0


def install_system(pkg, title, printer=False, update=False, services=False):
    if not update and pkg.kind == "rpm":
        version = fedora_package_version(pkg.name)
        if version:
            newer = "\n\n" + _("Your file is newer than Fedora's. Use the file only if you need that newer version "
                               "now.") if installed.compare("rpm", pkg.evr, version) > 0 else ""
            answer = ask(_("Fedora has {title}.\n\nRecommended: Install from Fedora. System Update keeps it up to "
                           "date.\n\nOr Use the file: installs your download. It never updates.").format(title=title)
                         + newer, ok=_("Install from Fedora"), cancel=_("Cancel"), extra=_("Use the file"))
            if answer == "ok":
                return install_from_fedora(pkg, title, printer, version, services)
            if answer != "extra":
                return 1
    f = str(staged_copy(pkg))
    if update:      # the layered file is swapped for the newer one in one step
        old = next((r for r in app_list.load() if r["where"] == "system" and r["package"] == pkg.name), {})
        cmd = ["rpm-ostree", "uninstall", old.get("nevra") or pkg.name, "--install", f]
        what = _("Updating {title} on the system. This can take a few minutes.").format(title=title)
        started = _("Updating {title} on the system. A progress window shows it.").format(title=title)
    else:
        cmd = ["rpm-ostree", "install", "--idempotent", f]
        what = _("Adding {title} to the system. This can take a few minutes.").format(title=title)
        started = _("Adding {title} to the system. A progress window shows it.").format(title=title)
    notify(started)
    if not windows.run_steps(what, [cmd]):
        if update:
            windows.failed(_("Updating {title} on the system").format(title=title))
        else:
            windows.failed(_("Adding {title} to the system").format(title=title))
        return 1
    app_list.remember({"title": title, "package": pkg.name, "nevra": pkg.nevra, "where": "system", "version": pkg.evr})
    # this system ignores an install script turning on a service, so it is done after the restart
    after_restart.add_pending({"title": title, "package": pkg.name, "printer": printer and not update,
                               "version": pkg.evr, "services": services and not update})
    after = _("After the restart, you will be asked to add your printer.") if printer and not update else \
        _("After the restart, you'll get a message when it's ready.")
    if update:
        notify(_("{title} is updated. Restart to use the new version.").format(title=title))
        offer_restart(_("{title} is updated. Restart to use the new version.").format(title=title))
    else:
        notify(_("{title} is installed. Restart to use it.").format(title=title))
        offer_restart(_("{title} is installed. Restart to start using it.").format(title=title),
                      after + "\n\n" + _("Updates: {how}").format(how=_(update_notes.UPDATES_SYSTEM)))
    return 0
