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
   - After you join a password Wi-Fi on the Network step, the installer asks "Where is NETWORK-NAME?" with **Home**,
     **Work** or **Public place**. The answer is saved with that network and carried over to the installed system.
     **Next** waits for an answer; **Back** skips the question, and the installed system asks at the first login.
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

**System Update** in System Tools, Updates updates now, with no password for the person at
the computer (from anywhere else, it asks). It shows the download and install
steps, lists what's new, and warns first on a low battery.
If the automatic update is already running, it follows that one. From a
terminal: `sudo uupd`.

To go back to the previous version, use **Undo the last update** in
[System Tools](system-tools.md#system-tools), pick it in the boot menu, or run
`rpm-ostree rollback` and restart. Undo in System Tools also pauses automatic
updates for 3 days; `rpm-ostree rollback` and the boot menu don't.

**Automatic rollback.** If a new version fails 2 starts in a row, the computer
goes back to the previous version by itself, says so at the next login, and
pauses automatic updates for 3 days. A start counts as bad when the login
screen or networking fails or doesn't start within 3 minutes, when it freezes
or hangs before the checks finish (turning it off and on counts, from the first
start of a new version), or, for a new
version, when a login doesn't reach a working desktop (no desktop after a
minute, or two logins that end within a minute: a login loop). Being offline,
or nobody logging in, never counts as a failure. Not caught: a freeze long
after login, and problems in apps; use Undo for those. It works
on computers installed from a live USB made after it was added (November 2026):
the boot menu's counter is set up only at install. **Test automatic rollback**
in [System Tools](system-tools.md#system-tools) checks it.

**Settings repair.** After each good start, a copy of the system settings
folder `/etc` is saved in `/sysroot/evenkeel-os/settings`. `/sysroot` stays
read-only for everything else (the copy is written in a private mount
namespace), and only root can read the copy. At every start, a check fails the
start when an important setting is broken. The important settings are the
account files (`passwd`, `shadow`, `group`, `gshadow`, `subuid`, `subgid`),
`fstab` (the list of disks), `sudoers`, `nsswitch.conf`,
`selinux/config`, `greenboot.conf`, `locale.conf`, `vconsole.conf`,
`containers/policy.json`, and, in the `pam.d`, `authselect` and `security`
folders, only the files the system itself comes with. Files you add in those
folders are yours: removing them is fine and they're never put back. The `pki`,
`ostree` and `containers/registries.d` folders aren't checked: removing a
certificate authority, an update source or a registry setting is a deliberate
change and stays. `sudoers.d` is never put back, so a removed admin grant stays
removed. Wi-Fi networks and other settings outside this list are never put
back. The one exception is the SELinux policy folder `/etc/selinux/targeted`:
when it's missing, it's put back whole, because without it an enforcing start
would freeze.

Broken means missing, or replaced by systemd's generic copy. At every start,
before the check, systemd puts its own generic `pam.d`, `nsswitch.conf`,
`locale.conf` and `vconsole.conf` in place when they're missing. Its generic
`pam.d` lets programs without their own login rules use the normal password
check, where Fedora's denies them.

`machine-id` isn't checked or put back: systemd makes a new one when it's
missing. A start without `/etc/machine-id` counts as a first start for systemd,
and Fedora's first-start setup would stop at a text question on the screen and
wait. EvenKeelOS stops it from asking questions (the installer already set
language, keyboard, time zone and accounts), so startup isn't held up before
the checks.

Not checked yet, only on real hardware: whether a start without
`/etc/machine-id` also switches services back on from their default settings
(for example automatic updates turned off in System Tools), as a first start
can.

After a failed start, the repair puts back only the broken important settings
from the copy, replacing systemd's generic copies. It changes nothing else. The
account files are put back only when they're missing. Removing accounts on
purpose (even all of them) stays: old accounts and passwords don't come back.
Then greenboot restarts the computer, and the next login shows a message
listing what was put back (a folder counts as one). The message shows only once
that start passed its start-up checks, and only within 3 days.

If `/etc/fstab` was missing, `/boot` isn't mounted and greenboot can't count
bad starts or restart. The repair then mounts `/boot` read-only (from the saved
`fstab`'s `/boot` line, only inside greenboot's own mount namespace) so
greenboot can. If it still can't, the repair restarts the computer itself after
putting things back. After a repair that put something back, it sets the retry
counter to 1 when it isn't set or has reached 0, so greenboot restarts into the
repaired version instead of stopping (greenboot's own default is 3, which
matters if `greenboot.conf` was deleted). This extra try happens only once per
saved copy. To write the counter, the repair
unlocks `/boot` only in its own private mount namespace and locks it again only
there, as greenboot does, so an update writing to `/boot` at the same time isn't
affected. The boot menu repair and the retry-counter step after an update work
the same way.

The repair doesn't run on a rollback test copy or on a new version on trial:
going back to the earlier version is the fix there. If the repair doesn't fix
the start, then after the second bad start (not after an update) greenboot
doesn't restart by itself. Turn the computer off and on, and that start is the
earlier version, which has its own settings. When the repair put things back
but the start still fails and the computer goes back to the earlier version (no
update involved, and no good start since the repair), the next login says the
settings couldn't be put back and the computer went back. Automatic updates are
not paused. A rollback after an update is still reported as an update rollback,
with the 3-day pause, even if a repair worked earlier. greenboot is switched on
from `/usr/lib/systemd/system` as well as `/etc`, so deleting `/etc` can't
switch it off. greenboot stops before any check when `/etc/motd.d` is missing, so that
folder is made before it starts.

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
3. **How to get apps:** opens Bazaar and Install a package file to show them.

The computer also asks once about each password Wi-Fi network: Home, Work or Public place (see
[Network safety](system-tools.md#network-safety)).

One restart at the end, if needed. **Later** shows it at the next login;
**Don't show again** stops it. It's in [System Tools](system-tools.md#system-tools)
any time.

**New to Linux?** opens in System Tools after the setup checklist closes: where things are, coming from Windows, and
what's different ([the guide](new-to-linux.md)). It opens at every login until **Don't show this again at login** at
its end is ticked. It's in System Tools, Get help, any time.
