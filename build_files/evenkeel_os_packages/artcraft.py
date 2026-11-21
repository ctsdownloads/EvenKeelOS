"""ArtCraft apps, straight from ArtCraft's own signed releases on GitHub; checked for updates once a day."""
import os
import re
import subprocess
import time

from evenkeel_os_ui import notify, say
from evenkeel_os_packages import app_list, boxes, common, windows

KEYRING = "/usr/share/evenkeel-os/artcraft-keyring.gpg"
FINGERPRINT = "2B76741B414AAD6CD33E631213A005C0B9D7C3ED"
APPS = {"photocraft": "PhotoCraft", "vectorcraft": "VectorCraft", "filmcraft": "FilmCraft", "lightcraft": "LightCraft",
        "pdfcraft": "PdfCraft", "effectcraft": "EffectCraft", "anicraft": "AniCraft", "designcraft": "DesignCraft",
        "figcraft": "FigCraft", "texturecraft": "TextureCraft", "materialcraft": "MaterialCraft",
        "soundcraft": "SoundCraft", "wordcraft": "WordCraft", "deckcraft": "DeckCraft", "cadcraft": "CADCraft",
        "gridcraft": "GridCraft"}
CHECKED = common.STATE.with_name("artcraft-checked")


def app_id(app):
    return f"ai.storyteller.{app}"


def version_key(v):
    return tuple(int(x) for x in v.split("."))


def latest(app):
    """The newest release version of an ArtCraft app, or '' when GitHub can't be reached."""
    try:
        r = subprocess.run(["git", "ls-remote", "--tags", f"https://github.com/storytold/{app}"],
                           capture_output=True, text=True, timeout=60, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except subprocess.TimeoutExpired:
        return ""
    found = re.findall(r"refs/tags/v(\d+(?:\.\d+)*)$", r.stdout, re.M)
    return max(found, key=version_key) if found else ""


def signed_by_artcraft(signature, path):
    r = subprocess.run(["gpgv", "--status-fd", "1", "--keyring", KEYRING, str(signature), str(path)],
                       capture_output=True, text=True)
    return r.returncode == 0 and re.search(rf"^\[GNUPG:\] VALIDSIG .* {FINGERPRINT}$", r.stdout, re.M) is not None


def run(text, steps, quiet):
    if quiet:
        return all(subprocess.run(cmd, capture_output=True).returncode == 0 for _, cmd in steps)
    return windows.run_steps(text, steps)


def fetch_and_install(app, version, quiet=False):
    """Download one release, check ArtCraft's signature, then install it: 'ok', 'unsigned' or 'failed'."""
    title = APPS[app]
    folder = common.CACHE / "artcraft"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{app}-{version}-linux-x86_64.flatpak"
    bundle, signature = folder / name, folder / f"{name}.asc"
    url = f"https://github.com/storytold/{app}/releases/download/v{version}/{name}"
    try:
        if not run(f"Downloading {title} from ArtCraft.",
                   [(f"Downloading {title}", ["curl", "-fsSL", "--retry", "3", "-o", str(bundle), url]),
                    ("Downloading its signature", ["curl", "-fsSL", "--retry", "3", "-o", str(signature),
                                                   f"{url}.asc"])], quiet):
            return "failed"
        if not signed_by_artcraft(signature, bundle):
            return "unsigned"
        # ArtCraft's apps ask to run programs outside their sandbox (talking to org.freedesktop.Flatpak); not here
        if not run(f"Installing {title}.", [
                (f"Installing {title}", ["flatpak", "install", "--user", "--reinstall", "-y", "--noninteractive",
                                         "--bundle", str(bundle)]),
                ("Keeping it in its sandbox", ["flatpak", "override", "--user",
                                               "--no-talk-name=org.freedesktop.Flatpak", app_id(app)])], quiet):
            return "failed"
    finally:
        bundle.unlink(missing_ok=True)
        signature.unlink(missing_ok=True)
    app_list.remember({"title": title, "package": app_id(app), "where": "artcraft", "version": version})
    return "ok"


def install(app):
    title = APPS[app]
    version = latest(app)
    if not version:
        say("ArtCraft's downloads can't be reached right now. Check the internet connection and try again.", "error")
        return 1
    if not boxes.room_for(1000):
        return 1
    result = fetch_and_install(app, version)
    if result == "unsigned":
        say(f"The {title} download isn't signed by ArtCraft, so it was not installed.", "error")
        return 1
    if result == "failed":
        windows.failed(f"Installing {title}")
        return 1
    notify(f"{title} is installed.")
    say(f"{title} is installed. Find it in Show Apps.\n\nUpdates: checked once a day, straight from ArtCraft.")
    return 0


def update_due():
    """The installed ArtCraft apps when a day has passed since the last check, else nothing."""
    ours = [r for r in app_list.load() if r["where"] == "artcraft"]
    return ours if ours and not (CHECKED.exists() and time.time() - CHECKED.stat().st_mtime < 86400) else []


def update(ours):
    """Bring installed ArtCraft apps up to ArtCraft's newest signed release."""
    reached = True
    for r in ours:
        app = r["package"].rsplit(".", 1)[-1]
        version = latest(app) if app in APPS else ""
        reached = reached and bool(version)
        if version and version_key(version) > version_key(r.get("version") or "0") and \
                fetch_and_install(app, version, quiet=True) == "ok":
            notify(f"{r['title']} is updated to version {version}.")
    if reached:     # when GitHub couldn't be reached, the next login tries again
        CHECKED.parent.mkdir(parents=True, exist_ok=True)
        CHECKED.touch()
    return 0
