# System Tools

[Back to the EvenKeelOS README](../README.md)

## System Tools

**System Tools** is one window with a sidebar. A search box at the top of the sidebar finds any tool by its name,
what it does, or its command. Show Apps has only System Tools for these tools: Install Package File, Remove Apps,
Start Apps at Login, Repair App Boxes, Install Media Codecs and System Update no longer have their own icons, because
they are inside it. Double-clicking an .rpm, .deb, .exe or .msi file still opens the right tool. The Windows-style
start menu's System Update entry opens System Tools on its Updates page.

For now, the tools still open their own small windows on top of System Tools while they work. Moving them inside the
window comes in a later update.

### Overview

| Item | What it does |
|------|--------------|
| Status banner | Says **Your computer is in good shape** with **Update now**, or that a new version is ready with **Restart now**, or that automatic updates are paused until a day with **Resume now**, or that automatic updates are off with **Turn on** |
| Undo the last update | Goes back to the version before the last update |
| Free up disk space | Removes unused app parts, old update files and container images. Your files aren't touched |
| Save problem details | Saves recent errors to one file to email your helper |
| Setup checklist | Codecs, disk unlock and apps. See [First login](install.md#first-login) |

### Updates

| Item | What it does |
|------|--------------|
| System Update | Updates now |
| Automatic updates | Turns daily updates on or off. On is recommended. Shows On, Paused or Off. After an undo it shows the pause, with **Resume now** |
| Update firmware | Installs BIOS and device firmware updates. Keep it plugged in |
| Undo the last update | Goes back to the version before the last update |

While automatic updates are on, VPNs, codecs and apps added to the system are checked every day too.

### Apps

| Item | What it does |
|------|--------------|
| Drop zone | Drop an .rpm or .deb to install it, or an .exe or .msi to get its Linux version |
| Get apps | Opens Bazaar |
| Install a package file | Installs an .rpm or .deb. See [Apps](apps.md) |
| Remove apps | Removes apps you added from package files |
| Start apps at login | Switches apps on or off at login |
| Repair app boxes | Rebuilds an app box that stopped working |
| Media codecs | Adds video and audio formats. See [Media codecs](building.md#media-codecs) |
| Remove media codecs | Takes them out again, after asking. Needs your password and a restart |
| Get a VPN | Mullvad, Proton, IVPN or NordVPN, kept up to date. See below |
| Windows programs | Pick an .exe or .msi to get its Linux version |
| Zoom meetings | If you chose your usual browser for Zoom, this lets you be asked about Chrome again. See [Zoom meetings](zoom.md) |

### Disk and startup

| Item | What it does |
|------|--------------|
| Disk space | Shows how much is free, with a bar, and updates after Free up disk space |
| Free up disk space | Removes unused app parts, old update files and container images. Your files aren't touched |
| Unlock disk automatically | Lets the security chip (TPM) unlock an encrypted disk at startup. Shows On or Off |
| Restart into BIOS settings | Restarts straight into the BIOS screen |

### Make it yours

| Item | What it does |
|------|--------------|
| Desktop layout | Pick Standard (the top bar) or Windows-style (the bottom bar and start menu, which opens on the desktop at login). It takes effect after you log out and back in |
| Accent color and wallpaper | Opens Settings, Appearance. Folder icons follow the accent color |

### Get help

| Item | What it does |
|------|--------------|
| Undo the last update | Goes back to the version before the last update |
| Save problem details | Saves recent errors to one file to email your helper |
| Test automatic rollback | Checks that the computer goes back by itself when a new version doesn't start. See below |
| Prefer the terminal? | Shows every tool's command |

### Commands

`evenkeel-os-tools` opens the window. `evenkeel-os-tools --page=updates` (or `apps`, `disk`, `yours`, `help`) opens it
on that page. All the old commands still work, such as `evenkeel-os-tools firmware`,
`evenkeel-os-packages install`, `evenkeel-os-update` and `evenkeel-os-codecs`.

### Details

**Passwords.** No password for an admin at the computer: automatic updates on,
the pause after an undo and resuming it, disk unlock (it asks the disk password
instead) and freeing space. These keep the admin password, because a bad
program could misuse them: automatic updates off, undo, firmware, the rollback
test, adding apps to the system, and getting a VPN.
Desktop layout changes only your own desktop, so it never asks.

**Unlock disk automatically.**

- Needs a disk encrypted at install and a TPM 2.0 chip. Secure Boot should be on.
- Asks for the disk password once, then a restart. Five wrong passwords lock it
  for an hour.
- If the disk moves or startup settings change (a BIOS update, Secure Boot off),
  the disk password is asked again. Turn it back on in System Tools.

**Undo the last update.** Sets the previous version to start next time (like
`rpm-ostree rollback`). Versions from the same day show the time too. A
downloaded update waiting for a restart can be dropped with **Don't use it**. After an undo, **Use the newer version** goes forward
again. An undo (or **Don't use it**) pauses automatic updates for 3 days, so the
bad update doesn't come straight back; they turn back on by themselves. System
Update still works by hand. If the problem returns after the pause, turn off
Automatic updates and tell your helper.

**Test automatic rollback.** Pick a real problem to test: **Quick test** (a
start-up check fails), **No login screen**, **No networking**, **Stuck while
starting**, **Login loop**, or **Freeze** (a kernel crash at the login screen;
you turn it off and on). It makes a test copy of the running version with that
problem (`rpm-ostree kargs --append=evenkeel_os.test_rollback=KIND`; nothing
breaks without that kernel argument). At the restart the test copy really
breaks: 2 bad starts in a row (each picked test says what you'll see), then the
computer goes back to the version it had, removes the test copy and says the
test worked at the next login (after every rollback, not just the first). The
test copy takes the place of the earlier version kept for Undo, so Undo has
nothing to go back to until the next update. Needs the admin password, and a
computer installed from a newer live USB (see
[Automatic rollback](install.md#updating-and-rolling-back)). If the computer is
still running a test copy, the tool offers to remove its marker instead
(`rpm-ostree kargs --delete=evenkeel_os.test_rollback=KIND`).

**Get a VPN.** Pick Mullvad, Proton, IVPN or NordVPN. It asks you to confirm, then the password. It adds that
company's own download source and the app to the system (not a box), then offers a restart. Nothing is installed until
you pick one. After the restart it asks **Turn it on** at login. Also `evenkeel-os-tools vpn` and
`evenkeel-os-packages vpn`. See [VPNs](vpn.md).

**Save problem details.** Saves `problem-details-<date>.txt` to Documents:
system version and hardware, recent warnings and errors, the last 3 days of
updates, Flatpaks and boxes, and the logs of Install a package file and System
Tools. Box apps' own logs stay out. Nothing is sent anywhere.
