"""What the installer offers: languages, keyboards, time zones, disks and networks."""
import json
import locale
import os
import re
import subprocess
import xml.etree.ElementTree as ET
import zoneinfo

import langtable

import i18n
from i18n import _

EVDEV = "/usr/share/X11/xkb/rules/evdev.xml"
LOG = "/tmp/evenkeel-os-install.log"                     # the install engine's log
LIVE_LABEL = "EvenKeelOS-Live"                           # the USB stick's label (iso/src/iso.yaml)
TZ_REGIONS = ["Africa", "America", "Antarctica", "Arctic", "Asia", "Atlantic", "Australia", "Europe", "Indian",
              "Pacific"]


def languages():
    """[(language id, English name, native name)], by English name: English and the ones EvenKeelOS is
    translated into."""
    ids = {langtable.parse_locale(name).language for name in i18n.translations()} | {"en"}
    found = []
    for lang in ids:
        if not locales(lang):
            continue
        found.append((lang, langtable.language_name(languageId=lang, languageIdQuery="en"),
                      langtable.language_name(languageId=lang)))
    return sorted(found, key=lambda x: x[1].lower())


def locales(lang):
    """[(locale, English name, native name)] for a language, most likely first (langtable's order); only
    the ones EvenKeelOS is translated into."""
    return [(loc, langtable.language_name(languageId=loc, languageIdQuery="en"),
             langtable.language_name(languageId=loc)) for loc in langtable.list_locales(languageId=lang)
            if i18n.translated(loc)]


def keyboards():
    """{layout id: description}, ids as "us" or "us(intl)", for every XKB layout and variant."""
    out = {}
    for layout in ET.parse(EVDEV).getroot().iter("layout"):
        name = layout.findtext("configItem/name")
        if name == "custom":                 # a placeholder for a layout file of one's own, not a layout
            continue
        out[name] = layout.findtext("configItem/description")
        for variant in layout.iter("variant"):
            out[f"{name}({variant.findtext('configItem/name')})"] = variant.findtext("configItem/description")
    return out


KEYMAPS = "/usr/lib/kbd/keymaps/xkb"         # kbd's text-console keymaps made from XKB layouts


def keymap_name(layout):
    """The text console's keymap for an XKB layout such as "de(nodeadkeys)": kbd's converted "de-nodeadkeys"."""
    return layout.replace("(", "-").rstrip(")")


def has_console_keymap(layout):
    """Whether a layout can be used before the desktop starts (the disk password)."""
    return os.path.exists(f"{KEYMAPS}/{keymap_name(layout)}.map.gz")


def suggested_keyboards(loc):
    """langtable's keyboards for the locale, US English always among them."""
    out = list(langtable.list_keyboards(languageId=loc))
    return out if "us" in out else out + ["us"]


def timezones():
    """{region: [(time zone, city as shown)]}, e.g. "America/Argentina/Buenos_Aires" -> "Argentina, Buenos Aires"."""
    out = {r: [] for r in TZ_REGIONS}
    for tz in zoneinfo.available_timezones():
        region, _, rest = tz.partition("/")
        if region in out and rest:
            out[region].append((tz, rest.replace("_", " ").replace("/", ", ")))
    return {r: sorted(cities, key=lambda c: c[1]) for r, cities in out.items() if cities}


def uses_12_hour(loc):
    """Whether the locale writes times with AM/PM, as GNOME's clock decides it."""
    before = locale.setlocale(locale.LC_TIME)
    try:
        locale.setlocale(locale.LC_TIME, loc)
        return "%p" in locale.nl_langinfo(locale.T_FMT) or "%r" in locale.nl_langinfo(locale.T_FMT)
    except locale.Error:
        return False
    finally:
        locale.setlocale(locale.LC_TIME, before)


def size_text(size):
    for unit, step in (("TB", 10 ** 12), ("GB", 10 ** 9)):
        if size >= step:
            return f"{size / step:.0f} {unit}" if size / step >= 10 else f"{size / step:.1f} {unit}"
    return f"{size // 10 ** 6} MB"


STICK_FILESYSTEMS = {"vfat", "exfat", "ntfs", "ext4", "btrfs", "xfs"}      # ones a log can be saved to


def lsblk(*devices):
    """lsblk's tree for the devices (all of them when none are named), sizes in bytes."""
    return json.loads(subprocess.run(["lsblk", "-J", "-b", "-o",
                                      "NAME,PATH,MODEL,SERIAL,SIZE,TYPE,RO,FSTYPE,LABEL,RM,TRAN,MOUNTPOINTS",
                                      *devices], capture_output=True, text=True, check=True).stdout)["blockdevices"]


def live_disk():
    """The USB stick this runs from, so it is never offered or erased."""
    for cmd in (["findmnt", "-no", "SOURCE", "/run/initramfs/live"], ["blkid", "-L", LIVE_LABEL]):
        source = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
        if source:
            parent = subprocess.run(["lsblk", "-no", "PKNAME", source], capture_output=True, text=True).stdout.strip()
            return f"/dev/{parent}" if parent else source
    return ""


def identity(disk):
    """What tells this disk apart, checked again just before it is erased: its model, serial number and size."""
    return f"{(disk.get('model') or '').strip()}|{(disk.get('serial') or '').strip()}|{disk['size']}"


def other_disks():
    """Writable disks, apart from this USB stick, zram and empty card readers."""
    live = live_disk()
    return [d for d in lsblk() if d["type"] == "disk" and d["path"] != live and not d["name"].startswith("zram")
            and d.get("ro") not in (True, "1") and int(d["size"]) > 0]


def disks():
    """[{"path", "model", "size", "encrypted", "identity"}]: the disks EvenKeelOS can be installed on."""
    def has_luks(dev):
        return dev.get("fstype") == "crypto_LUKS" or any(has_luks(c) for c in dev.get("children") or [])

    return [{"path": d["path"], "model": (d.get("model") or _("Disk")).strip(), "size": size_text(int(d["size"])),
             "encrypted": has_luks(d), "identity": identity(d)} for d in other_disks()]


def sticks():
    """Filesystems on other plugged-in sticks that a file can be saved to."""
    out = []
    for d in other_disks():
        if not (d.get("rm") in (True, "1") or d.get("tran") == "usb"):
            continue
        for part in [d, *(d.get("children") or [])]:
            if part.get("fstype") in STICK_FILESYSTEMS:
                name = (part.get("label") or d.get("model") or _("USB stick")).strip()
                out.append({"path": part["path"], "name": name, "size": size_text(int(d["size"]))})
    return out


def save_to_stick(path, source, name):
    """Copy source to the stick as name, then unmount it; returns "" or what went wrong."""
    mounted = subprocess.run(["udisksctl", "mount", "--no-user-interaction", "-b", path], capture_output=True,
                             text=True)
    where = re.search(r" at (/\S.*?)\.?$", mounted.stdout.strip())
    if not where:
        already = subprocess.run(["findmnt", "-no", "TARGET", path], capture_output=True, text=True).stdout.strip()
        if not already:
            return (mounted.stderr or mounted.stdout).strip() or _("The USB stick could not be opened.")
        target = already.splitlines()[0]
    else:
        target = where.group(1)
    try:
        with open(source, "rb") as src, open(f"{target}/{name}", "wb") as dst:
            dst.write(src.read())
            dst.flush()
            os.fsync(dst.fileno())
    except OSError as e:
        return _("The file could not be written: {error}.").format(error=e.strerror)
    subprocess.run(["udisksctl", "unmount", "--no-user-interaction", "-b", path], capture_output=True)
    return ""


def network():
    """(wired connected?, [{"ssid", "signal", "secured"}]) from NetworkManager, strongest Wi-Fi first."""
    def nmcli(*args):
        r = subprocess.run(["nmcli", "-t", *args], capture_output=True, text=True)
        return r.stdout.splitlines() if r.returncode == 0 else []

    wired = any(line.split(":")[:2] == ["ethernet", "connected"] for line in nmcli("-f", "TYPE,STATE", "device"))
    seen, wifi = set(), []
    for line in nmcli("-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"):
        ssid, signal, security = re.split(r"(?<!\\):", line)[:3]
        ssid = ssid.replace("\\:", ":")
        if ssid and ssid not in seen:
            seen.add(ssid)
            wifi.append({"ssid": ssid, "signal": int(signal or 0), "secured": security not in ("", "--")})
    return wired, sorted(wifi, key=lambda w: -w["signal"])
