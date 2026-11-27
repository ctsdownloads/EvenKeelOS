"""Reading an .rpm or .deb, and working out what it needs."""
import io
import os
import platform
import re
import subprocess
import tarfile
from pathlib import Path
from evenkeel_os_ui import _, N_
from evenkeel_os_packages import common, update_notes


class Package:
    def __init__(self, path):
        self.path = Path(path)
        self.kind = ""            # rpm or deb
        self.name = self.version = self.arch = self.nevra = ""
        self.files = []           # normalized paths (/usr/..., no ./)
        self.texts = {}           # path -> text, for udev rules and desktop files
        self.depends = ""         # requirements, as one lowercase string
        self.scripts = ""         # install scripts, as one lowercase string
        self.vendor = ""          # rpm Vendor or deb Maintainer, to name the maker
        self.evr = ""             # rpm epoch:version-release, or the deb version


def norm(p):
    p = "/" + p.lstrip("./").lstrip("/") if p not in (".", "./") else "/"
    for old, new in (("/lib/", "/usr/lib/"), ("/lib64/", "/usr/lib64/"), ("/bin/", "/usr/bin/"),
                     ("/sbin/", "/usr/sbin/")):
        if p.startswith(old):
            p = new + p[len(old):]
    return p.rstrip("/") or "/"


def wanted_text(p):
    base = os.path.basename(p)
    return (p.endswith(".rules") and "/udev/rules.d/" in p) or p.endswith(".desktop") \
        or bool(update_notes.REPO_FILE.match(p)) \
        or p.endswith((".metainfo.xml", ".appdata.xml")) or base in ("Makefile", "Kbuild") or \
        p.startswith(("/usr/lib/systemd/system-preset/", "/usr/lib/systemd/user-preset/")) or \
        (p.startswith("/usr/share/polkit-1/actions/") and p.endswith(".policy"))


def read_tar(pkg, fileobj, mode):
    links = {}
    with tarfile.open(fileobj=fileobj, mode=mode) as tar:
        for m in tar:
            p = norm(m.name)
            if m.isdir():
                continue
            pkg.files.append(p)
            if m.issym():
                links[p] = m.linkname
            elif m.isfile() and wanted_text(p) and m.size < 256 * 1024:
                pkg.texts[p] = tar.extractfile(m).read().decode("utf-8", "replace")
    # a launcher or rule that is a link to a file elsewhere in the package (Discord does this)
    for p, target in links.items():
        if wanted_text(p):
            real = target if target.startswith("/") else os.path.normpath(os.path.join(os.path.dirname(p), target))
            if norm(real) in pkg.texts:
                pkg.texts[p] = pkg.texts[norm(real)]


def read_rpm(pkg):
    def q(*args):
        r = subprocess.run(["rpm", "-qp", "--nosignature", "--nodigest", *args, str(pkg.path)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise ValueError(r.stderr.strip() or _("rpm could not read it"))
        return r.stdout
    info = q("--qf", "%{NAME}\n%{VERSION}-%{RELEASE}\n%{ARCH}\n%{VENDOR}\n%{EPOCHNUM}\n").split("\n")
    pkg.kind, pkg.name, pkg.version, pkg.arch, pkg.vendor = "rpm", info[0], info[1], info[2], info[3]
    pkg.evr = f"{info[4] or 0}:{pkg.version}"
    pkg.nevra = f"{pkg.name}-{pkg.version}.{pkg.arch}"
    pkg.depends = q("--requires").lower()
    pkg.scripts = q("--scripts").lower()
    proc = subprocess.Popen(["rpm2archive", "-n", "-"], stdin=open(pkg.path, "rb"), stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL)
    read_tar(pkg, proc.stdout, "r|")
    proc.stdout.close()
    proc.wait()


def read_deb(pkg):
    data = control = None
    with open(pkg.path, "rb") as f:
        if f.read(8) != b"!<arch>\n":
            raise ValueError(_("it is not a .deb package"))
        while True:
            head = f.read(60)
            if len(head) < 60:
                break
            name = head[:16].decode().strip().rstrip("/")
            size = int(head[48:58].decode().strip())
            body = f.read(size)
            if size % 2:
                f.read(1)
            if name.startswith("control.tar"):
                control = body
            elif name.startswith("data.tar"):
                data = body
    if control is None or data is None:
        raise ValueError(_("the .deb is incomplete"))
    fields, scripts = {}, []
    with tarfile.open(fileobj=io.BytesIO(control), mode="r:*") as tar:
        for m in tar:
            base = os.path.basename(m.name)
            if not m.isfile():
                continue
            text = tar.extractfile(m).read().decode("utf-8", "replace")
            if base == "control":
                for k, v in re.findall(r"^([A-Za-z-]+):[ \t]*(.*(?:\n[ \t].*)*)", text, re.M):
                    fields[k.lower()] = v
            elif base in ("preinst", "postinst", "prerm", "postrm"):
                scripts.append(text)
    pkg.kind = "deb"
    pkg.name = fields.get("package", "").strip()
    pkg.version = fields.get("version", "").strip()
    pkg.arch = fields.get("architecture", "").strip()
    pkg.vendor = fields.get("maintainer", "").strip()
    pkg.evr = pkg.version
    pkg.depends = " ".join(fields.get(k, "") for k in ("depends", "pre-depends")).lower()
    pkg.scripts = "\n".join(scripts).lower()
    read_tar(pkg, io.BytesIO(data), "r:*")
    if not pkg.name:
        raise ValueError(_("the .deb has no package name"))


def read_package(path):
    pkg = Package(path)
    with open(path, "rb") as f:
        magic = f.read(8)
    if magic.startswith(b"\xed\xab\xee\xdb"):
        read_rpm(pkg)
    elif magic == b"!<arch>\n":
        read_deb(pkg)
    else:
        raise ValueError(_("it is not an .rpm or .deb package"))
    return pkg


# ---------------------------------------------------------------- what the package needs

def desktop_entry(text):
    """(visible, name) for a .desktop file."""
    sect, fields = None, {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("["):
            sect = line
        elif sect == "[Desktop Entry]" and "=" in line:
            k, v = line.split("=", 1)
            fields.setdefault(k.strip(), v.strip())
    visible = fields.get("Type", "Application") == "Application" and \
        fields.get("NoDisplay", "").lower() != "true" and fields.get("Hidden", "").lower() != "true"
    return visible, fields.get("Name", "")


RUNS_PROGRAM = re.compile(r"\bRUN\b(?!\{builtin\})|\bPROGRAM\b|IMPORT\{program\}")   # RUN{builtin} stays in udev


def rule_runs_program(text):
    joined = re.sub(r"\\\n", " ", text)
    return any(RUNS_PROGRAM.search(line) for line in joined.splitlines() if not line.lstrip().startswith("#"))


# Printer description, filter or driver files, not docs or examples; ADDS_PRINTER matches an install script's lpadmin.
PRINTER_FILE = re.compile(r"\.ppd(\.gz|\.bz2)?$|/cups/(lib/)?(filter|backend)/[^/]+$|/lpd/[^/]*filter[^/]*$|"
                          r"/cupswrapper/[^/]+$|/[^/]*printfilter[^/]*$|/(cups|ppds?)/.*\.drv(\.gz)?$", re.I)
NOT_PRINTER = re.compile(r"/(doc|docs|examples?|samples?)/", re.I)
ADDS_PRINTER = re.compile(r"^\s*(?!#)(.*[\s;|&(/])?lpadmin\s(.*\s)?-p\s", re.M)


def starts(p, *prefixes):
    return any(p.startswith(x) for x in prefixes)


def classify(pkg):
    """What the package has that a box cannot provide, in plain words."""
    files = pkg.files
    apps = {}
    for p in files:
        if p.startswith("/usr/share/applications/") and p.endswith(".desktop") and p in pkg.texts:
            visible, name = desktop_entry(pkg.texts[p])
            if visible:
                apps[p] = name or os.path.basename(p)[:-8]
    rules = {p: pkg.texts.get(p, "") for p in files if "/udev/rules.d/" in p and p.endswith(".rules")}
    safe_rules = {p: t for p, t in rules.items() if t and not rule_runs_program(t)}
    program_rules = [p for p in rules if p not in safe_rules]

    found = {}

    def flag(key, test):
        if any(test(p) for p in files):
            found[key] = True

    flag("driver", lambda p: starts(p, "/usr/lib/modules/", "/usr/src/akmods/", "/etc/modprobe.d/",
                                    "/usr/lib/modprobe.d/", "/etc/modules-load.d/", "/usr/lib/modules-load.d/",
                                    "/etc/dkms/")
         or re.search(r"\.ko(\.(xz|zst|gz))?$", p) or (p.startswith("/usr/src/") and p.endswith("/dkms.conf")))
    if re.search(r"(^|[\s,(])(dkms|akmods|kernel-devel|linux-headers[\w.-]*)([\s,()]|$)", pkg.depends):
        found["driver"] = True
    # driver source built when the package is installed (VirtualBox does this): a kernel module makefile
    if any(t for p, t in pkg.texts.items() if os.path.basename(p) in ("Makefile", "Kbuild") and "obj-m" in t):
        found["driver"] = True
    if re.search(r"(^|[\s;|&(])(modprobe|insmod|depmod|dkms)\s", pkg.scripts):
        found["driver"] = True
    flag("firmware", lambda p: p.startswith("/usr/lib/firmware/"))
    # Printer drivers by what they hold, in any folder: makers like Epson and Lexmark use /opt or /usr/local.
    flag("printer", lambda p: starts(p, "/usr/lib/cups/", "/usr/share/cups/model/", "/usr/share/cups/drv/",
                                     "/usr/share/ppd/") or (PRINTER_FILE.search(p) and not NOT_PRINTER.search(p)))
    if ADDS_PRINTER.search(pkg.scripts):
        found["printer"] = True
    flag("scanner", lambda p: starts(p, "/etc/sane.d/") or re.match(r"/usr/lib(64)?/(x86_64-linux-gnu/)?sane/", p))
    flag("login", lambda p: starts(p, "/etc/pam.d/", "/usr/lib/pam.d/", "/etc/security/", "/etc/sudoers.d/",
                                   "/etc/selinux/", "/usr/share/selinux/")
         or re.match(r"/usr/lib(64)?/(x86_64-linux-gnu/)?security/", p))
    flag("network", lambda p: starts(p, "/usr/lib/NetworkManager/", "/usr/lib64/NetworkManager/",
                                     "/etc/NetworkManager/", "/usr/lib/firewalld/", "/etc/firewalld/"))
    flag("service", lambda p: (starts(p, "/usr/lib/systemd/system/", "/etc/systemd/system/")
                               and re.search(r"\.(service|socket|timer|path)$", p))
         or starts(p, "/etc/init.d/", "/usr/share/dbus-1/system-services/", "/usr/share/dbus-1/system.d/",
                   "/etc/dbus-1/system.d/"))
    # Services the package's install script turns on are needed; preset ones are optional.
    units = [os.path.basename(p) for p in files if (starts(p, "/usr/lib/systemd/system/", "/etc/systemd/system/")
             and re.search(r"\.(service|socket|timer|path)$", p)) or p.startswith("/etc/init.d/")]
    user_units = [os.path.basename(p) for p in files
                  if p.startswith("/usr/lib/systemd/user/") and p.endswith(".service")]
    presets = "\n".join(t for p, t in pkg.texts.items() if "/systemd/system-preset/" in p)
    turned_on = script_on = False      # script_on: the script itself does it, which this system ignores
    for line in pkg.scripts.splitlines():
        line = line.strip()
        if line.startswith("#"):
            continue
        user = bool(re.search(r"--user\b|--global\b", line))
        if re.search(r"\bsystemctl\b.*\b(enable|start|restart|reenable)\b", line):
            if (units and not user) or (user_units and user):
                turned_on = True
                script_on = script_on or (not user and bool(re.search(r"\b(enable|reenable)\b", line)))
        elif user and user_units and re.search(r"\bsystemctl\b.*\bdaemon-reload\b", line):
            turned_on = True        # reload so its own service can start (Docker Desktop)
    if re.search(r"^\s*enable\s", presets, re.M):
        turned_on = True
    # Apps that run as root (pkexec or sudo) can't work in a box.
    own = set(files)
    root_programs = [m for p, t in pkg.texts.items() if p.startswith("/usr/share/polkit-1/actions/")
                     for m in re.findall(r"org\.freedesktop\.policykit\.exec\.path\">\s*([^<\s]+)", t)
                     if norm(m) in own]
    root_exec = re.compile(r"(?m)^Exec=\s*(\S*/)?(pkexec|sudo|gksu|gksudo|kdesu|su-to-root)\b")
    root_launch = any(root_exec.search(pkg.texts.get(p, "")) for p in apps)
    if turned_on:
        found["needed_service"] = True
    elif user_units:
        found["user_service"] = True
    flag("settings", lambda p: starts(p, "/usr/lib/sysctl.d/", "/etc/sysctl.d/", "/usr/lib/udev/hwdb.d/",
                                      "/etc/udev/hwdb.d/"))
    flag("admin", lambda p: starts(p, "/usr/share/polkit-1/", "/etc/polkit-1/"))

    words = {
        "driver": N_("a driver (kernel module)"),
        "firmware": N_("device firmware"),
        "printer": N_("a printer driver"),
        "scanner": N_("a scanner driver"),
        "login": N_("login or security settings"),
        "network": N_("a network or VPN plugin for the system"),
        "service": N_("a background service that starts with the computer"),
        "needed_service": N_("a background service the app needs, which cannot run in a box"),
        "user_service": N_("a background service for your account (in a box it does not start)"),
        "programrules": N_("a hardware rule that runs a program"),
    }
    if program_rules:
        found["programrules"] = True
    blocking = [words[k] for k in ("driver", "firmware", "printer", "scanner", "login", "network") if k in found]
    notes = []
    if "needed_service" in found:
        blocking.append(words["needed_service"])
    elif "service" in found:
        (notes if apps else blocking).append(words["service"])
    if "user_service" in found:
        notes.append(words["user_service"])
    if "programrules" in found:
        (notes if apps else blocking).append(words["programrules"])
    if "settings" in found:
        notes.append(N_("system settings (these will not apply)"))
    if "admin" in found:
        notes.append(N_("parts that need administrator rights (these may not work)"))

    docs = ("/usr/share/doc/", "/usr/share/licenses/", "/usr/share/man/", "/usr/share/metainfo/",
            "/usr/share/appdata/", "/usr/lib/.build-id/", "/usr/share/lintian/")
    rules_only = bool(safe_rules) and not blocking and \
        all(p in safe_rules or starts(p, *docs) for p in files)
    # a package that only adds a download source (a repository) and its signing key, and no app
    keys = ("/etc/pki/rpm-gpg/", "/usr/share/distribution-gpg-keys/", "/etc/apt/trusted.gpg.d/", "/etc/apt/keyrings/",
            "/usr/share/keyrings/", "/etc/debsig/", "/usr/share/debsig/")
    repo_files = {p: t for p, t in pkg.texts.items() if update_notes.REPO_FILE.match(p)}
    source_only = bool(repo_files) and not blocking and \
        all(update_notes.REPO_FILE.match(p) or starts(p, *keys, *docs) for p in files)
    bins = sorted(p for p in files if re.match(r"/usr/bin/[^/]+$", p))[:10]
    # One app: its own name; several: the package name.
    title = next(iter(apps.values())) if len(apps) == 1 else pkg.name.capitalize() if apps else pkg.name
    return {"apps": apps, "bins": bins, "safe_rules": safe_rules, "blocking": blocking, "notes": notes,
            "rules_only": rules_only, "source_only": source_only,
            "needs_root": bool(apps) and bool(root_programs or root_launch), "turns_on": script_on,
            "sources": source_names(repo_files, pkg.kind),
            "title": title}


def source_names(repo_files, kind):
    """The download sources a package adds: [(id, name, enabled)], from its .repo, .list or .sources files."""
    out = []
    for p, text in repo_files.items():
        if kind == "rpm" and p.endswith(".repo"):
            for m in re.finditer(r"^\[([^\]]+)\]\s*\n((?:(?!\[).*\n?)*)", text, re.M):
                body = m.group(2)
                name = re.search(r"^name\s*=\s*(.*)$", body, re.M)
                on = re.search(r"^enabled\s*=\s*(\S+)", body, re.M)
                out.append((m.group(1).strip(), (name.group(1).strip() if name else m.group(1)).replace(
                    "$releasever", common.fedora_version()).replace("$basearch", platform.machine()),
                    not on or on.group(1) not in ("0", "false", "no")))
        else:
            for m in re.finditer(r"^\s*deb\s+(?:\[[^\]]*\]\s+)?(\S+)|^URIs:\s*(\S+)", text, re.M):
                url = m.group(1) or m.group(2)
                out.append((url, re.sub(r"^\w+://", "", url).split("/")[0], True))
    return out
