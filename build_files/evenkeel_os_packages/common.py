"""Paths, box kinds and names shared by every part."""
import platform
from pathlib import Path

import evenkeel_os_ui as ui


HOME = Path.home()
STATE = HOME / ".local/share/evenkeel-os/apps.json"
CACHE = HOME / ".cache/evenkeel-os/packages"
LOG = CACHE / "last.log"
HWRULES = "/usr/libexec/evenkeel-os-hwrules"
ui.TITLE = "Install Package File"
ui.ICON = "system-software-install-symbolic"


def fedora_version():
    return platform.freedesktop_os_release()["VERSION_ID"]


BOXES = {
    "rpm": {"name": "evenkeel-fedora", "label": "Fedora box",
            "image": f"registry.fedoraproject.org/fedora-toolbox:{fedora_version()}"},
    "deb": {"name": "evenkeel-ubuntu", "label": "Ubuntu box",
            "image": "quay.io/toolbx/ubuntu-toolbox:24.04"},
}
WHERE = {"evenkeel-fedora": "Fedora box", "evenkeel-ubuntu": "Ubuntu box", "system": "System",
         "flathub": "Flathub", "rules": "Hardware rule"}
