#!/usr/bin/python3 -I
"""Build check: Make it yours' light and dark schedule and wallpaper slideshow, with a made-up gsettings."""
import datetime
import sys
import tempfile
import zoneinfo
from pathlib import Path

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else "/usr/lib/evenkeel-os")
import evenkeel_os_appearance as a  # noqa: E402

problems = []
set_to = []
a.gsettings = lambda *args: set_to.append(args) or ""
a.STATE = Path(tempfile.mkdtemp(), "appearance.json")
LA = "America/Los_Angeles"


def at(text, zone=LA):
    return datetime.datetime.fromisoformat(text).replace(tzinfo=zoneinfo.ZoneInfo(zone))


def minutes(t):
    return t.hour * 60 + t.minute


# Sunset and sunrise, against values worked out with an independent astronomy library (astral 3.2).
SUN = ((LA, "2026-11-25", "06:35", "16:44"), ("Europe/Copenhagen", "2026-06-21", "04:25", "21:57"),
       ("Australia/Sydney", "2026-01-15", "05:59", "20:08"), ("Asia/Tokyo", "2026-09-23", "05:29", "17:36"))
for zone, day, rise, sets in SUN:
    now = at(f"{day}T12:00", zone)
    got = a.dark_hours(a.load() | {"schedule": "sun"}, now, zone)
    want = (datetime.time.fromisoformat(sets), datetime.time.fromisoformat(rise))
    if not got or any(abs(minutes(g) - minutes(w)) > 6 for g, w in zip(got, want)):
        problems.append(f"{zone} on {day}: dark from/light from {got}, expected about {want}")
if a.sun_times(78.2, 15.6, datetime.date(2026, 12, 15)) is not None:
    problems.append("the polar night has a sunrise")
# Skips Etc/GMT+5 style names and short names like EST5EDT, which the time zone database doesn't link to a city.
linked = a.links("/usr/share/zoneinfo/tzdata.zi")


def target(zone):
    for _ in range(9):
        zone = linked.get(zone, zone)
    return zone


missing = sorted(z for z in zoneinfo.available_timezones() if not target(z).startswith("Etc/")
                 and ("/" in z or z in linked) and a.place(z) is None)
if missing:
    problems.append(f"{len(missing)} time zones have no city for sunset, such as {missing[:5]}")
# The schedule: dark across midnight, a change made by hand kept until the next switch, custom times.
s = a.load() | {"schedule": "custom", "dark_from": "21:00", "light_from": "06:30"}
for when, want in (("2026-11-25T21:00", "dark 2026-11-25"), ("2026-11-26T06:30", "light 2026-11-26"),
                   ("2026-11-25T22:00", "dark 2026-11-25"), ("2026-11-26T03:00", "dark 2026-11-25"),
                   ("2026-11-26T12:00", "light 2026-11-26")):
    if a.period(s, at(when)) != want:
        problems.append(f"custom 21:00 to 06:30 at {when}: {a.period(s, at(when))}, not {want}")
set_to.clear()
a.apply(s, at("2026-11-25T22:00"))
a.apply(s, at("2026-11-25T23:30"))
if set_to != [("set", "org.gnome.desktop.interface", "color-scheme", "prefer-dark")]:
    problems.append(f"dark at 22:00, then nothing more until morning: set {set_to}")
set_to.clear()
a.apply(s, at("2026-11-26T07:00"))
if set_to != [("set", "org.gnome.desktop.interface", "color-scheme", "default")]:
    problems.append(f"light in the morning: set {set_to}")
off = a.load()
set_to.clear()
a.apply(off, at("2026-11-26T22:00"))
if set_to:
    problems.append(f"the schedule off still changes things: {set_to}")
# The slideshow: the next picture each day, round and round; only pictures; at each login.
pics = Path(tempfile.mkdtemp())
for name in ("b.png", "a.jpg", "c.webp", "notes.txt"):
    (pics / name).write_text("x")
s = a.load() | {"slideshow": str(pics), "every": "day"}
shown = []
for day in ("2026-11-25T09:00", "2026-11-25T18:00", "2026-11-26T09:00", "2026-11-27T09:00", "2026-11-28T09:00"):
    set_to.clear()
    a.apply(s, at(day))
    shown.append(Path(set_to[0][3]).name if set_to else None)
if shown != ["a.jpg", None, "b.png", "c.webp", "a.jpg"]:
    problems.append(f"daily slideshow showed {shown}")
if set_to and {k for _, _, k, _ in set_to} != {"picture-uri", "picture-uri-dark"}:
    problems.append(f"a slide sets {set_to}, not the light and dark wallpaper")
s = a.load() | {"slideshow": str(pics), "every": "login"}
set_to.clear()
a.apply(s, at("2026-11-25T09:00"))
a.apply(s, at("2026-11-25T09:05"))
a.apply(s, at("2026-11-25T18:00"), login=True)
if [Path(x[3]).name for x in set_to if x[2] == "picture-uri"] != ["a.jpg", "b.png"]:
    problems.append(f"at each login: switched on shows the first, then one per login: {set_to}")
a.save(s)
if a.load()["slideshow"] != str(pics):
    problems.append("the settings don't survive saving")
# An old name finds its city through the time zone database's own link, even through two links.
tz = Path(tempfile.mkdtemp())
(tz / "zone.tab").write_text("NZ\t-3652+17446\tPacific/Auckland\nAQ\t-7750+16636\tAntarctica/McMurdo\n")
(tz / "tzdata.zi").write_text("L Pacific/Auckland NZ\nL Pacific/Auckland Antarctica/McMurdo\nL NZ Old/Name\n")
table = (str(tz / "zone.tab"),)
if not (a.place("NZ", table) == a.place("Old/Name", table) == a.place("Pacific/Auckland", table)):
    problems.append(f"an old time zone name finds the wrong city: NZ {a.place('NZ', table)}")
if a.place("Antarctica/McMurdo", table) == a.place("NZ", table) or a.place("Asia/Nowhere", table) is not None:
    problems.append("a listed zone doesn't keep its own city, or a missing zone has one")
if a.listed_zone("Old/Name", table) != "Pacific/Auckland":
    problems.append(f"an old name's city is named {a.listed_zone('Old/Name', table)}, not Auckland")
(tz / "tzdata.zi").write_text("L A/B A/C\nL A/C A/B\n")
if a.place("A/B", table) is not None:
    problems.append("a loop in the links isn't stopped")
# Sunset to sunrise follows the sun itself: one period from sunset to sunrise, the same in every run.
sun = a.load() | {"schedule": "sun"}
labels = [a.period(sun, at(f"2026-11-25T{h}"), LA) for h in ("17:00", "17:03", "21:00", "23:59")]
labels += [a.period(sun, at(f"2026-11-26T{h}"), LA) for h in ("00:01", "06:00")]


def began(label, utc):
    """A period's start, in UTC as the label has it, is within 10 minutes of the known time."""
    try:
        when = datetime.datetime.strptime(label.split(" ", 1)[1], "%Y-%m-%d %H:%M")
    except (IndexError, ValueError):
        return False
    return abs(when - datetime.datetime.fromisoformat(utc)) <= datetime.timedelta(minutes=10)


if len(set(labels)) != 1 or not labels[0].startswith("dark") or not began(labels[0], "2026-11-26T00:44"):
    problems.append(f"one night in Los Angeles isn't one dark period from sunset (16:44): {labels}")
noon = a.period(sun, at("2026-11-26T12:00"), LA)
if not noon.startswith("light") or not began(noon, "2026-11-26T14:36"):
    problems.append(f"midday in Los Angeles isn't light since sunrise (06:36): {noon}")
# In the polar night (or day) the period began at the last sunset (or sunrise), months ago, and doesn't change.
north = "Arctic/Longyearbyen"
for days, kind in ((("2026-10-28", "2026-12-15", "2027-02-01"), "dark"), (("2026-04-20", "2026-06-21"), "light")):
    got = {a.period(sun, at(f"{d}T12:00", north), north) for d in days}
    if len(got) != 1 or not got.pop().startswith(kind):
        problems.append(f"Longyearbyen's polar {kind} isn't one {kind} period: {sorted(got)}")
# Longyearbyen in April: the sun sets just after midnight; the period mustn't flip back and forth.
flips, last = 0, None
for m in range(0, 24 * 60, 5):
    now = at("2027-04-19T00:00", north) + datetime.timedelta(minutes=m)
    p = a.period(sun, now, north).split()[0]
    flips, last = flips + (last is not None and p != last), p
if flips > 2:
    problems.append(f"Longyearbyen on 2027-04-19 switches {flips} times in a day")
# A damaged settings file: defaults, never a crash.
for text in ("null", "[]", '{"schedule": "x", "every": 3, "dark_from": "25:99", "slide": "2", "slideshow": 7}'):
    a.STATE.write_text(text)
    try:
        d = a.load()
        a.apply(d, at("2026-11-25T22:00"))
        if (d["schedule"], d["every"], d["dark_from"], d["slideshow"]) != ("off", "day", "20:00", ""):
            problems.append(f"settings file {text!r} gives {d}")
    except Exception as e:  # noqa: BLE001
        problems.append(f"settings file {text!r} crashes: {e!r}")
if problems:
    sys.exit("ERROR: Make it yours, light and dark and slideshow:\n  " + "\n  ".join(problems))
print("Make it yours: sunset and sunrise right in 4 places, every time zone (old names too) has a city, polar nights "
      "and a damaged settings file are handled, schedule and slideshow work")
