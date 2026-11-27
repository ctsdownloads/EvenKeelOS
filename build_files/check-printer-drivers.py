#!/usr/bin/python3 -I
"""Build check: printer drivers laid out like real ones are added to the system, not put in an app box."""
import sys

sys.path.insert(0, sys.argv[1])
from evenkeel_os_packages import reading  # noqa: E402


def package(name, files, scripts=""):
    pkg = reading.Package(f"/nowhere/{name}.rpm")
    pkg.name, pkg.files, pkg.scripts = name, files, scripts
    return pkg


PRINTER = "a printer driver"
cases = [
    # Epson's own ESC/P-R packages: filter and printer files under /opt
    ("Epson, under /opt", True, package("epson-inkjet-printer-escpr2", [
        "/opt/epson-inkjet-printer-escpr2/cups/lib/filter/epson-escpr2",
        "/opt/epson-inkjet-printer-escpr2/cups/lib/filter/epson-escpr-wrapper2",
        "/opt/epson-inkjet-printer-escpr2/ppds/Epson/Epson-ET-2850_Series-epson-inkjet-printer-escpr2.ppd.gz"])),
    # Lexmark's older packages: a print filter under /usr/local/lexmark
    ("Lexmark filter, under /usr/local", True, package("lexmark-legacy-wJRE-driver", [
        "/usr/local/lexmark/legacy/bin/printfilter", "/usr/local/lexmark/legacy/etc/lxk.conf"])),
    ("an install step that adds a printer", True, package("printer-setup", ["/opt/maker/bin/setup"],
                                                          "if [ -x /usr/sbin/lpadmin ]; then\n  /usr/sbin/lpadmin -p "
                                                          "office -e\nfi")),
    # Brother's older pair of packages: the lpr one (a filter under lpd/) and the cupswrapper one
    ("Brother lpr, under /opt", True, package("hl2270dwlpr", ["/opt/brother/Printers/HL2270DW/lpd/filterHL2270DW"])),
    ("Brother cupswrapper, under /opt", True, package("hl2270dwcupswrapper", [
        "/opt/brother/Printers/HL2270DW/cupswrapper/brother_lpdwrapper_HL2270DW"])),
    ("Lexmark printer files only", True, package("lexmark-ppd-files", ["/opt/lexmark/ppd/Lexmark_CX725_en.ppd"])),
    ("the usual printer folders", True, package("hplip-hpcups", ["/usr/lib/cups/filter/hpcups"])),
    ("an ordinary app", False, package("gnome-mines", [
        "/usr/bin/gnome-mines", "/usr/share/applications/org.gnome.Mines.desktop"])),
    ("an app with a Windows .drv file", False, package("wine-tool", ["/opt/wine-tool/lib/sound.drv"])),
    ("an app with an example printer file in its docs", False, package("pdf-tool", [
        "/usr/bin/pdf-tool", "/usr/share/doc/pdf-tool/examples/generic.ppd"])),
    ("an app that only adds you to the printer admin group", False, package("print-helper", ["/usr/bin/print-helper"],
                                                                             "getent group lpadmin >/dev/null && "
                                                                             "usermod -a -g lpadmin user\n"
                                                                             "# lpadmin -p old -e")),
]
problems = []
for label, want, pkg in cases:
    got = PRINTER in reading.classify(pkg)["blocking"]
    if got != want:
        problems.append(f"{label} ({pkg.name}): {'seen' if got else 'not seen'} as a printer driver")
if problems:
    print("ERROR: printer drivers are not recognized:", *problems, sep="\n  ")
    sys.exit(1)
print(f"Printer drivers recognized in any folder: {len(cases)} cases right")
