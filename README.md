# EvenKeelOS

A desktop that just works. It is a derivative of **Fedora®**, built on Fedora
Silverblue 45, with packages, the updater and Homebrew setup from
[Bluefin](https://projectbluefin.io/).

[![Build](https://github.com/ctsdownloads/EvenKeelOS/actions/workflows/build.yml/badge.svg)](https://github.com/ctsdownloads/EvenKeelOS/actions/workflows/build.yml)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)](#status)
[![Base](https://img.shields.io/badge/base-Fedora%20Silverblue%2045-1f6feb.svg)](https://fedoraproject.org/atomic-desktops/silverblue/)
[![Desktop](https://img.shields.io/badge/desktop-GNOME%20%7C%20Wayland-green.svg)](https://www.gnome.org/)
[![Signed](https://img.shields.io/badge/images-signed%20with%20cosign-lightgrey.svg)](docs/install.md#checking-that-updates-are-real)
[![License](https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg)](LICENSE)

## Contents

<!-- contents -->
- [Status](#status)
- [Who it's for](#who-its-for)
- [How this system works](#how-this-system-works)
- [What's in it](#whats-in-it)
- [System requirements](#system-requirements)
- [Documentation](#documentation)
- [Known limitations](#known-limitations)
- [Source code](#source-code)
- [Credits](#credits)
- [License](#license)
- [Trademarks](#trademarks)
<!-- /contents -->

## Status

> ⚠️ **Alpha.** Something can break on any day, there's no warranty or
> support, and you can roll back with `rpm-ostree rollback`.

A failed image build doesn't update installed computers: they keep the last good build,
and the failure opens an issue in this repository ([how it's built](docs/building.md#how-its-built)).

Not an official Universal Blue or Bluefin product.

## Who it's for

Gaming? Get [Bazzite](https://bazzite.gg/). Cloud-native developer? Get
[Bluefin](https://projectbluefin.io/). Just want a computer that works?
EvenKeelOS.

## How this system works

EvenKeelOS is **image-based**: the system arrives as one tested piece that apps
can't change, so it stays working.

- **Updates** download a new image in the background, used from the next restart.
- **The previous version stays on disk**, so you can go back
  ([Updating and rolling back](docs/install.md#updating-and-rolling-back)).
- **Apps** come from Bazaar or go into a box, and onto the system only when they
  have to.

## What's in it

| Part | Details |
|------|---------|
| Base | [Fedora Silverblue 45](https://fedoraproject.org/atomic-desktops/silverblue/), with Fedora's logos and release packages replaced by the generic ones |
| Packages | firefox, v4l-utils, and the Bluefin packages (xdg-terminal-exec among them) in [`build_files/bluefin-packages.txt`](build_files/bluefin-packages.txt) |
| Updates | Automatic with `uupd`: system, Flatpaks, app boxes and Homebrew, paused for 3 days after an undo. Apps added to the system by name (VPNs, codecs) are also checked daily in their own download sources. See [Updating and rolling back](docs/install.md#updating-and-rolling-back) |
| Automatic rollback | [greenboot](https://github.com/fedora-iot/greenboot-rs): a new version that fails 2 starts in a row (no login screen, no networking, stuck or frozen while starting, a login loop, or something that worked at the last good start now broken) goes back to the previous one by itself, and the next login names what broke. After a failed start it also puts back broken important settings from a copy of /etc saved after the last good start. New installs only. Each case can be tested for real in Wheelhouse. See [Updating and rolling back](docs/install.md#updating-and-rolling-back) |
| Certificate alerts | The certificates the computer trusts for secure websites and connections (Fedora's list and any certificate files added to it) are checked 3 minutes after the session starts and once a day, with no admin rights and no changes to the system. The trusted list is rebuilt at every start from Fedora's current list plus the added files, so certificates Fedora replaces or drops are replaced or dropped here too. A notification and a warning in Wheelhouse, Overview show when one has expired, expires within 30 days, or was removed. See [Wheelhouse](docs/wheelhouse.md#wheelhouse) |
| Homebrew and ujust | As on Bluefin, for terminal users |
| Services on by default | Fedora's defaults, plus Tailscale (idle until you sign in) and Podman's container auto-updates, as on Bluefin |
| Codecs | Not included (patents). The [setup checklist](docs/install.md#first-login) and **Media codecs** in Wheelhouse, Apps offer them, with no password for an admin. See [Media codecs](docs/building.md#media-codecs) |
| Apps from .rpm and .deb files | **Install a package file** in Wheelhouse, Apps puts them in a box; **Remove apps** there takes them out. An .rpm printer driver is recognized wherever the maker puts its files, and offered for the system instead. See [Apps from .rpm and .deb files](docs/apps.md#apps-from-rpm-and-deb-files) |
| Windows programs (.exe and .msi) | Opening one offers a Linux app: the same program's Linux version (Flathub, Fedora or Ubuntu), ArtCraft for Adobe programs, a hand-picked replacement for programs with no Linux version (Office, iTunes, Skype), or an app of the same kind. See [Windows programs](docs/apps.md#windows-programs-exe-and-msi) |
| Zoom meetings | Joining from a Zoom invite opens the meeting in Zoom's web version in Google Chrome; the first time, it offers to install Chrome from Flathub (or use the usual browser). See [Zoom meetings](docs/zoom.md) |
| VPNs | Get a VPN in Wheelhouse adds Mullvad, Proton, IVPN or NordVPN from that company's own download source, which is locked to its signing key and checked at every build. Nothing is installed until you pick one. Downloaded VPN files and Windows VPN installers install it the same way, and it is checked daily for updates. See [VPNs](docs/vpn.md) |
| Flathub | Added on first boot; Fedora's own Flathub entry is removed |
| EvenKeelOS Wheelhouse | One window with a sidebar (Overview, Updates, Apps, Network safety, Shared folders, Disk and startup, Make it yours, Get help) and a search box that finds any tool by name, what it does or its command. It has system updates, automatic updates, firmware, undo the last update, installing and removing apps, media codecs, getting a VPN, network safety, shared folders, disk space and unlock, boot options, BIOS settings, the desktop layout, light and dark on a schedule, a wallpaper slideshow, fonts and text size, problem details, the setup checklist, certificate alerts and the automatic rollback test. Each tool's questions and progress show inside the window. See [Wheelhouse](docs/wheelhouse.md#wheelhouse) |
| Network safety | Every network is Home, Work or Public place, saved with that network, and the banner's color shows which. Public place and Work let nothing in, and folders are shared only on Home. Home lets in apps you run on ports 1025 to 65535, with SSH off. **Let an app in** (from a hand-checked list, Fedora's firewall list and IANA's port list) and **Open a port** let in more, per place, with a warning first on a Public place. See [Network safety](docs/wheelhouse.md#network-safety) |
| Shared folders | Lets other computers on a Home network open folders you pick, like Windows file sharing. Macs, Linux computers and Windows PCs find it by themselves, with no address to type; other computers ask for your user name and a separate sharing password once. It never shares as a guest and works only on Home networks. See [Shared folders](docs/wheelhouse.md#shared-folders) |
| EvenKeelOS guide | How to do things, step by step, in Wheelhouse, Get help: New to EvenKeelOS? (for people coming from Windows), the desktop, files, apps, internet and networks, printing, updates and safety, making it yours, disk and startup, and getting help. Show me buttons open the place a step names, and the back arrow returns to the guide. New to EvenKeelOS? opens at login after the setup checklist until its box is ticked; not after **I already use Linux** in the installer. See [EvenKeelOS guide](docs/guide.md) |
| Boot options | In Wheelhouse, Disk and startup. Switches for common fixes to screen flicker (AMD and Intel), screens that dim on their own, and drive freezes, and a box to add your own kernel settings, like `amdgpu.abmlevel=0`. A setting that could stop the computer starting or weaken its security asks first, and settings the system sets itself are refused. Each change asks for the administrator password every time, makes a new system version (the old one stays as the fallback) and starts at the next restart. See [Boot options](docs/wheelhouse.md#boot-options) |
| Desktop | Teal accent color, with folder icons that follow whatever accent color you pick in Settings, Appearance; 7 EvenKeelOS wallpapers, each with a day picture for light mode and a night one for dark mode; minimize and maximize buttons, no hot corner, battery percentage shown |
| Dock | Firefox, Calendar, Files, Bazaar and Text Editor |
| Logo Menu | The [Logo Menu](https://github.com/Aryan20/Logomenu) extension on the top-left logo: About My System, Activities, App Grid, Bazaar, Resources, Ghostty, Extensions, and Wheelhouse, which the build adds |
| Windows-style layout | Optional, per user: a bottom bar from [Dash to Panel](https://github.com/home-sweet-gnome/dash-to-panel) and a start menu from [ArcMenu](https://gitlab.com/arcmenu/ArcMenu) on the EvenKeelOS logo, opening to the app categories, with Settings, System Update and Wheelhouse. It opens on the desktop at login, with no overview. Pick it in the installer (**Coming from Windows** picks it for you), or switch any time in Wheelhouse, Desktop layout (or `evenkeel-os-layout windows` / `current`), then log out and in |
| Terminal | [Ghostty](https://ghostty.org/), replacing Ptyxis everywhere |
| System monitor | [Resources](https://apps.gnome.org/Resources/) from Flathub; gnome-system-monitor is kept |
| Security | The few helpers that run as root take a fixed set of commands and refuse anything else; every build tests them with hostile input, and the VPN helper takes only the four VPN names, or an app already added to the system. No-password actions are for the person at the computer only, not a remote login or a program running outside the desktop session. Device rules from apps can't open the computer's own disks, or every keyboard and mouse at once (a rule must name the device's maker). See [Apps from .rpm and .deb files](docs/apps.md#apps-from-rpm-and-deb-files) |
| Fingerprint | On where the laptop has a supported reader; enroll in Settings, Users. A password is still set at install |
| Firefox | Mozilla's own home page, no Fedora tile |
| Microphone | Starts at 50% volume; a volume you set is kept |
| Power modes | tuned, as on Fedora, set so a power-mode switch never waits on a running update |
| Default apps | Fedora packages in [`build_files/default-apps.txt`](build_files/default-apps.txt), plus five from Flathub on the first start with internet ([`build_files/flathub-apps.txt`](build_files/flathub-apps.txt)). No email app |
| App store | [Bazaar](https://github.com/kolunmi/bazaar), replacing GNOME Software |
| Utilities folder | Holds Wheelhouse, with every EvenKeelOS tool inside it. Show Apps has no separate icons for them |
| File types | Text files open in Text Editor, .rpm and .deb in Install Package File, .exe and .msi in Windows Program, Flatpak files in Bazaar |
| Login screen and boot menu | EvenKeelOS logo and name, and the teal accent on the login and lock screens. New users get the EvenKeelOS logo as their picture. The live USB and the installed system both work with Secure Boot on, with one shim on the disk, so the firmware adds no extra "Fedora" boot entry |
| Live USB fit check | The live USB's Welcome window checks the computer before you install: start mode and Secure Boot, the disk (including a disk hidden by the BIOS's RAID setting), Wi-Fi (including Broadcom chips with no driver), graphics (NVIDIA runs on the open-source driver; the proprietary one isn't used), sound, memory, camera, Bluetooth and touchpad, each marked fine, limited or a problem, with plain advice. **Save the results** puts them on a second USB stick. See [Install](docs/install.md#from-the-live-usb) |
| Languages | The installer, Wheelhouse, the guide, every EvenKeelOS tool, its menu names and its password prompts are in 68 languages, listed in [`po/LINGUAS`](po/LINGUAS). Dates are written in the order and words of the region picked under Formats in Settings, Region & Language. Dash to Panel, ArcMenu, Logo Menu, Bazaar and Ghostty are translated into the same languages, as are System Update's "What is new" lines; disk sizes, folder names, spell check, dates and Bazaar's app descriptions (where the app's developer wrote them) follow the language too, right after a change. The installer offers only those languages. See [Translations](docs/building.md#translations) |
| fastfetch | Shows the EvenKeelOS logo |

## System requirements

- **Recommended:** 8 GB RAM.

## Documentation

- **[Install](docs/install.md)** - live USB, switching from Silverblue or
  Bluefin, updates, rollback and first login.
- **[Apps from .rpm and .deb files](docs/apps.md)** - installing, removing and
  repairing apps, and Windows programs.
- **[Zoom meetings](docs/zoom.md)** - joining Zoom meetings in the browser, and
  why Chrome.
- **[VPNs](docs/vpn.md)** - getting Mullvad, Proton, IVPN or NordVPN, and how they
  update.
- **[Wheelhouse](docs/wheelhouse.md)** - the one window for updates, apps, disk and startup, and help.
- **[EvenKeelOS guide](docs/guide.md)** - how to do things, step by step, the same as in Wheelhouse.
- **[How it's built](docs/building.md)** - the build, translations, media codecs and the boot
  menu name.

## Known limitations

- If Universal Blue's package repository goes away, builds fail and machines
  stay on the last good image.
- If RPM Fusion falls behind a new Fedora, builds fail until it catches up.
  Machines with the full codecs may then skip an update; nothing breaks.
- Apps from plain .rpm or .deb files don't update by themselves unless the
  package adds its own repository (Chrome and VS Code do).
- Apps that manage disks or hardware as root (GParted) can't do their job in a
  box.

## Source code

This repository is how the image is built. The software in the image comes from
other projects, under their own licenses, with their source available there:

- **Fedora packages** (almost everything): <https://src.fedoraproject.org/>.
  `rpm -q --qf '%{SOURCERPM}\n' <package>` names the source package and
  `dnf download --source <source package>` gets it.
- **Optional codecs** are not in the image. The full ffmpeg set comes from
  [RPM Fusion](https://rpmfusion.org/), source at
  <https://download1.rpmfusion.org/free/fedora/updates/45/SRPMS/>. OpenH264
  comes from Cisco through Fedora's Cisco repository.
- **The updater and Homebrew setup:** <https://github.com/ublue-os/uupd>, built in
  <https://copr.fedorainfracloud.org/coprs/ublue-os/packages/>.
- **Ghostty:** built in <https://copr.fedorainfracloud.org/coprs/scottames/ghostty/>,
  source at <https://github.com/ghostty-org/ghostty>.
- **Locked versions:** the Universal Blue and Ghostty packages, Dash to Panel,
  ArcMenu, Logo Menu and the ISO build tool are locked to exact versions and
  checked daily for newer ones; Dash to Panel must carry Fedora's signature. See
  [Locked versions](docs/building.md#locked-versions).
- **Boot test:** every build starts in a virtual machine and must reach the desktop
  before it's published, with its disk made by
  [bootc-image-builder](https://github.com/osbuild/image-builder), locked to
  one version. See [Boot test](docs/building.md#boot-test). Every Test automatic
  rollback test can also run for real in that virtual machine when a build is
  started by hand. See [Rollback tests](docs/building.md#rollback-tests).
- **Code rules:** every change is checked for one-line comments, no Python
  error dropped without a word (`except: pass`, `suppress`) and no forbidden
  words. See
  [How it's built](docs/building.md#how-its-built).
- **Boot files:** before making them, the build matches the zstd tool to its
  library version, since a Fedora update can bring one without the other. See
  [How it's built](docs/building.md#how-its-built).
- **Logo Menu:** <https://github.com/Aryan20/Logomenu> (GPL-2.0), from
  <https://extensions.gnome.org/extension/4451/logo-menu/>. Changed by the build: its menu gets a
  Wheelhouse entry (`build_files/build.sh`).
- **ArcMenu:** <https://gitlab.com/arcmenu/ArcMenu> (GPL-2.0), from
  <https://extensions.gnome.org/extension/3628/arcmenu/>.
- **Folder icons in the accent color:** <https://github.com/dpejoh/Adwaita-colors>
  (GPL-3.0), built at a pinned commit from Fedora's own Adwaita icons.
- **Everything else** added is in this repository.

Can't find the source for something? Open an issue at
<https://github.com/ctsdownloads/EvenKeelOS/issues>.

## Credits

- [Universal Blue](https://universal-blue.org/), its
  [image-template](https://github.com/ublue-os/image-template), and
  [Bluefin](https://projectbluefin.io/) ([source](https://github.com/ublue-os/bluefin),
  [docs](https://docs.projectbluefin.io/)).
- [Fedora](https://fedoraproject.org/), [bootc](https://bootc.dev/) and
  [rpm-ostree](https://coreos.github.io/rpm-ostree/).
- [cosign](https://github.com/sigstore/cosign), [Homebrew](https://brew.sh/),
  [Tailscale](https://tailscale.com/) and [RPM Fusion](https://rpmfusion.org/).
- [GNOME](https://www.gnome.org/), [Firefox](https://www.mozilla.org/firefox/)
  and [v4l-utils](https://linuxtv.org/wiki/index.php/V4l-utils).
- [winget](https://github.com/microsoft/winget-pkgs)'s program index, the app lists of
  [Flathub](https://flathub.org/), Fedora and Ubuntu, [ArtCraft](https://getartcraft.com/)'s apps, [msitools](https://gitlab.gnome.org/GNOME/msitools)
  and [pefile](https://github.com/erocarrera/pefile), for Windows Program.

## License

**This repository** is [GPL-3.0-or-later](LICENSE), except **files from
Universal Blue's [image template](https://github.com/ublue-os/image-template)**,
which stay [Apache-2.0](LICENSES/Apache-2.0.txt): the `Justfile`,
`Containerfile`, the build workflow and a few settings files. The
live-ISO build in `iso/`, based on Universal Blue's
[titanoboa](https://github.com/ublue-os/titanoboa), is Apache-2.0 too, except the
EvenKeelOS installer (`iso/src/evenkeel-os-installer/`,
`iso/src/evenkeel-os-install-engine`, and their launcher and polkit action),
which is GPL-3.0-or-later.

[`REUSE.toml`](REUSE.toml) lists the license of each file, and the texts are in
[`LICENSES/`](LICENSES).

**The image itself is not under those licenses.** It collects software from
many projects, each under its own license; Fedora explains its licensing at
<https://docs.fedoraproject.org/en-US/legal/>. See [Source code](#source-code).
The optional RPM Fusion codecs are under their own licenses too: ffmpeg GPLv3+,
x264 GPLv2+, x265 GPLv2+ and BSD.

---

## Trademarks

EvenKeelOS is not Fedora and is not affiliated with or endorsed by the Fedora Project or Red Hat. Fedora® is a registered trademark of Red Hat, Inc.
