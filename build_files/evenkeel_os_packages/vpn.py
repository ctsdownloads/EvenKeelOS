"""Get a VPN: a VPN app from its company's own download source, added to the system so it keeps updating."""
import json
import subprocess

from evenkeel_os_ui import ask, choose, notify, offer_restart, say
from evenkeel_os_packages import after_restart, app_list, common, installed, windows

LIST = "/usr/share/evenkeel-os/vpns.json"
HELPER = "/usr/libexec/evenkeel-os-vpn"
UPDATES = "Updates: automatic, from {maker}'s own download source. A daily check finds new versions, which start " \
          "at the next restart."


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
        say("The VPN list is missing.", "error")
        return 1
    keys = list(vpns)
    rows = [[vpns[k]["title"], "Installed" if is_installed(k) else ""] for k in keys]
    i = choose("Which VPN do you want? Each one comes from its company's own download source and keeps updating. "
               "To connect, you need an account with that company.", ["VPN", "Status"], rows)
    return install(keys[i]) if i is not None else 1


def install(name, intro=""):
    v = load()[name]
    title, maker = v["title"], v["maker"]
    if is_installed(name):
        say(f"{title} is already installed. Find it in Show Apps.")
        return 0
    if not has_key(v):
        say(f"{title} isn't available for Fedora {common.fedora_version()} yet. Check again after the next System "
            f"Update.", "warning")
        return 1
    if ask(f"{intro}Install {title}\n\nIt comes from {maker}'s own download source, which is added to the system "
           f"so {title} keeps updating. Needs your password and a restart.\n\nTo connect, you need a {maker} account.",
           ok=f"Install {title}") != "ok":
        return 1
    notify(f"Adding {title} to the system. A progress window shows it.")
    if not windows.run_steps(f"Adding {title} to the system. This can take a few minutes.",
                             [["pkexec", HELPER, "install", name]]):
        return windows.failed(f"Adding {title} to the system")
    app_list.remember({"title": title, "package": v["packages"][0], "where": "system", "vpn": name})
    after_restart.add_pending({"title": title, "package": v["packages"][0], "vpn": name})
    notify(f"{title} is installed. Restart to use it.")
    offer_restart(f"{title} is installed. Restart to start using it.",
                  f"After the restart, you'll be asked for your password once, to turn it on.\n\n"
                  f"{UPDATES.format(maker=maker)}")
    return 0


def offer_for_file(name, pkg):
    """A downloaded VPN file: install from its company's own download source, so it keeps updating. A file alone
    would never update, and some are only part of the app (IVPN's) or only add the source (Proton's, NordVPN's)."""
    v = load()[name]
    return install(name, intro=f"{pkg.path.name} is {v['title']}. It's installed from {v['maker']}'s own download "
                               f"source instead of the file, so it keeps updating.\n\n")


def turn_on(entry):
    """After the restart: turn on its background services. False to ask again at the next login."""
    v = load().get(entry["vpn"])
    if not v:
        return False
    title = v["title"]
    if ask(f"{title} is installed. Turn it on: its background service starts now and with the computer. Needs your "
           f"password.", ok="Turn it on", cancel="Later") != "ok":
        return False
    r = subprocess.run(["pkexec", HELPER, "turn-on", entry["vpn"]], capture_output=True, text=True)
    if r.returncode in (126, 127):
        return False
    if r.returncode != 0:
        say(f"{title} is installed, but its background service didn't turn on, so it may not connect.\n\n"
            f"{r.stdout.strip()}", "warning")
        return True
    notify(f"{title} is ready.")
    group = f"\n\nLog out and back in once, so {title} lets your account use it." if v.get("group") else ""
    say(f"{title} is ready. Find it in Show Apps.{group}")
    return True


def turn_on_services(entry):
    """An app added from a file whose installer turns on a background service. False to ask again next login."""
    title = entry["title"]
    if ask(f"{title} is installed. It has a background service that needs turning on. Needs your password.",
           ok="Turn it on", cancel="Later") != "ok":
        return False
    r = subprocess.run(["pkexec", HELPER, "services", entry["package"]], capture_output=True, text=True)
    if r.returncode in (126, 127):
        return False
    if r.returncode != 0:
        say(f"{title} is installed, but its background service didn't turn on.\n\n{r.stdout.strip()}", "warning")
    return True


def remove_steps(entry):
    return [["pkexec", HELPER, "remove", entry["vpn"]]]
