"""Remove Apps."""
import subprocess

from evenkeel_os_ui import _, ask, choose, human, notify, offer_restart, say
from evenkeel_os_packages import (
    after_restart, app_list, boxes, common, installed, launchers, update_notes, vpn, windows,
)


def remove():
    records = app_list.load()
    # Apps removed another way (Bazaar, the command line) come off the list.
    asked = installed.system_requested()
    gone = [r for r in records
            if (r["where"] in common.FLATPAK_PLACES and not installed.flatpak_installed(r["package"]))
            or (r["where"] == "system" and asked is not None and r["package"] not in asked)]
    for r in gone:
        app_list.forget(r)
        after_restart.drop_pending(r["package"])
    records = [r for r in records if r not in gone]
    if not records:
        say(_("Nothing has been installed with Install Package File yet."))
        return 0
    space = boxes.sizes_line()
    i = choose(_("Which app do you want to remove?") + (f"\n{space}" if space else ""),
               [_("App"), _("Installed in")],
               [[r["title"], _(common.WHERE.get(r["where"], r["where"]))] for r in records])
    if i is None:
        return 1
    entry = records[i]
    title = entry["title"]
    if ask(_("Remove {title}?").format(title=title), ok=_("Remove")) != "ok":
        return 1
    where = entry["where"]
    kind = next((k for k in common.BOXES if common.BOXES[k]["name"] == where), None)
    if where in common.FLATPAK_PLACES:
        ok = not installed.flatpak_installed(entry["package"]) or windows.run_steps(
            _("Removing {title}.").format(title=title),
            [["flatpak", "uninstall", "--user" if where == "artcraft" else "--system", "-y", "--noninteractive",
              entry["package"]]])
        if ok and where == "artcraft":      # the sandbox setting made at install goes too
            subprocess.run(["flatpak", "override", "--user", "--reset", entry["package"]], capture_output=True)
    elif where == "system" and entry.get("vpn"):     # its services and download source go too
        ok = windows.run_steps(_("Removing {title} from the system.").format(title=title), vpn.remove_steps(entry))
    elif where == "system":
        ok = windows.run_steps(_("Removing {title} from the system.").format(title=title),
                               [["rpm-ostree", "uninstall", entry["package"]]])
        if not ok and entry.get("nevra"):
            ok = windows.run_steps(_("Removing {title} from the system.").format(title=title),
                                   [["rpm-ostree", "uninstall", entry["nevra"]]])
    elif where == "rules":
        ok = update_notes.remove_rules(entry["package"])
    else:
        launchers.unexport(entry)
        ok = True
        # An app already gone from its box just comes off the list.
        present = boxes.box_exists(where) and boxes.box_works(where)
        if present and kind and installed.box_version(kind, entry["package"]):
            # a download source is purged on Ubuntu, so its source file (a kept setting otherwise) goes too
            purge = ["--purge"] if entry.get("source") else []
            cmd = ["sudo", "dnf", "-y", "remove", entry["package"]] if where == common.BOXES["rpm"]["name"] else \
                ["sudo", "env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "remove", "-y", *purge, entry["package"]]
            ok = windows.run_steps(_("Removing {title}.").format(title=title), [boxes.in_box(where, *cmd)])
        if ok and entry.get("rules"):
            ok = update_notes.remove_rules(entry["package"])
    if not ok:
        windows.failed(_("Removing {title}").format(title=title))
        return 1
    app_list.forget(entry)
    after_restart.drop_pending(entry["package"])
    notify(_("{title} is removed.").format(title=title))
    if where == "system":
        offer_restart(_("{title} is removed. Restart to finish.").format(title=title))
        return 0
    if kind and boxes.box_exists(where) and not any(r["where"] == where for r in app_list.load()):
        label = _(common.BOXES[kind]["label"])
        mb = boxes.box_size(where)
        apps = _("an .rpm app") if kind == "rpm" else _("a .deb app")
        again = _("Recommended: Delete the box. It comes back by itself the next time you install {apps}. Anything "
                  "added to the box another way is deleted too. Your files are not touched.").format(apps=apps)
        if mb:
            again += " " + _("Deleting it frees about {size}.").format(size=human(mb))
        if ask(_("{title} is removed, and the {label} is now empty.").format(title=title, label=label) + "\n\n" +
               again + "\n\n" +
               _("Or Keep it: saves setup time if you'll install another {kind} app soon.")
               .format(kind=".rpm" if kind == "rpm" else ".deb"),
               ok=_("Delete the box"), cancel=_("Keep it")) == "ok":
            if boxes.delete_box(kind):
                notify(_("The {label} is deleted.").format(label=label))
                say(_("The {label} is deleted.").format(label=label))
            else:
                windows.failed(_("Deleting the {label}").format(label=label))
        return 0
    say(_("{title} is removed.").format(title=title))
    return 0
