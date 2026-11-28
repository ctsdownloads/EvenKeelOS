"""Paths, box kinds and names shared by every part."""
import os
import platform
from pathlib import Path

import evenkeel_os_ui as ui
from evenkeel_os_ui import _, N_


HOME = Path.home()
APPS_DIR = HOME / ".local/share/applications"
BIN_DIR = HOME / ".local/bin"
STATE = HOME / ".local/share/evenkeel-os/apps.json"
CACHE = HOME / ".cache/evenkeel-os/packages"
LOG = CACHE / "last.log"
HWRULES = "/usr/libexec/evenkeel-os-hwrules"
ui.TITLE = _("Install Package File")
ui.ICON = "system-software-install-symbolic"


def fedora_version():
    return platform.freedesktop_os_release()["VERSION_ID"]


BOXES = {
    "rpm": {"name": "evenkeel-fedora", "label": N_("Fedora box"),
            "image": f"registry.fedoraproject.org/fedora-toolbox:{fedora_version()}"},
    "deb": {"name": "evenkeel-ubuntu", "label": N_("Ubuntu box"),
            "image": "quay.io/toolbx/ubuntu-toolbox:24.04"},
}
SOURCED = set()      # packages installed from a download source in this run: System Update keeps them current
FLATPAK_PLACES = ("flathub", "artcraft")     # apps installed as Flatpaks: from Flathub, or ArtCraft's own
WHERE = {"evenkeel-fedora": N_("Fedora box"), "evenkeel-ubuntu": N_("Ubuntu box"), "system": N_("System"),
         "flathub": "Flathub", "artcraft": "ArtCraft", "rules": N_("Hardware rule")}


def plain_list(items):
    """Untranslated names (N_), one per line, translated."""
    return "\n".join("  - " + _(i) for i in items)


def launcher(where, app):
    """The app grid entry distrobox-export makes for an app in a box."""
    return APPS_DIR / f"{where}-{os.path.basename(app)}"
