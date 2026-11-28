"""Zoom meetings in the browser: Zoom's "open the Zoom app" links turned into Zoom's web version, in Chrome."""
import re
import shutil
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from evenkeel_os_ui import _, ask, launch
from evenkeel_os_packages import common, flathub, installed

CHROME = "com.google.Chrome"
CHOICE = common.STATE.with_name("zoom-browser")
CARRIED = ("pwd", "tk", "uname")       # passcode, webinar sign-up token and display name, as Zoom sent them
ZOOM_APP = [Path("/var/lib/flatpak/exports/share/applications/us.zoom.Zoom.desktop"),
            common.HOME / ".local/share/flatpak/exports/share/applications/us.zoom.Zoom.desktop"]


def zoom_host(host):
    """Zoom's own sites only (zoom.us, zoomgov.com and their parts), so a link can't send the browser elsewhere."""
    return bool(re.fullmatch(r"([a-z0-9-]+\.)*(zoom\.us|zoomgov\.com)", host))


def web_address(link):
    """zoommtg://us06web.zoom.us/join?action=join&confno=123&pwd=x -> https://us06web.zoom.us/wc/join/123?pwd=x."""
    try:
        parts = urlsplit(link)
        host = (parts.hostname or "").lower()
    except ValueError:      # not a link that can be read: Zoom's join page, where the meeting number can be typed
        return "https://zoom.us/join"
    host = host if zoom_host(host) else "zoom.us"
    query = {k: v[0] for k, v in parse_qs(parts.query).items()}
    meeting = query.get("confno", "")
    action = (query.get("action") or parts.path.rstrip("/").rsplit("/", 1)[-1]).lower()
    if not re.fullmatch(r"[0-9]{9,12}", meeting):
        return "https://zoomgov.com/join" if host.endswith("zoomgov.com") else "https://zoom.us/join"
    if action == "start":
        return f"https://{host}/wc/{meeting}/start"
    carried = {k: query[k] for k in CARRIED if query.get(k)}
    return f"https://{host}/wc/join/{meeting}" + (f"?{urlencode(carried)}" if carried else "")


def chrome_command():
    """How to start Chrome: its Flatpak, or Chrome added to the system; None if it isn't installed."""
    if installed.flatpak_installed(CHROME):
        return ["flatpak", "run", CHROME]
    found = shutil.which("google-chrome-stable") or shutil.which("google-chrome")
    return [found] if found else None


def uses_usual_browser():
    """Whether Zoom meetings were set to open in the usual browser, not Chrome."""
    try:
        return CHOICE.read_text().strip() == "default"
    except OSError:
        return False


def open_page(address, may_install=True):
    """Open a Zoom page in Chrome; the first time Chrome is missing, offer to install it, or use the usual browser."""
    command = chrome_command()
    if not command and may_install and not uses_usual_browser():
        answer = ask(_("Zoom meetings work best in Google Chrome: it can also share a browser tab with its "
                       "sound.\n\nRecommended: Install Chrome, from Flathub. It updates by itself.\n\n"
                       "Or Use the usual browser: the meeting works, but tab sound can't be shared. This is "
                       "remembered."), ok=_("Install Chrome"), cancel=_("Cancel"), extra=_("Use the usual browser"))
        if answer is None:
            return 1
        if answer == "extra":
            CHOICE.parent.mkdir(parents=True, exist_ok=True)
            CHOICE.write_text("default\n")
        else:       # if Chrome can't be installed, the meeting still opens in the usual browser
            flathub.install(CHROME, "Google Chrome", announce=False)
        command = chrome_command()
    launch((command or ["gio", "open"]) + [address])
    return 0


def open_link(link, may_install=True):
    """Zoom's page asked to open the Zoom app: the Zoom app if someone installed it, else the web version."""
    app = next((f for f in ZOOM_APP if f.exists()), None)
    if app:
        launch(["gio", "launch", str(app), link])
        return 0
    return open_page(web_address(link), may_install)
