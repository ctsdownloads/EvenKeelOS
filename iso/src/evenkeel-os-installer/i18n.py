"""The installer's words in the chosen language: the Language screen calls use(), everything else _()."""
import functools
import gettext
import glob
import locale as _locales
import os

import langtable

DOMAIN = "evenkeel-os"
_now = gettext.NullTranslations()
_locale = "en_US.UTF-8"


def use(locale):
    """Show the installer in a locale such as "pt_BR.UTF-8"; English where there is no translation."""
    global _now, _locale
    _now = gettext.translation(DOMAIN, languages=[locale], fallback=True)
    _locale = locale


@functools.cache
def _xkb(locale):
    return gettext.translation("xkeyboard-config", languages=[locale], fallback=True)


def keyboard(name):
    """A keyboard layout's name, as in evdev.xml ("German (no dead keys)"), in the installer's language."""
    return _xkb(_locale).gettext(name)


def language(code):
    """A language or locale ("de", "pt_BR.UTF-8") named in the installer's language."""
    return langtable.language_name(languageId=code, languageIdQuery=_locale) or code


def place(zone):
    """A time zone or region ("Europe/Berlin", "Europe") in the installer's language, as langtable names it."""
    if _locale.startswith("en"):
        return zone.replace("_", " ")
    return (langtable.timezone_name(timezoneId=zone, languageIdQuery=_locale) or zone).replace("_", " ")


def number(value, digits):
    """A number with the installer's language's decimal mark: 1.5 is "1,5" in German."""
    before = _locales.setlocale(_locales.LC_NUMERIC)
    try:
        _locales.setlocale(_locales.LC_NUMERIC, _locale)
        return _locales.format_string(f"%.{digits}f", value)
    except _locales.Error:
        return f"{value:.{digits}f}"
    finally:
        _locales.setlocale(_locales.LC_NUMERIC, before)


def translated(locale):
    """True when EvenKeelOS has a translation a locale would use; a script locale (@latin) needs one in that script."""
    if locale.startswith("en"):
        return True
    found = gettext.find(DOMAIN, languages=[locale])
    return found is not None and ("@" not in locale or "@" in found)


def translations():
    """The locale names EvenKeelOS is translated into, as in /usr/share/locale: "de", "pt_BR", "sr@latin"."""
    return [path.split(os.sep)[-3] for path in glob.glob(f"/usr/share/locale/*/LC_MESSAGES/{DOMAIN}.mo")]


def _(text):
    return _now.gettext(text)


def ngettext(one, many, n):
    return _now.ngettext(one, many, n)


def N_(text):
    """Marks text to translate where it is written down; _() translates it where it is shown."""
    return text
