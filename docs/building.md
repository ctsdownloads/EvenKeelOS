# How it's built

[Back to the EvenKeelOS README](../README.md)

## How it's built

[GitHub Actions](../.github/workflows/build.yml) builds and signs the image on
every push (except writing-only changes) and daily at 10:05 UTC, from the latest
Fedora Silverblue 44, and publishes it to `ghcr.io/ctsdownloads/evenkeel-os`.

| Path | Purpose |
|------|---------|
| `Containerfile`, `build_files/build.sh` | Start from `silverblue:44`, install everything, run the checks |
| `build_files/bluefin-packages.txt` | Fedora packages carried over from Bluefin |
| `build_files/default-apps.txt`, `flathub-apps.txt`, `evenkeel-os-flathub-apps`, `evenkeel-os-flatpak-apps.service`, `evenkeel-os-flathub.service`, `flathub.flatpakrepo` | Default apps, and the Flathub ones installed at the first start with internet |
| `build_files/evenkeel_os_ui.py` | Windows, notices and disk sizes shared by System Tools and Install Package File |
| `build_files/evenkeel-os-update`, `evenkeel-os-update-helper` | **System Update**, and its Python helper for progress text and what's new |
| `build_files/evenkeel-os-packages`, `evenkeel_os_packages/`, `evenkeel-os-box-run`, `evenkeel-os-hwrules` | **Install Package File**, **Remove Apps**, **Repair App Boxes**, **Start Apps at Login**, and their helpers |
| `build_files/evenkeel-os-tools`, `-admin`, `-safe` | **System Tools** and its two root helpers |
| `build_files/evenkeel-os-codecs`, `-setup`, `-admin`, `-lib.sh`, `rpmfusion-*.repo` | **Install Media Codecs** and its helpers |
| `build_files/*.policy`, `*.rules` | polkit actions and the narrow no-password rules |
| `build_files/*.gschema.override`, `*.dconf`, `gnome-mimeapps.list`, `xdg-terminals.list`, `60-evenkeel-os-mic.conf` | Desktop defaults |
| `build_files/rebrand.sh`, `initramfs.sh`, `evenkeel-os-boot-label` | EvenKeelOS name and logo, and the boot menu rename |
| `build_files/check-*.py` | Build tests: packages are read correctly, docs keep up |
| `iso/` | The live USB and its installer. `iso/build-local-iso.sh` builds a test ISO locally; `iso/verify-image.sh` checks the built images |
| `system_files/` | Files copied into the image |
| `cosign.pub` | Public key for verifying the image |

**The build fails, and nothing is published,** if:

- Fedora's logos or release packages remain, or the boot image can't unlock a
  disk;
- GNOME Software is still there, Bazaar is missing, a tool is missing from
  Utilities, or text files wouldn't open in Text Editor;
- a default service is off, tuned isn't Bluefin's version, or RPM Fusion's codecs
  wouldn't install;
- Install Package File misreads four real Fedora packages.

A separate docs check fails when the README's contents table or a link is out of
date.

A failed signing step leaves an unsigned image that a signed rebase rejects.

Fedora's service presets are kept through the rebrand. Universal Blue's package
repository is used only during the build.

## Media codecs

Some formats (H.264, H.265) are covered by patents in some countries, so Fedora
and this image leave them out. Adding them is your choice and your
responsibility.

The [setup checklist](install.md#first-login) offers **Web video only**,
**Everything** or **Not now**. **Install Media Codecs** in Show Apps opens the
same window any time, or in a terminal:

    codecs          # explains the options, changes nothing
    codecs web      # web video in Firefox only
    codecs full     # the full ffmpeg set
    codecs remove   # takes them out again

- **Web video only:** Cisco's OpenH264 replaces Fedora's empty stand-in, under
  Cisco's own patent license.
- **Everything:** the full ffmpeg, x264 and x265 from
  [RPM Fusion](https://rpmfusion.org/), with its key (fingerprint
  `E9A4 91A3 DE24 7814 E7E0 67EA E06F 8ECD D651 FF2E`) from Fedora's
  `distribution-gpg-keys`. Updates take a little longer after.

### Passwords

Adding needs no password: one narrow polkit rule, for an admin at the computer,
accepting only `web`, `full` or `skip`, installing a fixed list. Removing asks
for the admin password. To always be asked, override the rule with an empty file
of the same name in `/etc/polkit-1/rules.d/`.

Restart afterwards. `rpm-ostree rollback` undoes it.

## Boot menu name

New installs from the live USB show EvenKeelOS in the boot menu. The live USB
has no Fedora boot files, so it needs Secure Boot off (see
[From the live USB](install.md#from-the-live-usb)). Older installs keep their
old name ("Fedora", "Generic", "bluefin"), which lives in the firmware. To
rename it:

    sudo evenkeel-os-boot-label          # shows what would change
    sudo evenkeel-os-boot-label --apply  # makes the change
