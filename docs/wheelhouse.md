# Wheelhouse

[Back to the EvenKeelOS README](../README.md)

## Wheelhouse

**EvenKeelOS Wheelhouse** (just **Wheelhouse** under its icon) is one window with a sidebar. A ship is
steered from its wheelhouse; this is where you steer your computer.
A search box at the top of the sidebar finds any tool by its name, what it does, or its command. Show Apps has only Wheelhouse for these tools: Install Package File, Remove Apps,
Start Apps at Login, Repair App Boxes, Install Media Codecs and System Update no longer have their own icons, because
they are inside it. Double-clicking an .rpm, .deb, .exe or .msi file still opens the right tool. The Windows-style
start menu's System Update entry opens Wheelhouse on its Updates page. With the standard layout, the logo menu at
the top left has a Wheelhouse entry, under Extensions.

A tool's questions, lists, password box and progress show inside the Wheelhouse window, under the tool's name,
with a Back arrow at the top left. Back leaves the tool open: a bar at the top of every page says it is waiting for
an answer or still working, and its **Show** button goes back to it. One tool runs at a time: picking another while
one is open says to finish it first, and Wheelhouse stays open until the open tool is done. The admin password box is GNOME's own, and picking a file opens GNOME's file window. Run from a
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
- **Work** (`evenkeel-work`): like a Public place, nothing gets in and your folders are never shared. You can
  still open the office's own shared drives (samba-client), find printers and get an address.
- **Home** (`evenkeel-home`): like Fedora Workstation's own setting, apps you run can be reached on ports 1025 to
  65535 (for example phones, file sharing, web development test servers). System services below 1025 stay closed.
  Unlike Fedora, SSH is off. Turning on [Shared folders](#shared-folders) also lets file sharing in on Home.

Fedora's own FedoraWorkstation zone leaves ports 1025 to 65535 open on every network, including public Wi-Fi; here
that is only on Home. A computer whose Work zone still lets them in is changed once, at its next start
(`evenkeel-os-work-update.service`).

**Let in, by app or port.** Each place can let in more than its own settings, one app or port at a time:

- **Let an app in** opens a list to search by name or port number. It starts with apps checked by hand against
  their own documentation (Jellyfin, LocalSend, Sunshine, Home Assistant, Foundry Virtual Tabletop, Barotrauma, each
  with the link that states its ports, in `build_files/let-in-checked.txt`) and Fedora's own firewall list (264 apps
  and games, such as Minecraft, Plex, Syncthing, Steam In-Home Streaming and KDE Connect). Typing also searches IANA's
  official list of ports (`/etc/services`). Each entry shows its ports and where they come from.
- **Open a port** lets in one port or a range (like 8080 or 2456-2458) for TCP, UDP or both, with a name you give it.
- On a **Public place**, both ask first: strangers on the same network could reach it too.
- File sharing (Samba, and the ports Windows uses to find a computer) can't be let in on Work or a Public place:
  folders are shared only on Home, in [Shared folders](#shared-folders).

What's let in is listed under the place, with a button to close it again. Closing never closes a port another entry
or the place itself still uses. On Home, SSH and printers have their own switches instead.

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
| Banner | Says which network you're on and what it lets in. Its color follows the place: teal for Home, navy for Work, dark amber for a Public place. If the firewall isn't running, or new networks aren't a Public place, it turns amber and says so |
| Your networks | Lists every saved Wi-Fi and wired network with a **Home** / **Work** / **Public place** picker for each (open Wi-Fi just shows Public place). A change takes effect at once for a connected network, or the next time it connects if that can't be done at once |
| Log in from another computer (SSH) | Under **Also let in, on Home**. Off to start. On starts the SSH server and lets it in on Home, never on Work or a Public place. Shows on only when both are true. Asks for the administrator password |
| Share my printer | Under **Also let in, on Home**. Off to start. On shares printers plugged into this computer and lets them be reached on Home, never on Work or a Public place. Shows on only when both are true. Asks for the administrator password |
| Apps and ports let in | Pick a place (it starts on the place of the network you're on) to see what it lets in beyond its own settings. **Let an app in** and **Open a port** add to it, and each entry's bin closes it again. Each change asks for the administrator password |

Changing a network's place doesn't ask for a password for an administrator user (Fedora's NetworkManager rule for
the wheel group). Other users are asked by NetworkManager.

If a computer updated from an older EvenKeelOS still has another default zone (for example Fedora's
FedoraWorkstation), the banner turns amber and says new networks aren't a Public place yet. Its **Fix** button
(asks for the password) makes Public place the default.

GNOME's own Public folder sharing (Settings, Sharing, File Sharing) uses a random port, so it only works on a Home
network.

In a terminal:

    nmcli connection modify NETWORK connection.zone evenkeel-home    # or evenkeel-work, evenkeel-public
    pkexec /usr/libexec/evenkeel-os-tools-admin firewall ssh on      # or off; same for ipp
    pkexec /usr/libexec/evenkeel-os-tools-admin firewall default
    pkexec /usr/libexec/evenkeel-os-tools-admin let-in work app minecraft          # home, work or public
    pkexec /usr/libexec/evenkeel-os-tools-admin let-in home ports "My game" 2456-2458/udp
    pkexec /usr/libexec/evenkeel-os-tools-admin let-in home remove "ports:2456-2458/udp"

All but the first ask for the administrator password. What's let in is listed in `/etc/evenkeel-os/let-in.json`.

### Shared folders

Lets other computers on a Home network open folders you pick, like Windows file sharing (it uses Samba). Nobody types
an address. A Mac finds this computer in Finder under Network, a Linux computer in Files under Network, and a
Windows PC under Network in File Explorer. Macs and Linux find it through Avahi (the computer announces itself).
Windows finds it through wsdd. A Windows PC lists other computers only when its own network is set to Private (in
Settings, Network and internet); on a Public network Windows turns network discovery off.

Sharing works only on networks set to **Home** in [Network safety](#network-safety). Never on Work or a Public place.
Samba and wsdd run only while a Home network is connected and at least one folder is shared by someone with a sharing
password, and stop by themselves when you leave it. Windows finds the computer only on the Home network. Macs and
Linux computers on another network connected at the same time may still see its name, but can't open it: turning
sharing on lets file sharing (port 445) into the Home firewall zone only, and turning it off takes it back out. The ports Windows
uses to find the computer are already open on Home. The switch is for everyone on this computer.

A wired network set to Home counts as Home on any cable you plug in, so the banner turns amber as a reminder when
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
| Banner | Says whether sharing is off, on (**Sharing on NETWORK**, and the name other computers see), waiting (**Sharing waits for a Home network**, on a Work network, a Public place or not connected), or **Nothing is shared yet** (no folder, or no sharing password). It turns amber for **Sharing didn't start**, for sharing over a wired Home network, and for **Shared folders can't start**, when `/etc/samba/smb.conf` was changed on the computer so it no longer includes the shared folders list (the switch can still turn sharing off) |
| Share folders on Home networks | A switch in the **Sharing** group. Turns sharing on or off. On a Work network or a Public place it shows off and greyed out, with **Off here:** and the network's name: sharing never runs there. If you turned it on, it comes back on by itself on a Home network; change it from a Home network |
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

Below that are three more groups: **Boot options**, **Common fixes** and **Your own settings**. See [Boot options](#boot-options).

### Boot options

Boot options are settings the computer starts with (kernel settings). Some fix screen flicker or a drive that freezes.
You can turn on a common fix, or type your own setting.

Each change asks for the administrator password, every time, and makes a new system version. The old version stays
as the fallback, and **Undo the last update** or automatic rollback can go back to it. A change starts at the next
restart. If an update is already waiting, it keeps the change, and updates after it carry the settings forward.

If the computer doesn't start properly with a new setting, automatic rollback goes back to the version before. The
note at the next login says the boot options caused it, and automatic updates aren't paused. **Undo the last update**
also knows a boot options change isn't an update: it offers to drop a waiting change, or to go back to the boot
options from before, and automatic updates aren't paused. When an update is waiting too, the change is part of the
waiting version, so dropping the update drops the change with it.

A setting the computer already had (like `quiet`) isn't counted as added, so taking out your settings never takes out
the system's own.

**The page.** **Disk and startup**, after **Starting the computer**, shows three groups:

| Item | What it does |
|------|--------------|
| Boot options | A status row. It says **In use**, **No boot options added**, or **Restart to use the changes** with a **Restart now** button. It shows what the next start really uses, so after a rollback a setting that caused it isn't shown |
| Common fixes | One switch for each fix in the list below. A switch is on when the next start uses that fix |
| Your own settings | An entry, **Add a setting, like amdgpu.abmlevel=0**, and a row with a trash button for each setting you added. Risky ones say why under their name |

While a change is being made, the section waits until it's done.

**Common fixes.** These are fixes people commonly report. Each one can cost a little battery, so turn one on only for a
problem you have.

| Fix | Setting | For |
|-----|---------|-----|
| AMD: white flickering | `amdgpu.sg_display=0` | The screen flashes white, often with an outside display |
| AMD: flicker, turn off Panel Self Refresh | `amdgpu.dcdebugmask=0x10` | Flicker or glitches when the picture is still |
| AMD: flicker, turn off Panel Replay | `amdgpu.dcdebugmask=0x400` | Glitches on newer AMD chips |
| AMD: flicker, turn off both | `amdgpu.dcdebugmask=0x410` | When neither of the two above is enough |
| AMD: screen dims or shifts colors on its own | `amdgpu.abmlevel=0` | Turns off adaptive backlight |
| Intel (older chips): flicker or freezes | `i915.enable_psr=0` | Turns off Panel Self Refresh |
| Intel (newest chips): flicker or black flashes | `xe.enable_psr=0` and `xe.enable_panel_replay=0` | Turns off Panel Self Refresh and Panel Replay |
| Drive freezes or disappears | `nvme_core.default_ps_max_latency_us=0` | Keeps the drive out of its deepest power saving |

The three `amdgpu.dcdebugmask` choices replace each other: turning one on replaces the one that was on.

**Typing your own.** Type one or more settings and press the apply button. Names are read the way the kernel reads
them: `-` and `_` are the same, and `0x0` or `00` is the same as `0`.

- Risky settings show **This setting is risky**, with the reason, and **Cancel** or **Add anyway**:
  - security turned off or weakened: `selinux=0`, `enforcing=0`, `security=`, `lsm=`, `lockdown=`,
    `module.sig_enforce=0`, `mitigations=off`, `nopti`, `pti=off`, `spectre_v2=off`, `nospectre_v1`, `nospectre_v2`,
    `nokaslr`, `iommu=off`, `intel_iommu=off`, `amd_iommu=off`, `audit=0`, `sysrq_always_enabled`,
    `spectre_v2_user=off`, `spec_store_bypass_disable=off`, `nospec_store_bypass_disable`, `l1tf=off`, `mds=off`,
    `retbleed=off`, `tsx=on`, `nosmap`, `nosmep`, `kvm.nx_huge_pages=off`;
  - starting without the desktop or into a shell: `rd.break`, `rd.shell`, `single`, `emergency`, `rescue`,
    `rd.rescue`, `rd.emergency`, `1` to `4`, `s`, `systemd.unit=` (anything but `graphical.target`),
    `rd.systemd.unit=`, `systemd.mask=`, and `rd.shell`, `systemd.debug_shell` or `rd.systemd.debug_shell` with any
    value but off (like `0` or `no`);
  - no picture: `nomodeset`, `amdgpu.dc=0`, and any `.modeset=0`;
  - may not start, or loses hardware: `acpi=off`, `acpi=noirq`, `noapic`, `nolapic`, `nosmp`, `noefi`, `mem=`,
    `memmap=`, `maxcpus=`, `nr_cpus=`, `efi=noruntime`, and anything with `blacklist` in its name.

  Settings that only make the computer stricter aren't warned about, like `selinux=1`, `enforcing=1`,
  `module.sig_enforce=1`, `rd.shell=0` or `mitigations=auto,nosmt`.
- Refused, because the system sets them itself and changing them stops it starting: `root`, `rootflags`,
  `rootfstype`, `ostree`, `rw`, `ro`, `BOOT_IMAGE`, `initrd`, `fstab`, `rd.fstab`, `rd.auto`, `systemd.volatile`,
  `luks`, and anything starting with `rd.luks`, `luks.`, `rd.lvm`, `rd.md`, `rd.dm`, `ostree.`, `composefs` or
  `mount.usr`.
- Refused, because they run a program with full control while the computer starts: `init=`, `rdinit=` and anything
  starting with `systemd.run`.
- Anything starting with `evenkeel_os.` is for **Test automatic rollback** and is refused. Changes are refused while a
  rollback test copy is running.
- Text that isn't a setting is refused, and so are values with quotes or spaces. Letters, numbers and `. _ - , : / +
  = @ !` work, like `video=eDP-1:1920x1080@60` or `acpi_osi=!`.
- You can add up to 20 settings, and each name only once.

In a terminal:

    pkexec /usr/libexec/evenkeel-os-boot-options set SETTING...

Give it the full list of settings you want added. With no settings, it takes them all out, and common fixes left out
are taken out too. It asks for the administrator password every time. It refuses what Wheelhouse refuses, but
doesn't warn about risky settings. Only Wheelhouse does.

### Make it yours

| Item | What it does |
|------|--------------|
| Desktop layout | Pick Standard (the top bar) or Windows-style (the bottom bar and start menu, which opens on the desktop at login). It takes effect after you log out and back in |
| Accent color and wallpaper | Opens Settings, Appearance. Folder icons follow the accent color |
| Light and dark | **Dark style**: Off, Sunset to sunrise, or Custom times (Dark from, Light from). Sunset and sunrise are worked out each day for your time zone's city, with no location service. It switches only at the change, so if you switch it yourself it stays that way until the next change. Night Light in Settings only warms the colors; this switches the whole style |
| Wallpaper slideshow | Pick a folder of your pictures (JPEG, PNG or WebP). The wallpaper changes to the next one, in name order, every hour, every day or at each login. Turn **Slideshow** off to keep the picture you have |
| Fonts and text | The fonts for menus and windows, documents, and code and the terminal, and **Text size** (1.00 is normal; Large text in Settings, Accessibility is 1.25). **Back to the original** puts all four back. GNOME's own Settings has none of these |

### Get help

| Item | What it does |
|------|--------------|
| EvenKeelOS guide | How to do things, step by step. It opens on a list of topics: **New to EvenKeelOS?**, **The desktop**, **Files**, **Apps**, **Internet and networks**, **Printing**, **Updates and safety**, **Making it yours**, **Disk and startup** and **Getting help**, each also listed on Get help. A topic is a page of numbered steps. **Show me** next to a step opens the Wheelhouse page, Settings page or topic it names, and the back arrow at the top left goes back one page at a time, to the guide. The same text is in [EvenKeelOS guide](guide.md). At login, **New to EvenKeelOS?** opens after the setup checklist, until **Don't show this again at login** at its end is ticked, and never after **I already use Linux** in the installer |
| Undo the last update | Goes back to the version before the last update |
| Save problem details | Saves recent errors to one file to email your helper |
| Test automatic rollback | Checks that the computer goes back by itself when a new version doesn't start, and that important settings are put back when they're deleted. See below |
| Certificate alerts | Lists trusted certificates that expired, expire within 30 days, or were removed, with **Remove it** for an expired one you added. Also `evenkeel-os-tools certificates`. See below |
| Prefer the terminal? | Shows every tool's command, each with a copy button |

### Commands

`evenkeel-os-tools` opens the window. `evenkeel-os-tools --page=updates` (or `apps`, `disk`, `yours`, `help`, or
`guide` for the EvenKeelOS guide) opens it on that page. All the old commands still work, such as `evenkeel-os-tools firmware`,
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
  the disk password is asked again. Turn it back on in Wheelhouse.

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
you turn it off and on), or one that breaks something that worked: **Sound
driver blocked**, **Wi-Fi driver blocked**, **Bluetooth driver blocked**,
**Graphics driver blocked** (each blocks the driver this computer uses with
`module_blacklist=`), **Printing service off**, **Firewall off**, **Update
program broken** (a bind mount over `uupd` until the restart) or **A system
service fails** (ModemManager, or switcheroo-control). Those wait for a login;
about 3 minutes after it, a window asks before each restart: **Restart now**,
or **Not yet** to save your work first (nothing restarts until Restart now).
Graphics driver blocked restarts by itself after 2 minutes with no answer,
because the screen may stay black. With nobody logged in, each start waits 15
minutes, then restarts without asking. The note names what broke. A driver test keeps any driver blocks you set in
Boot options. They refuse, and say why, when this computer
doesn't have that thing or it wasn't working, when the driver is built into
the system, or when no list of what works has been saved yet (4 minutes after
a good start). It makes a test copy of the running version with that
problem (`rpm-ostree kargs --append=evenkeel_os.test_rollback=KIND`; nothing
breaks without that kernel argument). At the restart the test copy really
breaks: 2 bad starts in a row (each picked test says what you'll see), then the
computer goes back to the version it had, removes the test copy and says the
test worked at the next login (after every rollback, not just the first). The
other tests break the start before there's a desktop, so they restart without
asking, and can't be stopped once started; their start question says so. The
test copy takes the place of the earlier version kept for Undo, so Undo has
nothing to go back to until the next update. Needs the admin password, and a
computer installed from a newer live USB (see
[Automatic rollback](install.md#updating-and-rolling-back)). If the computer is
still running a test copy, the tool offers to remove its marker instead
(`rpm-ostree kargs --delete=evenkeel_os.test_rollback=KIND`, plus its driver block).

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
top of Wheelhouse, Overview, with a **Details** button) shows when a
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
whose names Wheelhouse can't handle show "tell your helper" instead of
**Remove it**. After removing, Wheelhouse checks that the certificate
is really no longer trusted and says so if it still is. For an expiring added one, it says to ask whoever gave it for a
new one. For built-in ones, it says Fedora's updates replace them, so keep
automatic updates on. A removed certificate is no longer trusted. The alert
goes away once read. A certificate removed in Wheelhouse raises no "removed"
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
updates, Flatpaks and boxes, and the logs of Install a package file and
Wheelhouse. Box apps' own logs stay out. Nothing is sent anywhere.
