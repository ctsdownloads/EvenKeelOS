"""The installer's words in the chosen language: the Language screen calls use(), everything else _()."""
import contextlib
import functools
import gettext
import glob
import locale as pylocale
import os
import sys

import langtable

sys.path.insert(0, "/usr/lib/evenkeel-os")
import evenkeel_os_ui  # noqa: E402

N_ = evenkeel_os_ui.N_          # the screens import it from here, with _
DOMAIN = "evenkeel-os"
_now = gettext.NullTranslations()
_current = "en_US.UTF-8"


def use(loc):
    """Show the installer in a locale such as "pt_BR.UTF-8"; English where there is no translation."""
    global _now, _current
    _now = gettext.translation(DOMAIN, languages=[loc], fallback=True)
    _current = loc


@contextlib.contextmanager
def in_locale(category, loc):
    """Read one part of a locale (LC_TIME, LC_NUMERIC) for a moment; locale.Error when it isn't on this system."""
    before = pylocale.setlocale(category)
    try:
        pylocale.setlocale(category, loc)
        yield
    finally:
        pylocale.setlocale(category, before)


@functools.cache
def _xkb(loc):
    return gettext.translation("xkeyboard-config", languages=[loc], fallback=True)


def keyboard(name):
    """A keyboard layout's name, as in evdev.xml ("German (no dead keys)"), in the installer's language."""
    return _xkb(_current).gettext(name)


def language(code):
    """A language or locale ("de", "pt_BR.UTF-8") named in the installer's language."""
    return langtable.language_name(languageId=code, languageIdQuery=_current) or code


def place(zone):
    """A time zone or region ("Europe/Berlin", "Europe") in the installer's language, as langtable names it."""
    if _current.startswith("en"):
        return zone.replace("_", " ")
    return (langtable.timezone_name(timezoneId=zone, languageIdQuery=_current) or zone).replace("_", " ")


def number(value, digits):
    """A number with the installer's language's decimal mark: 1.5 is "1,5" in German."""
    try:
        with in_locale(pylocale.LC_NUMERIC, _current):
            return pylocale.format_string(f"%.{digits}f", value)
    except pylocale.Error:
        return f"{value:.{digits}f}"


def translated(loc):
    """True when EvenKeelOS has a translation a locale would use; a script locale (@latin) needs one in that script."""
    if loc.startswith("en"):
        return True
    found = gettext.find(DOMAIN, languages=[loc])
    return found is not None and ("@" not in loc or "@" in found)


def translations():
    """The locale names EvenKeelOS is translated into, as in /usr/share/locale: "de", "pt_BR", "sr@latin"."""
    return [path.split(os.sep)[-3] for path in glob.glob(f"/usr/share/locale/*/LC_MESSAGES/{DOMAIN}.mo")]


def _(text):
    return _now.gettext(text)
