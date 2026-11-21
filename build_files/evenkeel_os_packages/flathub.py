"""Finding the same app on Flathub, and installing from it."""
import json
import os
import re
import shutil
import urllib.request
from evenkeel_os_ui import notify, say
from evenkeel_os_packages import app_list, installed, update_notes, windows


GENERIC = re.compile(r"(^|\s)(web browser|browser|desktop|for linux|client|launcher|app|stable|beta|bin)$")


def base_name(s):
    """A name without the generic words packages add: 'Brave Web Browser' and 'brave-browser' -> 'brave'."""
    s = re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).strip()
    for _ in range(3):
        s = GENERIC.sub("", s).strip()
    return s.replace(" ", "")


def app_ids(pkg):
    """App IDs the package names itself by (its app data file or launcher, e.g. com.visualstudio.code)."""
    ids = []
    for p in pkg.files:
        b = os.path.basename(p)
        for end in (".metainfo.xml", ".appdata.xml", ".desktop"):
            if b.endswith(end) and b.count(".") >= 2 + end.count("."):
                ids.append(b[:-len(end)])
        if b.endswith((".metainfo.xml", ".appdata.xml")):
            m = re.search(r"<id>\s*([^<\s]+?)(\.desktop)?\s*</id>", pkg.texts.get(p, ""))
            if m and m.group(1).count(".") >= 2:
                ids.append(m.group(1))
    return list(dict.fromkeys(ids))


def flathub_get(url, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, method="POST" if data else "GET", data=body,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=8))


def flathub_match(pkg, info):
    """(app id, name) of the same app on Flathub, or None; looser name matches only for verified apps."""
    if not shutil.which("flatpak"):
        return None
    for app_id in app_ids(pkg)[:4]:
        try:
            data = flathub_get(f"https://flathub.org/api/v2/appstream/{app_id}")
            if data and data.get("id"):
                return data["id"], data.get("name") or info["title"]
        except (OSError, ValueError):       # Flathub unreachable or its answer unreadable: no match from it
            continue
    want = {installed.norm_name(s) for s in (pkg.name, info["title"]) if s} - {""}
    loose = {base_name(s) for s in (pkg.name, info["title"]) if s} - {""}
    hits, seen = [], set()
    for query in dict.fromkeys([info["title"], pkg.name]):
        try:
            for h in flathub_get("https://flathub.org/api/v2/search", {"query": query}).get("hits", [])[:10]:
                if h.get("app_id") not in seen:
                    seen.add(h.get("app_id"))
                    hits.append(h)
        except (OSError, ValueError):       # Flathub unreachable or its answer unreadable: no match from it
            continue
    for h in hits:
        app_id, name = h.get("app_id", ""), h.get("name", "")
        if installed.norm_name(name) in want or installed.norm_name(app_id.rsplit(".", 1)[-1]) in want:
            return app_id, name
    for h in hits:
        app_id, name = h.get("app_id", ""), h.get("name", "")
        if h.get("verification_verified") and (base_name(name) in loose or
                                               base_name(app_id.rsplit(".", 1)[-1]) in loose):
            return app_id, name
    return None


def install(app_id, name):
    """Install an app from Flathub and list it in Remove Apps."""
    if not windows.run_steps(f"Installing {name} from Flathub.",
                             [["flatpak", "install", "--system", "-y", "--noninteractive", "flathub", app_id]]):
        windows.failed(f"Installing {name}")
        return 1
    app_list.remember({"title": name, "package": app_id, "where": "flathub"})
    notify(f"{name} is installed.")
    say(f"{name} is installed. Find it in Show Apps.\n\n{update_notes.UPDATES_FLATHUB}")
    return 0
