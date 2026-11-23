# How it's built

[Back to the EvenKeelOS README](../README.md)

## How it's built

[GitHub Actions](../.github/workflows/build.yml) builds and signs the image on
every push (except writing-only changes) and daily at 10:05 UTC, from the latest
Fedora Silverblue 45, and publishes it to `ghcr.io/ctsdownloads/evenkeel-os`.

| Path | Purpose |
|------|---------|
| `Containerfile`, `build_files/build.sh` | Start from `silverblue:45`, install everything, run the checks |
| `build_files/bluefin-packages.txt` | Fedora packages carried over from Bluefin |
| `build_files/default-apps.txt`, `flathub-apps.txt`, `evenkeel-os-flathub-apps`, `evenkeel-os-flatpak-apps.service`, `evenkeel-os-flathub.service`, `flathub.flatpakrepo` | Default apps, and the Flathub ones installed at the first start with internet |
| `build_files/evenkeel_os_ui.py` | Windows, notices and disk sizes shared by System Tools and Install Package File |
| `boot_test/run-boot-test.sh`, `boot_test/boot-check`, `boot_test/boot-check-root`, `boot_test/Containerfile` | The [boot test](#boot-test): starts each new build in a virtual machine before it's published |
| `build_files/evenkeel_os_health.py`, `greenboot/evenkeel-os-health`, `greenboot/40-evenkeel-os-still-works.sh`, `greenboot/93-evenkeel-os-health-record.sh`, `greenboot/evenkeel-os-health-record.service` | The trial check: after each good start (4 minutes in) a list of what works is saved to `/var/lib/evenkeel-os/health-record.json`; while a new version is on trial, after a login, anything on that list that's broken now fails the start (it waits 2 minutes for slow devices first). Hardware counts only if it's still there (unplugged, switched off in the BIOS or by a privacy switch doesn't count); only USB devices in fixed ports are listed; things switched off by their owner aren't asked for; a start that only changed boot options checks programs only; a mistake in the check itself never fails a start. What broke goes to `/var/lib/evenkeel-os/health-lost`, and to `rolled-back-why` with the next rollback's note. `sudo /usr/libexec/evenkeel-os-health compare --no-wait` runs the comparison by hand |
| `build_files/check-health.py` | Build check: the trial check against a made-up computer, with each of 58 changes counted as broken, or not, as it should be, and the driver each rollback test copy blocks |
| `build_files/firewall/evenkeel-home.xml`, `evenkeel-work.xml`, `evenkeel-public.xml` | The three firewall zones for Network safety: Home, Work and Public place |
| `build_files/evenkeel_os_network.py` | Each network's place, shared by System Tools, the question and the installer |
| `build_files/evenkeel-os-network-ask`, `evenkeel-os-network-ask.desktop` | The once-per-network question, started at login |
| `build_files/check-network.py` | Build check: the default zone is Public place, Public lets nothing in, Home and Work keep 1025-65535 and have no SSH, open Wi-Fi can't be made Home, and the question is asked only for joined password Wi-Fi networks with no place |
| `build_files/evenkeel_os_sharing.py` | Shared folders: the shared folders list, which folders may be shared, and the Samba settings written for them |
| `build_files/samba/smb.conf` | EvenKeelOS's Samba settings: no guest access, no printers, no NetBIOS, Mac-friendly settings, the computer's own name for Macs and Linux. It includes the list System Tools writes |
| `build_files/samba/wsdd-evenkeel-os.conf` | Holds wsdd to Home networks and restarts it with Samba |
| `build_files/samba/50-evenkeel-os-sharing` | NetworkManager hook: checks again whenever a network comes or goes |
| `build_files/firewall/evenkeel-sharing.xml` | Firewall service: port 445 (wsdd's ports are already open on Home), added to Home only while sharing is on |
| `build_files/check-sharing.py` | Build check for Shared folders: no guest access, nothing shared until picked, and only your own, non-hidden folders can be shared |
| `build_files/evenkeel_os_bootopts.py`, `evenkeel-os-boot-options` | Boot options: the common fixes, the risky and refused settings, reading what the next start uses, and the root helper that changes them with `rpm-ostree kargs` (its own polkit action, the password every time) |
| `build_files/check-boot-options.py` | Build check for Boot options: rpm-ostree can make the changes, every common fix is allowed without a warning, risky settings are warned about however they're written, and settings the system sets itself, settings that run a program while starting, and text that isn't a setting are refused |
| `build_files/evenkeel-os-update`, `evenkeel-os-update-helper` | **System Update**, and its Python helper for progress text and what's new |
| `build_files/evenkeel-os-packages`, `evenkeel_os_packages/`, `evenkeel-os-box-run`, `evenkeel-os-hwrules` | **Install Package File**, **Remove Apps**, **Repair App Boxes**, **Start Apps at Login**, and their helpers |
| `build_files/evenkeel-os-tools`, `-admin`, `-safe`, `evenkeel_os_panel.py`, `check-panel.py` | **System Tools**: the window, every job, its two root helpers, and the build check that every tool has a row |
| `build_files/evenkeel_os_dialogs.py`, `evenkeel-os-dialog`, `check-dialogs.py` | A tool's questions, lists, password box and progress inside the System Tools window: the window's side, the program tools started from it use in place of zenity (same options and answers), and the build check that no tool runs zenity itself and that the answers match |
| `build_files/evenkeel-os-updates-pause-check`, `50-evenkeel-os-pause.conf` | Skips automatic updates during the pause after an undo |
| `build_files/greenboot/`, `evenkeel-os-rolled-back.desktop` | Automatic rollback: greenboot's start-up checks (login screen, networking, a working desktop after a login), the retry counter (2 bad starts) started as soon as an update is installed, a one-time repair of boot menus where greenboot's file ran into the next one (it and the retry-counter step unlock `/boot` only in their own private mount namespace, so an update writing to `/boot` isn't affected), the rollback tests (each breaks one real thing, only with its kernel argument; `check-rollback-tests.py` checks each listed test reaches its piece), the note and update pause after a rollback, and the settings repair (`build_files/greenboot/evenkeel-os-settings` saves, checks and repairs and does the test's delete step; `build_files/greenboot/evenkeel-os-settings-test` is the test, with its own polkit action in the System Tools policy and the admin password every time; the greenboot steps `05-evenkeel-os-settings.sh` (start-up check), `50-evenkeel-os-settings-repair.sh` (after a failed start) and `95-evenkeel-os-settings-save.sh` (after a good start, last); `build_files/check-settings-repair.py` runs the check and repair on a made-up `/etc`, including systemd's generic copies; `build_files/50-evenkeel-os-firstboot.conf` makes the first-start setup ask no questions, so a start without `machine-id` isn't held up before the checks) |
| `build_files/evenkeel-os-certs`, `evenkeel-os-certs.service`, `evenkeel-os-certs.timer`, `evenkeel-os-cert-remove`, `evenkeel-os-ca-trust.service`, `check-certs.py` | Certificate alerts: the check (as the person logged in, 3 minutes after the session starts and once a day; a per-user timer switched on for every account from `/usr/lib/systemd/user`), and the build check with made-up certificates (it prints this image's own expired or expiring certificates as warnings). `build_files/evenkeel-os-cert-remove` is the removal helper for an added certificate (`/usr/libexec/evenkeel-os-cert-remove`, its own polkit action; only for a plain file in the anchors folder, never a link, and it refuses a file with more than one certificate; `evenkeel-os-cert-remove FILE FINGERPRINT`; `check-root-helpers.py` tests its refusals in the real anchors folder (a file with two certificates, a different certificate, a link, a pipe) and that System Tools and the helper take the same file names), and `build_files/evenkeel-os-ca-trust.service` rebuilds the trusted list at every start (`update-ca-trust extract`) |
| `build_files/evenkeel-os-codecs`, `-setup`, `-admin`, `-lib.sh`, `rpmfusion-*.repo` | **Install Media Codecs** and its helpers |
| `build_files/*.policy`, `*.rules` | polkit actions and the narrow no-password rules, all for the person at the computer only. `40-evenkeel-os-uupd.rules` narrows uupd's own rule, which let any account start, stop or restart updates, to starting and stopping them from the computer |
| `build_files/*.gschema.override`, `*.dconf`, `gnome-mimeapps.list`, `xdg-terminals.list`, `60-evenkeel-os-mic.conf` | Desktop defaults |
| `build_files/evenkeel-os-layout` | Switches a user between the current and the Windows-style layout |
| `build_files/evenkeel-os-accent-icons`, `evenkeel-os-accent-icons.desktop`, `check-accent-icons.sh` | Folder icons in the accent color: the colored sets are built from Fedora's Adwaita at a pinned [Adwaita Colors](https://github.com/dpejoh/Adwaita-colors) commit; the helper switches sets when the accent color changes and leaves any other icon theme alone |
| `build_files/rebrand.sh`, `initramfs.sh`, `evenkeel-os-boot-label` | EvenKeelOS name and logo, and the boot menu rename |
| `build_files/branding/` | Logos, the user picture, and the wallpapers (`wallpapers/`, a day and a night picture each, listed for Settings in `evenkeel-os.xml`) |
| `build_files/evenkeel-os-shell-theme.sh` | Adds one rule to GNOME Shell's own style file at build time so the lock screen's password box uses the accent color; fails the build if GNOME renames that part |
| `build_files/evenkeel-os-no-bootc.tuned.conf` | Keeps tuned from running bootc, and waiting on updates, at every power-mode switch |
| `build_files/check-*.py` | Build tests: packages are read correctly, printer drivers are recognized in any folder (`check-printer-drivers.py`), power modes skip bootc, docs keep up, and (`check-root-helpers.py`) every root helper refuses hostile input, bad device rules are refused and no-password rules stay at the computer. The build workflow also runs shellcheck and bandit on the root helpers |
| `build_files/locked-versions.txt`, `check-locked-versions.py`, `update-locked-versions.sh`, `.github/workflows/check-versions.yml` | The exact versions of the outside packages and the ISO build tool, the build check that they match, and the daily check for newer ones (see [Locked versions](#locked-versions)) |
| `iso/` | The live USB and its installer. `iso/build-local-iso.sh` builds a test ISO locally; `iso/verify-image.sh` checks the built images |
| `system_files/` | Files copied into the image |
| `cosign.pub` | Public key for verifying the image |

**The build fails, and nothing is published,** if:

- Fedora's logos or release packages remain, or the boot image can't unlock a
  disk;
- GNOME Software is still there, Bazaar is missing, System Tools is missing from
  Utilities, another EvenKeelOS tool still has its own icon, the System Tools
  window is missing a tool, an icon or a command, or text files wouldn't open in
  Text Editor;
- a default service is off, or RPM Fusion's codecs wouldn't install;
- Logo Menu, ArcMenu or Dash to Panel is missing or doesn't support the image's
  GNOME, or the Windows-style layout's defaults or switch don't work;
- a power mode would still run bootc on every switch;
- an outside package is not at its locked version or is not on the list (see
  [Locked versions](#locked-versions));
- Install Package File misreads four real Fedora packages;
- a tool would open its windows outside System Tools, or answer differently there;
- Network safety isn't set up right (a new network isn't a Public place, or Home and Work let in SSH).
- Shared folders isn't set up right (guest access is on, Samba or wsdd starts on its own, the firewall service is wrong,
  a hidden folder or another user's folder is accepted, or the shares written don't match the list), or Samba,
  smbpasswd, testparm, setsebool, avahi-daemon or wsdd is missing.
- Boot options isn't set up right (rpm-ostree can't make the changes, a common fix is refused or warned about, a
  risky setting isn't warned about, or a setting the system sets itself, one that runs a program while starting, or
  text that isn't a setting, is accepted).

A separate docs check fails when the README's contents table or a link is out of
date.

A failed signing step leaves an unsigned image that a signed rebase rejects.

### Boot test

Before anything is published, the build starts the new image in a virtual machine on the same free GitHub machine
(`boot_test/run-boot-test.sh`) and checks, one line each (`boot_test/boot-check`):

- the computer finishes starting and the login screen runs;
- a test user logs in by itself and reaches the desktop;
- Logo Menu runs with the standard layout, then ArcMenu and Dash to Panel run after switching to Windows-style;
- System Tools opens;
- greenboot started saving the list of what works, a list saved then passes the trial check, a doctored list fails
  it, and three real breaks are caught (checked in a private mount space, as greenboot runs it) and then put back:
  the update program swapped for one that fails (the same bind mount the rollback test uses), the firewall stopped,
  and printing stopped (`boot_test/boot-check-root`, which the test user may run with `sudo` in the test copy only).

The virtual machine runs a test-only copy (`boot_test/Containerfile`): the new image plus the automatic test login,
SSH for the checks, the check scripts and `sudo` for the one root check script,
without the Flathub app downloads of a first start (so a slow Flathub can't
fail the test). That copy is never published. Its disk is made with bootc-image-builder,
locked to one version in `run-boot-test.sh`. The test user's key and password are made for each run and thrown away.

If the start or a check fails, it tries once more from a clean start. If that fails too, the build stops: nothing is
published, everyone keeps the last good version, and "The image build failed" issue opens. Pull request builds run
the same test, so a change that breaks starting shows up before it's merged.

Each run's results are under **Artifacts** at the bottom of the run's page, as **boot-test**: `report.txt` (each
check, PASS or FAIL), `desktop-1.png` (a screenshot of the desktop at the end of the checks; `desktop-2.png` after a
second try), the start messages (`serial-1.log`), the warnings of that start (`warnings-1.txt`) and the build
machine's free disk space (`disk-space.txt`). If the test stops before the checks, the report says where, and the
build log has the details.

The disk is made with the old `quay.io/centos-bootc/bootc-image-builder` container, which its makers keep as a
stand-in for their newer `image-builder`. When they retire it, the boot test moves to `image-builder`.

When a build of `main` fails (a merge, the daily build or a run by hand), the build workflow opens an issue named
"The image build failed", assigned to `ctsdownloads`, with a link to the failed run. Another failure adds a comment
to that issue instead of a new one, and the next good build closes it. Pull request builds and cancelled builds don't
open an issue.

Fedora's service presets are kept through the rebrand. Universal Blue's package
repository is used only during the build.

## Locked versions

These are locked to exact versions in
[`build_files/locked-versions.txt`](../build_files/locked-versions.txt):

- the Universal Blue packages (uupd, Bazaar, Homebrew setup, ujust and its
  disk-encryption helper) and Ghostty, from Copr;
- Titanoboa, the ISO build tool, at one exact commit.

`build_files/build.sh` installs the Copr packages at exactly those versions. At
the end of the build, `build_files/check-locked-versions.py` fails the build if a
package not signed by Fedora's key is missing from the list or is at a different
version, or if a listed package isn't installed. The ISO build
(`.github/workflows/build-iso.yml` and `iso/build-local-iso.sh`) uses Titanoboa at
the locked commit, and its upload step is pinned to a commit like the other
GitHub actions.

### The daily check

[`check-versions.yml`](../.github/workflows/check-versions.yml) runs every day at
9:35 UTC, before the 10:05 UTC image build. You can also run it by hand from the
Actions tab. It runs `build_files/update-locked-versions.sh`, which asks Copr for
the newest version of each locked package (with Fedora's own package tool, dnf5,
in a Fedora container) and asks GitHub for Titanoboa's newest `main` commit.

If anything is newer, it opens a pull request named "Update locked versions" on
the branch `update-locked-versions`. The pull request is assigned to
`ctsdownloads` and mentions him, and lists each change with a link (the Copr
package page, or the Titanoboa compare page). If that pull request is already
open, the check adds a new commit on top of its branch and a comment listing the
change, so anything you changed on that branch is kept. If the branch changes
while the check runs, it stops and tries again the next day.

Nothing changes in the image until that pull request is merged. Review it and
merge it. Pull requests opened by a workflow don't start the image build checks
(a GitHub rule). The build and its checks run after the merge, and a failed
build publishes nothing. To run every check before merging: Actions tab, **Build
container image**, **Run workflow**, pick the branch `update-locked-versions`,
**Run workflow**. A build from any branch but `main` publishes nothing.

### Things to know

- **Merge in time.** Copr keeps the newest build of a package and deletes older
  builds about 14 days after a newer one is out (from Copr's documentation, as
  quoted in [this bug report](https://bugzilla.redhat.com/show_bug.cgi?id=1630257)).
  If the pull request isn't merged in time, the locked version can disappear and
  the daily build stops (`build.sh` says the locked version did not install)
  until it is merged.
- **Closing without merging.** The pull request opens again the next day while a
  newer version is still out.
- **A new extra package.** If a newer version needs another Universal Blue
  package that isn't on the list, the build stops and names it. Add that package
  to the list by hand on the pull request's branch (the build run above shows
  it), or on `main` if it shows up after the merge.
- **One-time setting.** In the GitHub repository, go to Settings, Actions,
  General, Workflow permissions, tick **Allow GitHub Actions to create and
  approve pull requests**, and Save. Without it, the pull request step fails.

### Not locked

- The Fedora base image (`quay.io/fedora-ostree-desktops/silverblue:45`) and
  its packages, taken by the tag and rebuilt daily.
- Titanoboa itself builds inside Fedora's own `quay.io/fedora/fedora:latest`
  container.
- The Flathub apps installed at the first start with internet, and Flathub apps
  added later.
- Software added after install: the optional codecs from RPM Fusion and Cisco,
  and VPN apps from each company's own download source.

Locked elsewhere: the GNOME extensions Logo Menu and ArcMenu by sha256 checksum,
and the folder icons by an Adwaita Colors commit, both in `build_files/build.sh`.

## Media codecs

Some formats (H.264, H.265) are covered by patents in some countries, so Fedora
and this image leave them out. Adding them is your choice and your
responsibility.

The [setup checklist](install.md#first-login) offers **Web video only**,
**Everything** or **Not now**. **Media codecs** in System Tools, Apps opens the
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
boots Fedora's signed shim and grub, so it works with Secure Boot on (see
[From the live USB](install.md#from-the-live-usb)). Older installs keep their
old name ("Fedora", "Generic", "bluefin"), which lives in the firmware. To
rename it:

    sudo evenkeel-os-boot-label          # shows what would change
    sudo evenkeel-os-boot-label --apply  # makes the change

The disk gets one copy of Fedora's signed shim (`shimx64.efi`). Fedora also
ships it as `shim.efi`, and some PCs' firmware (Framework laptops, for one)
turns that copy into an extra "Fedora" boot entry, so the image leaves it out.
Installs from before this change keep it until they are installed fresh.
