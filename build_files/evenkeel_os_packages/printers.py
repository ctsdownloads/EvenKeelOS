"""Printer drivers."""
import re

from evenkeel_os_ui import _, ask, launch, say


MAKERS = ["Brother", "Canon", "Epson", "HP", "Samsung", "Xerox", "Lexmark", "Ricoh", "Kyocera", "Konica Minolta",
          "OKI", "Sharp", "Pantum", "Dell", "Fujifilm", "Toshiba"]


def maker(pkg):
    """The printer maker named in the package, or ''."""
    name, vendor = pkg.name.lower(), f" {pkg.vendor} ".lower().replace("hewlett", " hp ")
    for m in MAKERS:
        w = re.escape(m.split()[0].lower())
        # Name may start a word; vendor must match a whole word (Canonical isn't Canon).
        if re.search(rf"(^|[^a-z]){w}", name) or re.search(rf"[^a-z]{w}[^a-z]", vendor):
            return m
    return ""


def open_printers():
    """True when Printers opened."""
    try:
        launch(["gnome-control-center", "printers"])
        return True
    except OSError:
        say(_("Printers didn't open. Open Settings, then Printers."), kind="error")
        return False


def try_driverless(title, kind):
    """Most printers need no driver. Offer to add the printer first. Returns 'printers', 'driver' or None."""
    extra = _("Install the driver") if kind == "rpm" else _("About this driver")
    answer = ask(_("{title} is a printer driver. Most printers work without one.\n\n"
                   "Recommended: Open Printers, and add your printer there first.\n\n"
                   "Or {extra}: only if your printer doesn't work without it.").format(title=title, extra=extra),
                 ok=_("Open Printers"), extra=extra)
    if answer == "ok":
        if open_printers():
            if kind == "rpm":
                say(_("Printers is open. Choose Add Printer.\n\nIf your printer isn't there or doesn't print right, "
                      "open this file again and choose Install the driver."))
            else:
                say(_("Printers is open. Choose Add Printer.\n\nIf your printer isn't there or doesn't print right, "
                      "open this file again to see how to get the driver."))
        return "printers"
    return "driver" if answer == "extra" else None
