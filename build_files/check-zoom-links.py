#!/usr/bin/python3 -I
"""Build test: Zoom's "open the Zoom app" links open the right Zoom web address, only on Zoom's own sites, in Chrome."""
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, "/usr/lib/evenkeel-os")
from evenkeel_os_packages import zoom  # noqa: E402

JOIN = "https://zoom.us/join"
CASES = [
    # what Zoom's launch page sends on Linux, and the web address it should become
    ("zoommtg://zoom.us/join?action=join&confno=9876543210&pwd=abcDEF123&browser=firefox&confid=dGlkPTE",
     "https://zoom.us/wc/join/9876543210?pwd=abcDEF123"),
    ("zoommtg://us06web.zoom.us/join?action=join&confno=86118972847&pwd=U0pSQ0KiS2xRbzNFUlJEODpzbEhaQT09"
     "&confid=dXRpZD1V&browser=chrome", "https://us06web.zoom.us/wc/join/86118972847?pwd=U0pSQ0KiS2xRbzNFUlJEODpzbE"
     "haQT09"),
    ("zoommtg://zoom.us/join?action=join&confno=91234567890&tk=WEBINAR-token_1&uname=Matt+H",
     "https://zoom.us/wc/join/91234567890?tk=WEBINAR-token_1&uname=Matt+H"),
    ("zoomus://zoom.us/join?confno=123456789&pwd=xxxx&zc=0", "https://zoom.us/wc/join/123456789?pwd=xxxx"),
    ("zoommtg://zoom.us/start?confno=123456789&zc=0", "https://zoom.us/wc/123456789/start"),
    ("zoommtg://zoom.us/join?action=Start&confno=123456789", "https://zoom.us/wc/123456789/start"),
    ("zoommtg://zoom.us/meeting/join?confno=123456789&pwd=p", "https://zoom.us/wc/join/123456789?pwd=p"),
    ("zoommtg://ZOOM.US:443/join?confno=123456789", "https://zoom.us/wc/join/123456789"),
    ("zoommtg://zoomgov.com/join?action=join&confno=1612345678&pwd=g", "https://zoomgov.com/wc/join/1612345678?pwd=g"),
    ("zoommtg://zoom.us/join?action=join&confno=123456789&pwd=a%26b%3Dc",
     "https://zoom.us/wc/join/123456789?pwd=a%26b%3Dc"),
    # anything that isn't Zoom's own site goes to Zoom's own site
    ("zoommtg://evil.example.com/join?action=join&confno=123456789", "https://zoom.us/wc/join/123456789"),
    ("zoommtg://zoom.us.evil.com/join?action=join&confno=123456789", "https://zoom.us/wc/join/123456789"),
    ("zoommtg://zoom.us@evil.com/join?confno=123456789", "https://zoom.us/wc/join/123456789"),
    ("zoommtg://evil.com\\.zoom.us/join?confno=123456789", "https://zoom.us/wc/join/123456789"),
    ("zoommtg://evil .zoom.us/join?confno=123456789", "https://zoom.us/wc/join/123456789"),
    # no usable meeting number: Zoom's own join page, where it can be typed in
    ("zoommtg://zoom.us/join?action=join&confno=some.name", JOIN),
    ("zoommtg://zoom.us/join?confno=١٢٣٤٥٦٧٨٩", JOIN),
    ("zoommtg://zoom.us/", JOIN),
    ("zoommtg://zoomgov.com/", "https://zoomgov.com/join"),
    ("zoommtg://[zoom.us/join?confno=123456789", JOIN),
    ("zoommtg://zoom／us/join?confno=123456789", JOIN),
]
wrong = [f"{link}\n  gave {zoom.web_address(link)}\n  want {want}" for link, want in CASES
         if zoom.web_address(link) != want]


def opens(link, chrome=None, choice=None, answer=None, may_install=True, zoom_app=False):
    """What opening a link runs, with Chrome installed or not, a remembered choice, and an answer to the question."""
    ran, asked = [], []
    with tempfile.TemporaryDirectory() as tmp:
        zoom.CHOICE = Path(tmp) / "zoom-browser"
        if choice:
            zoom.CHOICE.write_text(choice)
        app = Path(tmp) / "us.zoom.Zoom.desktop"
        if zoom_app:
            app.touch()
        zoom.ZOOM_APP = [app]
        zoom.chrome_command = lambda: chrome
        zoom.ask = lambda *a, **k: asked.append(a) or answer
        zoom.flathub = types.SimpleNamespace(install=lambda *a, **k: 1)
        zoom.start = ran.append
        zoom.open_link(link, may_install)
        remembered = zoom.CHOICE.read_text() if zoom.CHOICE.exists() else ""
        command = [("ZOOMAPP" if w == str(app) else w) for w in ran[0]] if ran else None
    return command, bool(asked), remembered


LINK = "zoommtg://zoom.us/join?action=join&confno=123456789&pwd=p"
PAGE = "https://zoom.us/wc/join/123456789?pwd=p"
CHROME = ["flatpak", "run", "com.google.Chrome"]
FLOWS = [
    ("Chrome installed", dict(chrome=CHROME), (CHROME + [PAGE], False, "")),
    ("no Chrome, picks the usual browser", dict(answer="extra"), (["gio", "open", PAGE], True, "default\n")),
    ("no Chrome, usual browser remembered", dict(choice="default\n"), (["gio", "open", PAGE], False, "default\n")),
    ("no Chrome, install fails", dict(answer="ok"), (["gio", "open", PAGE], True, "")),
    ("no Chrome, Cancel", dict(answer=None), (None, True, "")),
    ("another tool busy: no install offer", dict(may_install=False), (["gio", "open", PAGE], False, "")),
    ("Zoom app installed", dict(chrome=CHROME, zoom_app=True), (["gio", "launch", "ZOOMAPP", LINK], False, "")),
]
wrong += [f"{name}: gave {got}, want {want}" for name, how, want in FLOWS if (got := opens(LINK, **how)) != want]
if wrong:
    sys.exit("ERROR: Zoom links don't open the right way:\n" + "\n".join(wrong))
print(f"Zoom links open the right web address ({len(CASES)} kinds of link) the right way ({len(FLOWS)} situations)")
