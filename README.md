# EvenKeelOS

A desktop that just works. It is a derivative of **Fedora®**, built on Fedora
Silverblue 45, with packages, the updater and Homebrew setup from
[Bluefin](https://projectbluefin.io/).

[![Build](https://github.com/ctsdownloads/evenkeel-os/actions/workflows/build.yml/badge.svg)](https://github.com/ctsdownloads/evenkeel-os/actions/workflows/build.yml)
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
| Packages | firefox, v4l-utils, xdg-terminal-exec, and the Bluefin packages in [`build_files/bluefin-packages.txt`](build_files/bluefin-packages.txt) |
| Updates | Automatic with `uupd`: system, Flatpaks, app boxes and Homebrew, paused for 3 days after an undo. See [Updating and rolling back](docs/install.md#updating-and-rolling-back) |
| Automatic rollback | [greenboot](https://github.com/fedora-iot/greenboot-rs): if a new version doesn't start properly 3 times (login screen or networking), the computer goes back to the previous one by itself and says so. Offline never counts. New installs only. Test it in System Tools |
| Homebrew and ujust | As on Bluefin, for terminal users |
| Services on by default | Fedora's defaults, plus Tailscale (idle until you sign in) and Podman's container auto-updates, as on Bluefin |
| Codecs | Not included (patents). The [setup checklist](docs/install.md#first-login) and **Install Media Codecs** offer them, with no password for an admin. See [Media codecs](docs/building.md#media-codecs) |
| Apps from .rpm and .deb files | **Install Package File** puts them in a box; **Remove Apps** takes them out. See [Apps from .rpm and .deb files](docs/apps.md#apps-from-rpm-and-deb-files) |
| Flathub | Added on first boot; Fedora's own Flathub entry is removed |
| System Tools | Firmware, disk unlock, free space, BIOS settings, automatic updates, undo the last update, problem details, the setup checklist, the desktop layout, and the automatic rollback test. See [System Tools](docs/system-tools.md#system-tools) |
| Desktop | Minimize and maximize buttons, no hot corner, battery percentage shown |
| Dock | Firefox, Calendar, Files, Bazaar and Text Editor |
| Logo Menu | The [Logo Menu](https://github.com/Aryan20/Logomenu) extension on the top-left logo: About My System, Activities, App Grid, Bazaar, Resources, Ghostty, Extensions |
| Windows-style layout | Optional, per user: a bottom bar from [Dash to Panel](https://github.com/home-sweet-gnome/dash-to-panel) and a start menu from [ArcMenu](https://gitlab.com/arcmenu/ArcMenu) on the EvenKeelOS logo, opening to the app categories, with Settings, System Update and System Tools. It opens on the desktop at login, with no overview. Pick it in the installer, or switch any time in System Tools, Desktop layout (or `evenkeel-os-layout windows` / `current`), then log out and in |
| Terminal | [Ghostty](https://ghostty.org/), replacing Ptyxis everywhere |
| System monitor | [Resources](https://apps.gnome.org/Resources/) from Flathub; gnome-system-monitor is kept |
| Fingerprint | On where the laptop has a supported reader; enroll in Settings, Users. A password is still set at install |
| Firefox | Mozilla's own home page, no Fedora tile |
| Microphone | Starts at 50% volume; a volume you set is kept |
| Power modes | tuned, as on Fedora, set so a power-mode switch never waits on a running update |
| Default apps | Fedora packages in [`build_files/default-apps.txt`](build_files/default-apps.txt), plus five from Flathub on the first start with internet ([`build_files/flathub-apps.txt`](build_files/flathub-apps.txt)). No email app |
| App store | [Bazaar](https://github.com/kolunmi/bazaar), replacing GNOME Software |
| Utilities folder | Every EvenKeelOS tool, in Show Apps |
| File types | Text files open in Text Editor, .rpm and .deb in Install Package File, Flatpak files in Bazaar |
| Login screen and boot menu | EvenKeelOS logo and name. The live USB and the installed system both work with Secure Boot on |
| fastfetch | Shows the EvenKeelOS logo |

## System requirements

- **Minimum:** 8 GB RAM.
- **Recommended:** 16 GB RAM, especially with apps in boxes.

## Documentation

- **[Install](docs/install.md)** - live USB, switching from Silverblue or
  Bluefin, updates, rollback and first login.
- **[Apps from .rpm and .deb files](docs/apps.md)** - installing, removing and
  repairing apps.
- **[System Tools](docs/system-tools.md)** - the system jobs, in windows.
- **[How it's built](docs/building.md)** - the build, media codecs and the boot
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
- **Logo Menu:** <https://github.com/Aryan20/Logomenu> (GPL-2.0), from
  <https://extensions.gnome.org/extension/4451/logo-menu/>.
- **ArcMenu:** <https://gitlab.com/arcmenu/ArcMenu> (GPL-2.0), from
  <https://extensions.gnome.org/extension/3628/arcmenu/>.
- **Everything else** added is in this repository.

Can't find the source for something? Open an issue at
<https://github.com/ctsdownloads/evenkeel-os/issues>.

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

## License

**This repository** is [GPL-3.0-or-later](LICENSE), except **files from
Universal Blue's [image template](https://github.com/ublue-os/image-template)**,
which stay [Apache-2.0](LICENSES/Apache-2.0.txt): the `Justfile`,
`Containerfile`, build workflows, `disk_config/` and a few settings files. The
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
