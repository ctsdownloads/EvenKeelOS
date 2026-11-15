"""Remove Apps."""

from evenkeel_os_ui import ask, choose, human, notify, offer_restart, say
from evenkeel_os_packages import (
    after_restart, app_list, boxes, common, installed, launchers, update_notes, windows,
)


def remove():
    records = app_list.load()
    # Flathub apps removed another way (Bazaar, the command line) come off the list.
    gone = [r for r in records if r["where"] == "flathub" and not installed.flatpak_installed(r["package"])]
    for r in gone:
        app_list.forget(r)
    records = [r for r in records if r not in gone]
    if not records:
        say("Nothing has been installed with Install Package File yet.")
        return 0
    space = boxes.sizes_line()
    i = choose("Which app do you want to remove?" + (f"\n{space}" if space else ""), ["App", "Installed in"],
               [[r["title"], common.WHERE.get(r["where"], r["where"])] for r in records])
    if i is None:
        return 1
    entry = records[i]
    title = entry["title"]
    if ask(f"Remove {title}?", ok="Remove") != "ok":
        return 1
    where = entry["where"]
    kind = next((k for k in common.BOXES if common.BOXES[k]["name"] == where), None)
    if where == "flathub":
        ok = not installed.flatpak_installed(entry["package"]) or windows.run_steps(
            f"Removing {title}.", [["flatpak", "uninstall", "-y", "--noninteractive", entry["package"]]])
    elif where == "system":
        ok = windows.run_steps(f"Removing {title} from the system.", [["rpm-ostree", "uninstall", entry["package"]]])
        if not ok and entry.get("nevra"):
            ok = windows.run_steps(f"Removing {title} from the system.", [["rpm-ostree", "uninstall", entry["nevra"]]])
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
            ok = windows.run_steps(f"Removing {title}.", [boxes.in_box(where, *cmd)])
        if ok and entry.get("rules"):
            ok = update_notes.remove_rules(entry["package"])
    if not ok:
        windows.failed(f"Removing {title}")
        return 1
    app_list.forget(entry)
    after_restart.drop_pending(entry["package"])
    notify(f"{title} is removed.")
    if where == "system":
        offer_restart(f"{title} is removed. Restart to finish.")
        return 0
    if kind and boxes.box_exists(where) and not any(r["where"] == where for r in app_list.load()):
        label = common.BOXES[kind]["label"]
        mb = boxes.box_size(where)
        free = f"frees about {human(mb)}" if mb else "frees its disk space"
        a = 'an .rpm' if kind == 'rpm' else 'a .deb'
        if ask(f"{title} is removed, and the {label} is now empty.\n\n"
               f"Recommended: Delete the box. It {free}, and comes back by itself the next time you install {a} app. "
               f"Anything added to the box another way is deleted too. Your files are not touched.\n\n"
               f"Or Keep it: saves setup time if you'll install another {a.split()[1]} app soon.",
               ok="Delete the box", cancel="Keep it") == "ok":
            if boxes.delete_box(kind):
                notify(f"The {label} is deleted.")
                say(f"The {label} is deleted.")
            else:
                windows.failed(f"Deleting the {label}")
        return 0
    say(f"{title} is removed.")
    return 0
