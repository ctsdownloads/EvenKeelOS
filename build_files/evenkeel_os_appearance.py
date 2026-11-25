"""Make it yours: light and dark on a schedule, and a wallpaper slideshow from a folder of the person's own pictures.

Settings are the person's own, in STATE. evenkeel-os-appearance applies them at login and every few minutes; it only
changes GNOME's own settings (dark style and wallpaper), and only when a period or a slide has changed, so a switch
made by hand stays until the next one.
"""
import datetime
import json
import math
import os
import subprocess
import zoneinfo
from pathlib import Path

STATE = Path.home() / ".config/evenkeel-os/appearance.json"
ZONES = ("/usr/share/zoneinfo/zone.tab", "/usr/share/zoneinfo/zone1970.tab")   # every city, then the newer list
PICTURES = (".jpg", ".jpeg", ".png", ".webp")
SCHEDULES = {"off": "Off", "sun": "Sunset to sunrise", "custom": "Custom times"}
EVERY = {"hour": "Every hour", "day": "Every day", "login": "At each login"}
FONT_KEYS = ("font-name", "document-font-name", "monospace-font-name", "text-scaling-factor")


def load():
    """The saved settings; anything missing or damaged in the file goes back to its default."""
    try:
        state = json.loads(STATE.read_text())
    except (OSError, ValueError):
        state = {}
    state = state if isinstance(state, dict) else {}
    for key, default, ok in (("schedule", "off", lambda v: v in SCHEDULES), ("every", "day", lambda v: v in EVERY),
                             ("dark_from", "20:00", clock_time), ("light_from", "07:00", clock_time),
                             ("slideshow", "", lambda v: isinstance(v, str)),
                             ("folder", "", lambda v: isinstance(v, str))):
        if not ok(state.get(key, default)):
            state[key] = default
        state.setdefault(key, default)
    if not isinstance(state.get("slide", -1), int):
        state.pop("slide")
    return state


def clock_time(value):
    try:
        datetime.time.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def save(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1))
    tmp.replace(STATE)


def gsettings(*args):
    """gsettings' answer, or None when it fails (no session)."""
    try:
        r = subprocess.run(["gsettings", *args], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def time_zone():
    """This computer's time zone name, as "America/Los_Angeles", or ""."""
    try:
        return os.readlink("/etc/localtime").split("zoneinfo/", 1)[1]
    except (OSError, IndexError):
        return ""


def place(zone, tables=ZONES):
    """(latitude, longitude) of a time zone's city, from the time zone list's own coordinates, or None.

    An old name, like NZ or US/Arizona, isn't in the list; the time zone database's own links (tzdata.zi) say which
    zone it stands for."""
    listed = listed_zone(zone, tables)
    return city(listed, tables) if listed else None


def listed_zone(zone, tables=ZONES):
    """The zone in the list that a name stands for: itself, or the zone its links lead to; or None."""
    seen = set()
    while zone and zone not in seen:
        if city(zone, tables):
            return zone
        seen.add(zone)
        zone = links(Path(tables[0]).parent / "tzdata.zi").get(zone)
    return None


def links(zi):
    """{old name: the zone it stands for}, from the time zone database's "L target name" lines."""
    try:
        with open(zi) as f:
            return {c[2]: c[1] for c in (line.split() for line in f) if len(c) == 3 and c[0] == "L"}
    except OSError:
        return {}


def city(zone, tables):
    def degrees(text, width):
        sign, digits = (-1 if text[0] == "-" else 1), text[1:]
        whole, rest = int(digits[:width]), digits[width:]
        return sign * (whole + int(rest[:2]) / 60 + (int(rest[2:4]) / 3600 if len(rest) >= 4 else 0))
    for table in tables:
        try:
            with open(table) as f:
                for line in f:
                    cols = line.split("\t")
                    if not line.startswith("#") and len(cols) >= 3 and cols[2].strip() == zone:
                        coords = cols[1]
                        split = max(coords.rfind("+"), coords.rfind("-"))
                        return degrees(coords[:split], 2), degrees(coords[split:], 3)
        except OSError:
            continue
    return None


def sun_times(lat, lon, day):
    """Sunrise and sunset on a day, in UTC (NOAA's formulas); None when the sun doesn't rise or set that day."""
    g = 2 * math.pi / 365 * (day.timetuple().tm_yday - 1)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g)
                       - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    la = math.radians(lat)
    cos_ha = math.cos(math.radians(90.833)) / (math.cos(la) * math.cos(decl)) - math.tan(la) * math.tan(decl)
    if not -1 <= cos_ha <= 1:
        return None
    ha = math.degrees(math.acos(cos_ha))
    midnight = datetime.datetime(day.year, day.month, day.day, tzinfo=datetime.timezone.utc)
    return tuple(midnight + datetime.timedelta(minutes=720 - 4 * (lon + s * ha) - eqtime) for s in (1, -1))


def sun_up(lat, lon, when):
    """Whether the sun is up (its top above the horizon) at a moment, by the same NOAA formulas."""
    when = when.astimezone(datetime.timezone.utc)
    hours = when.hour + when.minute / 60 + when.second / 3600
    g = 2 * math.pi / 365 * (when.timetuple().tm_yday - 1 + (hours - 12) / 24)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g)
                       - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    ha = math.radians((hours * 60 + eqtime + 4 * lon) / 4 - 180)
    la = math.radians(lat)
    return math.sin(la) * math.sin(decl) + math.cos(la) * math.cos(decl) * math.cos(ha) > math.cos(math.radians(90.833))


def sun_period(lat, lon, now):
    """"dark" or "light" and when it began, on a fixed 5-minute grid so every run agrees; "dark long" (or light) in a
    polar night or day, so a switch by hand stays until the sun really rises or sets."""
    step = datetime.timedelta(minutes=5)
    utc = now.astimezone(datetime.timezone.utc)
    t = utc.replace(minute=utc.minute - utc.minute % 5, second=0, microsecond=0)
    up = sun_up(lat, lon, t)
    name = "light" if up else "dark"
    for _ in range(366 * 24 * 12):                 # a year: the longest polar night is half of one
        if sun_up(lat, lon, t - step) != up:
            return f"{name} {t:%Y-%m-%d %H:%M}"
        t -= step
    return f"{name} long"


def dark_hours(state, now, zone=None):
    """(dark from, light from) as local times for the day of now, or None when there's no schedule or no sun times."""
    if state["schedule"] == "custom":
        return tuple(datetime.time.fromisoformat(state[k]) for k in ("dark_from", "light_from"))
    if state["schedule"] != "sun":
        return None
    zone = zone or time_zone()
    where = place(zone)
    times = where and sun_times(*where, now.date())
    if not times:
        return None
    try:
        local = zoneinfo.ZoneInfo(zone)
    except (ValueError, zoneinfo.ZoneInfoNotFoundError):
        local = now.tzinfo
    rise, sets = (t.astimezone(local).time().replace(second=0, microsecond=0) for t in times)
    return sets, rise


def period(state, now, zone=None):
    """Which part of the schedule now falls in, as "dark 2026-11-25" (the day it began), or None."""
    if state["schedule"] == "sun":
        where = place(zone or time_zone())
        return sun_period(*where, now) if where else None
    hours = dark_hours(state, now, zone)
    if hours is None:
        return None
    dark_from, light_from = hours
    t, today = now.time(), now.date()
    if dark_from > light_from:          # dark across midnight, the usual case
        if t >= dark_from:
            return f"dark {today}"
        if t < light_from:
            return f"dark {today - datetime.timedelta(days=1)}"
        return f"light {today}"
    return f"dark {today}" if dark_from <= t < light_from else f"light {today}"


def pictures(folder):
    try:
        return sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in PICTURES and p.is_file())
    except OSError:
        return []


def slot(state, now, login):
    """Which slide time now falls in; a login is always a new one for "at each login"."""
    if state["every"] == "login":
        return f"login {now.isoformat()}" if login else state.get("slot") or "start"   # "start": just switched on
    return now.strftime("%Y-%m-%d %H" if state["every"] == "hour" else "%Y-%m-%d")


def apply(state, now=None, login=False, zone=None):
    """Make the dark style and the wallpaper match the settings; True when the settings file needs saving."""
    now = now or datetime.datetime.now().astimezone()
    changed = False
    p = period(state, now, zone)
    if p and p != state.get("period"):
        if gsettings("set", "org.gnome.desktop.interface", "color-scheme",
                     "prefer-dark" if p.startswith("dark") else "default") is not None:
            state["period"], changed = p, True
    shown = pictures(state["slideshow"]) if state["slideshow"] else []
    s = slot(state, now, login)
    if shown and s != state.get("slot"):
        nxt = (state.get("slide", -1) + 1) % len(shown)     # slide is a number: load() drops anything else
        uri = shown[nxt].as_uri()
        if all(gsettings("set", "org.gnome.desktop.background", key, uri) is not None
               for key in ("picture-uri", "picture-uri-dark")):
            state["slide"], state["slot"], changed = nxt, s, True
    return changed
