# Install

[Back to the EvenKeelOS README](../README.md)

## Install

From the live USB on any computer, or by switching a Fedora Silverblue or
Bluefin computer.

### From the live USB

The live USB runs EvenKeelOS from the stick, so you can try it.
Nothing touches the disk until you install.

1. **Make the stick:** on GitHub, **Actions**, **Build live ISO (test)**, **Run
   workflow**. Download `evenkeel-os-live-iso` from the run, unzip it, and write
   the ISO with Fedora Media Writer or GNOME Disks (**Restore Disk Image**). Or
   build it locally: `iso/build-local-iso.sh` from a normal terminal (sudo, about
   70 GB free; the ISO lands in `~/Downloads/evenkeel-os-iso/`).
2. Start from the stick and pick **EvenKeelOS Live**. Secure Boot can stay on.
   The computer's boot list may name the stick "Fedora": its boot loader is
   Fedora's signed one.
3. **Welcome window:** **Install EvenKeelOS** or **Try it first**.
4. **The installer:** it asks for language, keyboards, network, time zone, date
   and time, disk, encryption, accounts, the computer's name and the desktop
   layout (Standard, or Windows-style with a bottom bar and start menu), then
   shows a **Review**. Click **Install**, then **Restart** when it's done.
   - If the install stops: **Save the log**, **Show a QR code**, or **Report on
     GitHub**. The log leaves out passwords and names.
5. Log in. The [setup checklist](#first-login) opens.

The installed system takes its updates from the signed image on GitHub.

### From Silverblue or Bluefin

Once per machine. The first rebase is unverified because it installs the
signing key; the second is verified.

```
rpm-ostree rebase ostree-unverified-registry:ghcr.io/ctsdownloads/evenkeel-os:latest
systemctl reboot
rpm-ostree rebase ostree-image-signed:docker://ghcr.io/ctsdownloads/evenkeel-os:latest
systemctl reboot
```

### Updating and rolling back

Updates are automatic: `uupd` runs daily at 4 am (or at the next start) for the
system, Flatpaks, app boxes and Homebrew. A new system is used from the next
restart.

**System Update** in Show Apps updates now, with no password. It shows the
download and install steps, lists what's new, and warns first on a low battery.
If the automatic update is already running, it follows that one. From a
terminal: `sudo uupd`.

To go back to the previous version, use **Undo the last update** in
[System Tools](system-tools.md#system-tools), pick it in the boot menu, or run
`rpm-ostree rollback` and restart. Undo in System Tools also pauses automatic
updates for 3 days; `rpm-ostree rollback` and the boot menu don't.

Next automatic update: `systemctl list-timers uupd.timer`.

### Checking that updates are real

Every update is signed. Your computer refuses any update without this project's
signature. To check yourself:

```
cosign verify --key cosign.pub ghcr.io/ctsdownloads/evenkeel-os:latest
```

### First login

**The setup checklist** opens at a new user's first login. Three steps, each
can be skipped:

1. **Media codecs:** see [Media codecs](building.md#media-codecs).
2. **Disk password at startup:** **Unlock disk automatically**, if the disk is
   encrypted and has a security chip.
3. **How to get apps:** opens Bazaar and Install Package File to show them.

One restart at the end, if needed. **Later** shows it at the next login;
**Don't show again** stops it. It's in [System Tools](system-tools.md#system-tools)
any time.
