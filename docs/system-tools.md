# System Tools

[Back to the EvenKeelOS README](../README.md)

## System Tools

**System Tools** is one window with a sidebar. A search box at the top of the sidebar finds any tool by its name,
what it does, or its command. Show Apps has only System Tools for these tools: Install Package File, Remove Apps,
Start Apps at Login, Repair App Boxes, Install Media Codecs and System Update no longer have their own icons, because
they are inside it. Double-clicking an .rpm, .deb, .exe or .msi file still opens the right tool. The Windows-style
start menu's System Update entry opens System Tools on its Updates page.

A tool's questions, lists, password box and progress show inside the System Tools window, under the tool's name,
with a Back arrow at the top left. Back leaves the tool open: a bar at the top of every page says it is waiting for
an answer or still working, and its **Show** button goes back to it. One tool runs at a time: picking another while
one is open says to finish it first, and System Tools stays open until the open tool is done. The admin password box is GNOME's own, and picking a file opens GNOME's file window. Run from a
terminal, or at login, the same tools still open their own small windows.

### Overview

| Item | What it does |
|------|--------------|
| Status banner | Says **Your computer is in good shape** with **Update now**, or that a new version is ready with **Restart now**, or that automatic updates are paused until a day with **Resume now**, or that automatic updates are off with **Turn on**. The paused and off warnings show before a certificate warning |
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

### Network safety

Every network is one of three places: **Home**, **Work** or **Public place**. The place is saved with that one
network (its firewall zone, `connection.zone`, in the network's own NetworkManager profile), so it follows that
network. A network with no place set is a Public place.

- **Public place** (`evenkeel-public`): nothing gets in. Only finding printers and devices (mdns) and getting an
  address (dhcpv6-client) work. SSH is off.
- **Home** (`evenkeel-home`) and **Work** (`evenkeel-work`): like Fedora Workstation's own setting, apps you run can
  be reached on ports 1025 to 65535 (for example phones, file sharing, web development test servers). System services
  below 1025 stay closed. Unlike Fedora, SSH is off. Turning on [Shared folders](#shared-folders) also lets file
  sharing in on Home.

Before this, every network used Fedora's FedoraWorkstation zone, which leaves ports 1025 to 65535 open on every
network, including public Wi-Fi. That is now only on Home and Work.

**The question.** Once per network, after you join a password-protected Wi-Fi that has no place yet, a small
window asks "Where is NETWORK-NAME?" with **Home**, **Work** and **Public place** (Public place picked). It shows at
login and when you join a new network. Closing the window without saving means it asks again at the next login. The
installer asks the same question after you join a password Wi-Fi (see [From the live USB](install.md#from-the-live-usb)).

Never asked:

- **Open Wi-Fi** (no password, including Enhanced Open): a Public place, since anyone can make a network with the
  same name. The page doesn't offer Home or Work for it; if one was set another way (in a terminal), the page says
  so and offers **Make it a Public place**.
- **Wired networks**: the computer keeps one wired setting for every cable you plug in, so a Home setting would also
  apply to a hotel's or an office's cable. They stay a Public place unless you change them on this page.
- **A hotspot this computer makes**: it keeps NetworkManager's own sharing setting, so devices on it still get an
  address. It isn't listed.

**The page.** **Network safety** (shield icon, after Apps) shows:

| Item | What it does |
|------|--------------|
| Banner | Says which network you're on and what it lets in. If the firewall isn't running, it turns amber and says so |
| Your networks | Lists every saved Wi-Fi and wired network with a **Home** / **Work** / **Public place** picker for each (open Wi-Fi just shows Public place). A change takes effect at once for a connected network, or the next time it connects if that can't be done at once |
| Log in from another computer (SSH) | Under **Also let in, on Home and Work**. Off to start. On starts the SSH server and lets it in on Home and Work, never on a Public place. Shows on only when both are true. Asks for the administrator password |
| Share my printer | Under **Also let in, on Home and Work**. Off to start. On shares printers plugged into this computer and lets them be reached on Home and Work, never on a Public place. Shows on only when both are true. Asks for the administrator password |

Changing a network's place doesn't ask for a password for an administrator user (Fedora's NetworkManager rule for
the wheel group). Other users are asked by NetworkManager.

If a computer updated from an older EvenKeelOS still has another default zone (for example Fedora's
FedoraWorkstation), the banner turns amber and says new networks aren't a Public place yet. Its **Fix** button
(asks for the password) makes Public place the default.

GNOME's own Public folder sharing (Settings, Sharing, File Sharing) uses a random port, so it only works on a Home
or Work network.

In a terminal:

    nmcli connection modify NETWORK connection.zone evenkeel-home    # or evenkeel-work, evenkeel-public
    pkexec /usr/libexec/evenkeel-os-tools-admin firewall ssh on      # or off; same for ipp
    pkexec /usr/libexec/evenkeel-os-tools-admin firewall default

The last two ask for the administrator password.

### Shared folders

Lets other computers on a Home network open folders you pick, like Windows file sharing (it uses Samba). Nobody types
an address. A Mac finds this computer in Finder under Network, a Linux computer in Files under Other Locations, and a
Windows PC under Network in File Explorer. Macs and Linux find it through Avahi (the computer announces itself).
Windows finds it through wsdd. A Windows PC lists other computers only when its own network is set to Private (in
Settings, Network and internet); on a Public network Windows turns network discovery off.

Sharing works only on networks set to **Home** in [Network safety](#network-safety). Never on Work or a Public place.
Samba and wsdd run only while a Home network is connected and at least one folder is shared by someone with a sharing
password, and stop by themselves when you leave it. Windows finds the computer only on the Home network. Macs and
Linux computers on another network connected at the same time may still see its name, but can't open it: turning
sharing on lets file sharing (port 445) into the Home firewall zone only, and turning it off takes it back out. The ports Windows
uses to find the computer are already open on Home. The switch is for everyone on this computer.

A wired network set to Home counts as Home on any cable you plug in, so the banner turns orange as a reminder when
sharing runs over a wired Home network.

**Passwords.** Other computers ask for your user name (your login name on this computer) and the sharing password.
The sharing password is separate from your login password, and has at least 8 characters. Each computer can remember
it. Nothing is ever shared as a guest (no password). Turning sharing on the first time asks you to set the sharing
password first. Changes ask for an administrator password (not again for a few minutes after).

**Folders.** Only folders inside your own home folder can be shared. Not the home folder itself, not hidden folders
(names starting with a dot, which hold settings and keys), and not folders that belong to someone else. A folder is
shared under its own name. A new folder starts as **Read only**. Change it in the list. Changing or removing a folder
drops only the connections open to that folder. A folder whose name isn't readable text (from an old zip file, say)
can't be shared: rename it first.

Everything another computer does in a shared folder is done as you. Files saved from other computers belong to you
(no permission errors), and other computers can't reach anything you couldn't. Shortcuts (symlinks) inside a shared
folder that point outside it don't open.

**The page.** **Shared folders** (folder icon, after Network safety) shows:

| Item | What it does |
|------|--------------|
| Banner | Says whether sharing is off, on (**Sharing on NETWORK**, and the name other computers see), waiting (**Sharing waits for a Home network**, on a Work network, a Public place or not connected), or **Nothing is shared yet** (no folder, or no sharing password). It turns orange for **Sharing didn't start**, for sharing over a wired Home network, and for **Shared folders can't start**, when `/etc/samba/smb.conf` was changed on the computer so it no longer includes the shared folders list (the switch can still turn sharing off) |
| Share folders on Home networks | A switch in the **Sharing** group. Turns sharing on or off |
| Sharing password | A row in the **Sharing** group with a **Set** or **Change** button |
| Add a folder | In the **Folders** group. Pick a folder in your home folder to share |
| Each shared folder | A row with its name, its place in the home folder, a **Read only** / **Read and write** choice, and a trash button to stop sharing it. A folder that was moved or deleted says **Folder not found** |

GNOME's own Settings, Sharing, File Sharing (the Public folder, WebDAV) is a separate thing and is left as it is.

In a terminal:

    pkexec /usr/libexec/evenkeel-os-tools-admin sharing on             # or off
    pkexec /usr/libexec/evenkeel-os-tools-admin sharing add FOLDER ro  # or rw
    pkexec /usr/libexec/evenkeel-os-tools-admin sharing mode FOLDER ro # or rw
    pkexec /usr/libexec/evenkeel-os-tools-admin sharing remove FOLDER
    pkexec /usr/libexec/evenkeel-os-tools-admin sharing password       # reads the password from standard input

These ask for the administrator password. Root and system accounts can't share folders.

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
| Test automatic rollback | Checks that the computer goes back by itself when a new version doesn't start, and that important settings are put back when they're deleted. See below |
| Certificate alerts | Lists trusted certificates that expired, expire within 30 days, or were removed, with **Remove it** for an expired one you added. Also `evenkeel-os-tools certificates`. See below |
| Prefer the terminal? | Shows every tool's command, each with a copy button |

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

The other test is **Important settings deleted**. It is not a test copy (no
kernel argument): it really deletes `/etc/passwd`, `/etc/shadow`, `/etc/group`,
`/etc/gshadow`, `/etc/fstab`, `/etc/pam.d` and `/etc/sudoers`, then restarts
right away, so save your work first. The command behind it is
`/usr/libexec/evenkeel-os-settings-test`. It has its own permission and asks
for the admin password every time (a password typed a few minutes before isn't
reused). Before deleting, it starts greenboot's retry counter. The next start
finds them broken, puts them back and restarts. A message at login says the
test worked and lists what was put back. If the repair doesn't work and the
computer goes back to the earlier version, the message says the test didn't
work (no pause of automatic updates). It refuses, and says why, when the
computer was installed before automatic rollback, an update is waiting for a
restart, a test copy is running, no copy of the settings has been saved since
this start (wait a few minutes), there's no earlier version to fall back to
(run it after the next update), the earlier version doesn't have the settings
repair yet (run it after the next update), or another version is set to start next (after
Undo the last update or picking a version in the boot menu; restart first). It
also refuses when greenboot was switched off with `systemctl mask`. If deleting
stops partway or the restart doesn't start, it says the settings are already
deleted and to restart now. The test's marker is cleared at any good start.

**Certificate alerts.** The certificates the computer trusts for secure
websites and connections are checked: Fedora's list and the certificate files
added to the computer (in `/etc/pki/ca-trust/source/anchors`). The check runs 3
minutes after the session starts and once a day, as the person logged in, with
no admin rights. It changes nothing in the system. The trusted list is rebuilt
at every start from Fedora's current list plus the added files (Fedora's own
`update-ca-trust extract`, run by `evenkeel-os-ca-trust.service`), so
certificates Fedora updates replace or drop are replaced or dropped here too,
even after a certificate was added. An alert (a desktop notification, and a warning at the
top of System Tools, Overview, with a **Details** button) shows when a
certificate has expired, expires within 30 days, or (one added to the computer)
was removed. **Certificate alerts** in Get help lists them (also
`evenkeel-os-tools certificates`). For an expired certificate that was added to
the computer, it offers **Remove it**; nothing is removed without you. It has
its own permission ("remove a trusted certificate") and asks for the admin
password every time. The helper is `/usr/libexec/evenkeel-os-cert-remove`. It
refuses a file that holds more than one certificate (it would remove the good
ones too: tell your helper), never follows a link, and accepts file names with
spaces or brackets. Before removing, it checks, as root, that the file still
holds exactly the one certificate you confirmed (by its fingerprint). If the
file changed, nothing is removed. It never opens a link, pipe or device. Files
whose names System Tools can't handle show "tell your helper" instead of
**Remove it**. After removing, System Tools checks that the certificate
is really no longer trusted and says so if it still is. For an expiring added one, it says to ask whoever gave it for a
new one. For built-in ones, it says Fedora's updates replace them, so keep
automatic updates on. A removed certificate is no longer trusted. The alert
goes away once read. A certificate removed in System Tools raises no "removed"
alert for any account on the computer (the removal is recorded in
`/var/lib/evenkeel-os/certs-removed`). An expired certificate is never put back
or extended.

Rebuilding the trusted list at every start also recreates the links in
`/etc/pki/tls/certs`, so a link someone added there by hand is gone after a
restart. Add certificates in `/etc/pki/ca-trust/source/anchors` instead.

**Get a VPN.** Pick Mullvad, Proton, IVPN or NordVPN. It asks you to confirm, then the password. It adds that
company's own download source and the app to the system (not a box), then offers a restart. Nothing is installed until
you pick one. After the restart it asks **Turn it on** at login. Also `evenkeel-os-tools vpn` and
`evenkeel-os-packages vpn`. See [VPNs](vpn.md).

**Save problem details.** Saves `problem-details-<date>.txt` to Documents:
system version and hardware, recent warnings and errors, the last 3 days of
updates, Flatpaks and boxes, and the logs of Install a package file and System
Tools. Box apps' own logs stay out. Nothing is sent anywhere.
