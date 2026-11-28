"""Making, sizing, checking and repairing the app boxes."""
import json
import platform
import subprocess
import tarfile
import urllib.request
from pathlib import Path

from evenkeel_os_ui import _, N_, ask, choose, free_mb, human, notify, say
from evenkeel_os_packages import app_list, common, launchers, reading, targets, windows


def box_exists(name):
    return subprocess.run(["podman", "container", "exists", name], capture_output=True).returncode == 0


def in_box(box, *cmd):
    return ["distrobox", "enter", "-T", "-n", box, "--", *cmd]


def image_size(image):
    """Download size of a box image in MB: 0 if it is already on this computer, None if it cannot be found out."""
    if subprocess.run(["podman", "image", "exists", image], capture_output=True).returncode == 0:
        return 0
    reg, _slash, rest = image.partition("/")
    repo, _colon, tag = rest.rpartition(":")
    arch = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine(), platform.machine())
    lists = "application/vnd.oci.image.index.v1+json,application/vnd.docker.distribution.manifest.list.v2+json"
    single = "application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json"
    try:
        headers = {}
        if reg == "quay.io":
            url = f"https://quay.io/v2/auth?service=quay.io&scope=repository:{repo}:pull"
            headers["Authorization"] = "Bearer " + json.load(urllib.request.urlopen(url, timeout=6))["token"]

        def get(ref, accept):
            req = urllib.request.Request(f"https://{reg}/v2/{repo}/manifests/{ref}",
                                         headers={**headers, "Accept": accept})
            return json.load(urllib.request.urlopen(req, timeout=6))
        man = get(tag, lists + "," + single)
        if "manifests" in man:
            digest = next(m["digest"] for m in man["manifests"] if m.get("platform", {}).get("architecture") == arch)
            man = get(digest, single)
        return max(1, sum(layer["size"] for layer in man["layers"]) // 1_000_000)
    except (OSError, ValueError, KeyError, TypeError, StopIteration):     # offline, or an answer it can't read
        return None


def box_sizes(names):
    """MB each box uses, or {} if not known quickly."""
    names = [n for n in names if box_exists(n)]
    if not names:
        return {}
    try:
        r = subprocess.run(["podman", "ps", "-a", "--size", "--format", "json",
                            *[f"--filter=name=^{n}$" for n in names]], capture_output=True, text=True, timeout=20)
        out = {}
        for c in json.loads(r.stdout):
            name = (c.get("Names") or [""])[0]
            size = c.get("Size") or {}
            out[name] = max(size.get("rootFsSize", 0), size.get("rwSize", 0)) // 1_000_000
        return out
    except (OSError, subprocess.TimeoutExpired, ValueError, AttributeError, TypeError):
        return {}


def box_size(name):
    return box_sizes([name]).get(name)


def sizes_line():
    """'Space used: Fedora box 1.2 GB, Ubuntu box 650 MB.' for the boxes that exist, or ''."""
    sizes = box_sizes([common.BOXES[k]["name"] for k in common.BOXES])
    parts = [f"{_(b['label'])} {human(sizes[b['name']])}" for b in common.BOXES.values() if sizes.get(b["name"])]
    return _("Space used: {sizes}.").format(sizes=", ".join(parts)) if parts else ""


def room_for(need_mb):
    """Warn before starting when the disk is too full for it. True to go on."""
    where = common.HOME / ".local/share/containers"
    free = free_mb(where if where.exists() else common.HOME)
    if free is None or free >= need_mb:
        return True
    return ask(_("Not enough free space. This needs about {needed}, and {free} is free.\n\n"
                 "Recommended: Cancel, then empty the Trash or remove apps you don't use, and try again.\n\n"
                 "Or Try anyway: if space runs out, it stops safely and nothing is lost.")
               .format(needed=human(need_mb), free=human(free)), ok=_("Try anyway"), cancel=_("Cancel")) == "ok"


def setup_need(size):
    """Disk space to set up a box: its download unpacks to about three times its size, plus room to work."""
    return (size or 400) * 3 + 1500


def delete_box(kind):
    """Delete an app box and its downloaded system, to free the space. Your own files are not touched."""
    box = common.BOXES[kind]
    ok = windows.run_steps(_("Deleting the {label}.").format(label=_(box["label"])),
                           [["distrobox", "rm", "--force", box["name"]]])
    if ok:     # the box's system image too, unless something else still uses it
        subprocess.run(["podman", "image", "rm", box["image"]], capture_output=True)
        helpers_mark(kind).unlink(missing_ok=True)
    return ok


def first_time(kind):
    """What setting up the box takes, said before anything is downloaded, and the download size."""
    size = image_size(common.BOXES[kind]["image"])
    disk = human(setup_need(size) - 1500)
    if size == 0:
        text = _("First time only: sets up the box, which takes a minute or two and uses about {disk} of disk space.")
    elif size:
        text = _("First time only: downloads about {size} MB and uses about {disk} of disk space.")
    else:
        text = _("First time only: downloads a few hundred MB and uses about {disk} of disk space.")
    return text.format(disk=disk, size=size), size


# Desktop helpers .rpm and .deb apps expect (zenity, notify-send); xdg-open already reaches the desktop.
HELPERS = {"rpm": ["zenity", "libnotify"], "deb": ["zenity", "libnotify-bin"]}
HELPER_CHECK = "command -v zenity >/dev/null && command -v notify-send >/dev/null"


def helpers_mark(kind):
    return common.STATE.with_name(f"helpers-{common.BOXES[kind]['name']}")


def helpers_added(kind):
    helpers_mark(kind).parent.mkdir(parents=True, exist_ok=True)
    helpers_mark(kind).touch()


def helper_steps(kind):
    box = common.BOXES[kind]["name"]
    label = _("Adding the desktop parts apps expect (progress windows and notifications)")
    if kind == "rpm":
        return [(label, in_box(box, "sudo", "dnf", "-y", "install", *HELPERS[kind]))]
    return [(label, in_box(box, "sh", "-c", "sudo apt-get update && sudo env DEBIAN_FRONTEND=noninteractive "
                           "apt-get install -y " + " ".join(HELPERS[kind])))]


def install_steps(kind, title, target, doing=N_("Installing {title}"), dnf_verb="install", apt_extra=()):
    """Steps that install a package file or a package name into its box; doing is the step's name, with {title}."""
    box = common.BOXES[kind]["name"]
    step = _(doing).format(title=title)
    if kind == "rpm":
        return [(step, in_box(box, "sudo", "dnf", "-y", dnf_verb, target))]
    return [(_("Getting Ubuntu's list of packages"), in_box(box, "sudo", "apt-get", "update")),
            (step, in_box(box, "sudo", "env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install",
                          "-y", *apt_extra, target))]


def ensure_helpers(kind, quiet=False):
    """Make sure the box has the desktop helpers. Done once per box; remembered after that."""
    box = common.BOXES[kind]["name"]
    if helpers_mark(kind).exists() or not box_exists(box):
        return True
    if subprocess.run(in_box(box, "sh", "-c", HELPER_CHECK), capture_output=True).returncode != 0:
        if not windows.run_steps(_("Preparing the {label}.").format(label=_(common.BOXES[kind]["label"])),
                                 helper_steps(kind), quiet=quiet):
            return False
    helpers_added(kind)
    return True


def setup_box(kind, size=None, again=False):
    """Make the box, with plain steps and a Cancel button. Cancel or failure leaves no half-made box."""
    label = _(common.BOXES[kind]["label"])
    box = common.BOXES[kind]
    steps = []
    if size != 0:
        pull = _("Downloading the {label} (about {size} MB)") if size else _("Downloading the {label}")
        steps.append((pull.format(label=label, size=size), ["podman", "pull", box["image"]]))
    steps += [(_("Creating the {label}").format(label=label),
               ["distrobox", "create", "--yes", "--no-entry", "--name", box["name"], "--image", box["image"]]),
              (_("Getting the {label} ready. The first time takes a few minutes.").format(label=label),
               in_box(box["name"], "true"))]
    steps += helper_steps(kind)
    helpers_mark(kind).unlink(missing_ok=True)
    if again:
        heading = _("Setting up the {label} again.").format(label=label)
    else:
        heading = _("Setting up the {label}. This happens only once.").format(label=label)
    # also as a notification, so it is seen even if the progress window opens behind another window
    notify(_("{heading} It takes a few minutes; a progress window shows each step.").format(heading=heading))
    if windows.run_steps(heading, steps, cancel=True):
        helpers_added(kind)
        return True
    subprocess.run(["distrobox", "rm", "--force", box["name"]], capture_output=True)
    if windows.CANCELLED:
        say(_("Setting up the {label} was stopped. Nothing was installed.").format(label=label))
    else:
        windows.failed(_("Setting up the {label}").format(label=label))
    return False


def box_works(name):
    try:
        return subprocess.run(in_box(name, "true"), capture_output=True, timeout=300).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def repair(kind, why="", confirm=True):
    """Make a broken box again from scratch and put back the apps that were installed in it."""
    label = _(common.BOXES[kind]["label"])
    box = common.BOXES[kind]["name"]
    inside = [r for r in app_list.load() if r["where"] == box]
    names = ", ".join(r["title"] for r in inside) or _("none")
    size = image_size(common.BOXES[kind]["image"])
    if size == 0 or size is None:
        rebuild = _("Repair: rebuilds it and puts back its apps: {names}.")
    else:
        rebuild = _("Repair: rebuilds it (downloads about {size} MB) and puts back its apps: {names}.")
    if confirm and ask((why or _("The {label} is not working.").format(label=label)) + "\n\n" +
                       rebuild.format(names=names, size=size) + "\n\n" +
                       _("Your files are not touched. Anything added to the box another way is not put back."),
                       ok=_("Repair")) != "ok":
        return 1
    for r in inside:
        launchers.unexport(r)
    subprocess.run(["distrobox", "rm", "--force", box], capture_output=True)
    if not setup_box(kind, size, again=True):
        return 1
    back, missing = [], []
    for r in inside:
        f = r.get("file")
        if not f or not Path(f).exists():
            missing.append(r["title"])
            app_list.forget(r)
            continue
        try:
            pkg = reading.read_package(f)
        except (OSError, ValueError, tarfile.TarError, EOFError):
            missing.append(r["title"])
            app_list.forget(r)
            continue
        if targets.box_install(pkg, reading.classify(pkg), r["title"], quiet=True) == 0:
            if r.get("rules"):          # its hardware rule is still on the system
                entry = next(x for x in app_list.load() if x["package"] == r["package"] and x["where"] == box)
                app_list.remember({**entry, "rules": True})
            back.append(r["title"])
        else:
            missing.append(r["title"])
    text = _("The {label} is repaired.").format(label=label)
    if back:
        text += "\n\n" + _("Put back: {apps}.").format(apps=", ".join(back))
    if missing:
        text += "\n\n" + _("Not put back (open their files again to install them): {apps}.").format(
            apps=", ".join(missing))
    notify(_("The {label} is repaired.").format(label=label))
    say(text)
    return 0


def repair_command(only_broken=False):
    """Repair an app box; only_broken (from System Update) repairs only one that doesn't work."""
    used = {r["where"] for r in app_list.load()}
    kinds = [k for k, b in common.BOXES.items() if box_exists(b["name"]) or b["name"] in used]
    if not kinds:
        say(_("There are no app boxes to repair."))
        return 0
    if only_broken:
        broken = [k for k in kinds if not (box_exists(common.BOXES[k]["name"]) and box_works(common.BOXES[k]["name"]))]
        if not broken:
            say(_("Your app boxes are working. The box that did not update was made outside Install Package File, "
                  "so Repair cannot fix it."))
            return 0
        kinds = broken
    if len(kinds) == 1:
        i = 0
    else:
        i = choose(_("Which box do you want to repair?"), [_("Box")], [[_(common.BOXES[k]["label"])] for k in kinds])
        if i is None:
            return 1
    label = _(common.BOXES[kinds[i]]["label"])
    return repair(kinds[i], why=_("Repair the {label}? Use this if apps in it no longer open or update.")
                  .format(label=label))
