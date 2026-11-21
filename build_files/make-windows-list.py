#!/usr/bin/python3 -I
"""Build step: the list of Windows programs whose own maker has a Linux version on Flathub, Fedora or Ubuntu.

Usage: make-windows-list.py WINGET.DB FLATHUB.XML.GZ FEDORA.XML.GZ UBUNTU.YML.GZ... OUT.JSON
Sure matches only: the same name from the same maker, or a Linux app named inside the Windows name.
"""
import collections
import gzip
import json
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, "/usr/lib/evenkeel-os")
from evenkeel_os_packages.windows_file import norm, norm_maker, trim  # noqa: E402

FILL = {"for", "windows", "desktop", "app", "client", "x64", "x86", "64", "bit", "32", "portable", "setup",
        "installer", "edition", "the", "beta", "stable", "lts", "esr", "msix", "exe", "msi"}
GENERIC = {"editor", "desktop", "client", "app", "application", "viewer", "player", "studio", "manager", "browser",
           "launcher", "tool", "tools"}
# words a Windows name adds to the Linux app's name: 'VLC media player' is VLC, 'Zoom Workplace' is Zoom
DESCRIBE = {"media", "player", "workplace", "browser", "web", "meetings", "messenger", "music"}
LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def version_key(v):
    return [(0, int(x)) if x.isdigit() else (1, x) for x in re.split(r"[.\-+_]", v)]


def winget(path):
    """Each winget program's newest name, its monikers, makers and MSI product codes."""
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    rows = collections.defaultdict(list)
    for pid, name, ver, mid, mon in db.execute(
            "select i.id, n.name, v.version, m.rowid, mo.moniker from manifest m join ids i on m.id = i.rowid "
            "join names n on m.name = n.rowid join versions v on m.version = v.rowid "
            "left join monikers mo on m.moniker = mo.rowid"):
        rows[pid].append((version_key(ver), name, mid, mon))
    pubs, codes = collections.defaultdict(set), collections.defaultdict(set)
    for mid, p in db.execute("select m.manifest, p.norm_publisher from norm_publishers_map m "
                             "join norm_publishers p on m.norm_publisher = p.rowid"):
        pubs[mid].add(trim(p))
    for mid, c in db.execute("select m.manifest, p.productcode from productcodes_map m "
                             "join productcodes p on m.productcode = p.rowid"):
        codes[mid].add(c.lower())
    out = {}
    for pid, rs in rows.items():
        rs.sort()
        _, name, _, mon = rs[-1]
        out[pid] = {"name": name, "moniker": mon or "", "pub": sorted(set().union(*(pubs[r[2]] for r in rs))),
                    "codes": sorted(set().union(*(codes[r[2]] for r in rs)))}
    return out


def untranslated(comp, path):
    return next((e.text for e in comp.findall(path) if not e.get(LANG) and e.text), "")


def appstream_xml(path, flatpak):
    """Apps in an AppStream file: id, package (Flatpak id or Fedora package), untranslated name, maker."""
    apps = []
    for comp in ET.parse(gzip.open(path)).getroot().findall("component"):
        if comp.get("type") not in ("desktop-application", "desktop"):
            continue
        name = untranslated(comp, "name")
        if flatpak:
            bundle = [b.text for b in comp.findall("bundle") if b.get("type") == "flatpak" and
                      (b.text or "").startswith("app/")]
            package = bundle[0].split("/")[1] if bundle else ""
        else:
            package = comp.findtext("pkgname") or ""
        if not package or not name:
            continue
        verified = any(v.get("key") == "flathub::verification::verified" and (v.text or "").strip() == "true"
                       for v in comp.iter("value"))
        apps.append({"id": package if flatpak else re.sub(r"\.desktop$", "", comp.findtext("id") or ""),
                     "package": package, "name": name, "verified": verified,
                     "dev": untranslated(comp, "developer/name") or untranslated(comp, "developer_name")})
    return apps


def ubuntu_yaml(path):
    """Apps in Ubuntu's AppStream file (YAML): only the fields used here, read line by line."""
    apps, doc, key = [], {}, None
    for line in gzip.open(path, "rt", encoding="utf-8"):
        if line.startswith("---"):
            if doc.get("Type") in ("desktop-application", "desktop") and doc.get("Package") and doc.get("Name"):
                apps.append({"id": re.sub(r"\.desktop$", "", doc.get("ID", "")), "package": doc["Package"],
                             "name": doc["Name"], "dev": doc.get("DeveloperName", ""), "verified": False})
            doc, key = {}, None
        elif line[:1] not in (" ", "\n") and ":" in line:
            key, value = line.split(":", 1)
            if value.strip():
                doc[key] = value.strip().strip("'\"")
        elif key in ("Name", "DeveloperName") and line.startswith("  C: "):
            doc[key] = line[5:].strip().strip("'\"")
    return apps


def maker_keys(app):
    parts = app["id"].lower().split(".")
    return {norm_maker(app["dev"])} | ({parts[1]} if len(parts) >= 3 else set())


def find(pkgs, apps):
    """{winget id: app} for the Windows programs whose maker has this app."""
    by_name, by_maker = collections.defaultdict(list), collections.defaultdict(list)
    for a in apps:
        if len(norm(a["name"])) >= 3:
            by_name[norm(a["name"])].append(a)
        for k in maker_keys(a):
            if len(k) >= 4:
                by_maker[k].append(a)

    def same_maker(p, a):
        return any(len(k) >= 4 and len(x) >= 4 and (k in x or x in k) for x in p["pub"] for k in maker_keys(a))

    found = {}
    for pid, p in pkgs.items():
        n = norm(p["name"])
        hit = next((a for a in by_name.get(n, []) if same_maker(p, a)), None)
        if not hit and len(n) >= 3:
            words = set(re.findall(r"[a-z0-9+]+", re.sub(r"\(.*?\)", "", p["name"].lower())))
            maker_words = {w for x in p["pub"] for w in words if len(w) >= 4 and w in x}
            for a in (a for x in p["pub"] for a in by_maker.get(x, [])):
                fw = set(re.findall(r"[a-z0-9+]+", a["name"].lower()))
                last = a["id"].lower().split(".")[-1]
                extra = FILL | maker_words | DESCRIBE
                if (fw - maker_words and fw <= words and not words - fw - extra) or \
                        (len(last) >= 4 and last not in GENERIC and
                         (last == n or (last in words and not words - {last} - extra))):
                    hit = a
                    break
        if hit:
            found[pid] = hit
    return found


def main(db_path, flathub_path, fedora_path, *ubuntu_paths_and_out):
    *ubuntu_paths, out_path = ubuntu_paths_and_out
    pkgs = winget(db_path)
    sources = {"flatpak": appstream_xml(flathub_path, flatpak=True),
               "fedora": appstream_xml(fedora_path, flatpak=False),
               "ubuntu": [a for p in ubuntu_paths for a in ubuntu_yaml(p)]}
    matches = collections.defaultdict(dict)
    for where, apps in sources.items():
        for pid, a in find(pkgs, apps).items():
            matches[pid][where] = a["package"]
            matches[pid].setdefault("title", a["name"])
    out = {"matches": matches, "packages": {pid: pkgs[pid] for pid in matches}}
    with open(out_path, "w") as f:
        json.dump(out, f, separators=(",", ":"), sort_keys=True)
    for where in sources:
        got = {norm(pkgs[p]["name"]) for p, m in matches.items() if where in m}
        print(f"Windows programs with a Linux version, {where}: {len(got)}")
    print(f"In all: {len({norm(pkgs[p]['name']) for p in matches})} ({len(matches)} winget entries)")


if __name__ == "__main__":
    main(*sys.argv[1:])
