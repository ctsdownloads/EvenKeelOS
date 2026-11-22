#!/usr/bin/python3 -I
"""Build step: what to offer for each Windows program: its own Linux version, or a Linux app that does its job.

Usage: make-windows-list.py WINGET.DB FLATHUB.XML.GZ FEDORA.XML.GZ REPLACEMENTS.JSON UBUNTU.YML.GZ... OUT.JSON
Same app: sure matches only, the same name from the same maker. Then the hand-picked replacements, then a Linux
app of the same kind for any other program winget knows.
"""
import collections
import gzip
import json
import os
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, "/usr/lib/evenkeel-os")
from evenkeel_os_packages.artcraft import APPS as ARTCRAFT  # noqa: E402
from evenkeel_os_packages.windows_file import makers_overlap, norm, norm_maker, trim  # noqa: E402

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "vpns.json")) as f:
    VPNS = json.load(f)

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
    tags = collections.defaultdict(set)
    for mid, t in db.execute("select m.manifest, t.tag from tags_map m join tags t on m.tag = t.rowid"):
        tags[mid].add(t.lower())
    out = {}
    for pid, rs in rows.items():
        rs.sort()
        _, name, _, mon = rs[-1]
        out[pid] = {"name": name, "moniker": mon or "", "pub": sorted(set().union(*(pubs[r[2]] for r in rs))),
                    "codes": sorted(set().union(*(codes[r[2]] for r in rs))),
                    "tags": set().union(*(tags[r[2]] for r in rs))}
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

    found = {}
    for pid, p in pkgs.items():
        n = norm(p["name"])
        hit = next((a for a in by_name.get(n, []) if makers_overlap(maker_keys(a), p["pub"], least=4)), None)
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


def program(names, aliases, makers, codes, offer):
    return {"names": sorted({norm(n) for n in names} - {""}), "aliases": sorted(set(aliases) - {""}),
            "pub": sorted(makers), "codes": sorted(codes), "offer": offer}


def replacement_offer(use, job, titles):
    """The Linux app a list entry points to, with its name; None if it isn't on Flathub any more."""
    if use.startswith("web:"):      # used in the browser instead of an app (Zoom)
        return {"web": use.split(":", 1)[1], "job": job}
    if use.startswith("vpn:"):      # its company's Linux version, from that company's own download source
        name = use.split(":", 1)[1]
        if name not in VPNS:
            sys.exit(f"ERROR: {use} is not in vpns.json")
        return {"vpn": name, "title": VPNS[name]["title"]}
    if use.startswith("artcraft:"):
        app = use.split(":", 1)[1]
        if app not in ARTCRAFT:
            sys.exit(f"ERROR: {use} is not an ArtCraft app")
        return {"artcraft": app, "title": ARTCRAFT[app], "job": job}
    if use not in titles:       # left out, so one app leaving Flathub doesn't stop the build
        print(f"WARNING: {use} is in the replacements list but not on Flathub; its entries are left out")
        return None
    return {"flatpak": use, "title": titles[use], "job": job}


def main(db_path, flathub_path, fedora_path, replacements_path, *ubuntu_paths_and_out):
    *ubuntu_paths, out_path = ubuntu_paths_and_out
    pkgs = winget(db_path)
    flathub = appstream_xml(flathub_path, flatpak=True)
    titles = {a["package"]: a["name"] for a in flathub}
    sources = {"flatpak": flathub, "fedora": appstream_xml(fedora_path, flatpak=False),
               "ubuntu": [a for p in ubuntu_paths for a in ubuntu_yaml(p)]}
    with open(replacements_path) as f:
        listed = json.load(f)
    programs, same = {}, collections.defaultdict(dict)
    # 1. the same program's own Linux version
    for where, apps in sources.items():
        for pid, a in find(pkgs, apps).items():
            same[pid][where] = a["package"]
            same[pid].setdefault("title", a["name"])
    for pid, offer in same.items():
        p = pkgs[pid]
        programs[pid] = program([p["name"]], [norm(p["moniker"])], p["pub"], p["codes"], offer)
    # 2. a hand-picked replacement for a program with no Linux version
    for e in listed["programs"]:
        offer = replacement_offer(e["use"], e["job"], titles)
        if offer and "web" in offer:
            offer["title"] = e["names"][0]
        if offer:
            programs["list:" + e["names"][0]] = program(e["names"], e.get("files", []),
                                                        [norm_maker(m) for m in e["makers"]], [], offer)
    # 3. any other known program: a Linux app of the same kind, from its tags
    kinds = [(k, replacement_offer(k["use"], k["job"], titles)) for k in listed["kinds"]]
    kinds = [(k, {**offer, "kind": True}) for k, offer in kinds if offer]
    # 4. a program nobody lists: the words its installer uses to describe itself
    by_words = [{"words": k["words"], "offer": offer} for k, offer in kinds]
    for pid, p in pkgs.items():
        kind = next((offer for k, offer in kinds if set(k["tags"]) & p["tags"]), None) if pid not in programs else None
        if kind:
            programs[pid] = program([p["name"]], [norm(p["moniker"])], p["pub"], p["codes"], kind)
    with open(out_path, "w") as f:
        json.dump({"programs": programs, "kinds": by_words}, f, separators=(",", ":"), sort_keys=True)
    for where in sources:
        got = {norm(pkgs[p]["name"]) for p, m in same.items() if where in m}
        print(f"Windows programs with a Linux version, {where}: {len(got)}")
    print(f"Hand-picked replacements: {len(listed['programs'])}; same kind of app: "
          f"{sum(1 for p in programs.values() if p['offer'].get('kind'))}")


if __name__ == "__main__":
    main(*sys.argv[1:])
