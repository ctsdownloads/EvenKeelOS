"""Get a VPN: a VPN app from its company's own download source, added to the system so it keeps updating."""
import json
import subprocess

from evenkeel_os_ui import _, N_, ask, choose, load_program, notify, say
from evenkeel_os_packages import after_restart, app_list, common, installed, windows

HELPER = "/usr/libexec/evenkeel-os-vpn"
LIST = load_program(HELPER, "vpnhelper").LIST     # the root helper's own list, so both read the same file
UPDATES = N_("Updates: automatic, from {maker}'s own download source. A daily check finds new versions, which "
             "start at the next restart.")


def load():
    try:
        with open(LIST) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def has_key(v):
    return bool(v["keys"].get(common.fedora_version()) or v["keys"].get("any"))


def for_package(name):
    """The VPN a downloaded package belongs to, or None."""
    return next((k for k, v in load().items() if name in v["files"]), None)


def is_installed(name):
    v = load().get(name)
    asked = installed.system_requested()
    return bool(v and asked and v["packages"][0] in asked)


def pick():
    vpns = load()
    if not vpns:
        say(_("The VPN list is missing."), "error")
        return 1
    keys = list(vpns)
    rows = [[vpns[k]["title"], _("Installed") if is_installed(k) else ""] for k in keys]
    i = choose(_("Which VPN do you want? Each one comes from its company's own download source and keeps updating. "
                 "To connect, you need an account with that company."), [_("VPN"), _("Status")], rows)
    return install(keys[i]) if i is not None else 1


def install(name, intro=""):
    v = load()[name]
    title, maker = v["title"], v["maker"]
    if is_installed(name):
        say(_("{title} is already installed. Find it in Show Apps.").format(title=title))
        return 0
    if not has_key(v):
        say(_("{title} isn't available for Fedora {version} yet. Check again after the next System Update.")
            .format(title=title, version=common.fedora_version()), "warning")
        return 1
    if ask(intro + _("Install {title}\n\nIt comes from {maker}'s own download source, which is added to the "
                     "system so {title} keeps updating. Needs your password and a restart.\n\nTo connect, you need "
                     "a {maker} account.").format(title=title, maker=maker),
           ok=_("Install {title}").format(title=title)) != "ok":
        return 1
    notify(_("Adding {title} to the system. A progress window shows it.").format(title=title))
    if not windows.run_steps(_("Adding {title} to the system. This can take a few minutes.").format(title=title),
                             [["pkexec", HELPER, "install", name]]):
        return windows.failed(_("Adding {title} to the system").format(title=title))
    app_list.remember({"title": title, "package": v["packages"][0], "where": "system", "vpn": name})
    after_restart.add_pending({"title": title, "package": v["packages"][0], "vpn": name})
    after_restart.offer(title, _("After the restart, you'll be asked for your password once, to turn it on.") +
                        "\n\n" + _(UPDATES).format(maker=maker))
    return 0


def offer_for_file(name, pkg):
    """A downloaded VPN file: install from its company's own download source, so it keeps updating."""
    v = load()[name]
    return install(name, intro=_("{filename} is {title}. It's installed from {maker}'s own download source instead "
                                 "of the file, so it keeps updating.").format(
                                     filename=pkg.path.name, title=v["title"], maker=v["maker"]) + "\n\n")


def run_helper(*args):
    """The root helper's answer; None when the password wasn't given."""
    r = subprocess.run(["pkexec", HELPER, *args], capture_output=True, text=True)
    return None if r.returncode in (126, 127) else r


def turn_on(entry):
    """After the restart: turn on its background services. False to ask again at the next login."""
    v = load().get(entry["vpn"])
    if not v:
        return False
    title = v["title"]
    if ask(_("{title} is installed. Turn it on: its background service starts now and with the computer. Needs "
             "your password.").format(title=title), ok=_("Turn it on"), cancel=_("Later")) != "ok":
        return False
    r = run_helper("turn-on", entry["vpn"])
    if r is None:
        return False
    if r.returncode != 0:
        say(_("{title} is installed, but its background service didn't turn on, so it may not connect.\n\n"
              "{details}").format(title=title, details=r.stdout.strip()), "warning")
        return True
    notify(_("{title} is ready.").format(title=title))
    group = "\n\n" + _("Log out and back in once, so {title} lets your account use it.").format(title=title) \
        if v.get("group") else ""
    say(_("{title} is ready. Find it in Show Apps.").format(title=title) + group)
    return True


def turn_on_services(entry):
    """An app added from a file whose installer turns on a background service. False to ask again next login."""
    title = entry["title"]
    if ask(_("{title} is installed. It has a background service that needs turning on. Needs your password.")
           .format(title=title), ok=_("Turn it on"), cancel=_("Later")) != "ok":
        return False
    r = run_helper("services", entry["package"])
    if r is None:
        return False
    if r.returncode != 0:
        say(_("{title} is installed, but its background service didn't turn on.\n\n{details}")
            .format(title=title, details=r.stdout.strip()), "warning")
    return True
