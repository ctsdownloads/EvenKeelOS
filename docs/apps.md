# Apps from .rpm and .deb files

[Back to the EvenKeelOS README](../README.md)

## Apps from .rpm and .deb files

The system is an image, so **Install Package File** puts apps from .rpm and .deb
files in a **box**: a small, separate Linux system just for those apps. That
keeps the system clean and apps easy to remove. Every window says which choice
is recommended and why.

.rpm files go in a Fedora box, .deb files in an Ubuntu 24.04 box (Distrobox
containers, kept apart from your own). System Update keeps the boxes current.

### Installing an app

1. Double-click the file, or open **Install Package File** and pick it.
2. It checks the file without installing anything. A file it can't use stops
   here (see [Files that cannot be installed](#files-that-cannot-be-installed)).
3. If the app is already there, it asks what to do (see
   [Already installed](#already-installed)).
4. If Bazaar (Flathub) has the same app, it recommends **Use Flathub**, which
   updates by itself. **Use the file** installs your download. Flathub matches
   are by app ID or name; loose name matches only for verified apps.
5. It says where the app goes:
   - Works in a box: **Set up and install** (or **Install**).
   - Parts of an .rpm need the system (a background service, say):
     **Add to the system** is recommended (password and restart). The box is
     still offered, without those parts.
   - A .deb can't go on the system, so it offers the box without those parts.
6. The last window says where to find it and how it updates (see
   [Updates](#updates)). Its icon shows in Show Apps and the dock.

### Apps that go on the system

**Add to the system** puts the app on top of the image, from the next restart.
Updates take a little longer after that. Remove Apps takes it off again.

| The package has | What happens |
|-----------------|--------------|
| An app, tools, a browser, most closed-source apps | Box |
| A device rule that only sets permissions | App in the box, rule on the system (password). A rule-only package offers **Add it** |
| A device rule that runs a program | Rule not added; the app still goes in the box |
| A device rule that could open disks or other system devices, every device at once, or every keyboard and mouse (one that doesn't name the device's maker) | Rule not added; the app still goes in the box |
| An optional background service | .rpm: **Add to the system** recommended. .deb: box, without it |
| A service the app turns on itself (Docker Desktop) | Has to go on the system |
| An app that runs as root (Timeshift) | Not installed |
| A driver, firmware, printer or scanner driver, login or network plugin, or a service with no app | Has to go on the system. .rpm: added. .deb: refused |

Rules from packages the install pulls in (`solaar` brings `solaar-udev`) are
offered too.

### Install from Fedora

When Fedora's own repositories have the package, it recommends **Install from
Fedora**, which System Update keeps current. **Use the file** never updates.

### Restarting after adding to the system

Added apps work after a restart: **Restart now** or **Later**. At the next login
a message says whether it's ready.

### Updates

| Updates line | Means |
|--------------|-------|
| Updates: automatic, with System Update. | From Fedora, or the package added its maker's source (Chrome, VS Code) |
| Updates: automatic. | From Bazaar (Flathub) |
| Updates: checked once a day, straight from ArtCraft. | An ArtCraft app; checked at login, signature checked |
| Updates: none, because it came from a file. To update, install a newer file. | From a plain file |

Before installing, **Use the file**, **Install the file too** and **Install it
here too** say the same. The package's install script is read first, so
Chrome and VS Code show that they update.

### Already installed

| Already there | Buttons |
|---------------|---------|
| Part of EvenKeelOS, from Fedora, or the same or older file on the system | OK |
| Newer file, on the system or in its box | **Update**, Cancel |
| Same version in its box | **Open it**, **Reinstall**, Cancel |
| Older file than in its box | **Install the older version**, Cancel |
| From Bazaar | **Open it**, **Install the file too**, Cancel |
| In the other box | **Open it**, **Install it here too**, Cancel |

### Files that cannot be installed

One OK button, nothing installed: a damaged download, a 32-bit file, a file for
another kind of computer (ARM), an app that runs as root, or a .deb that needs
the system (with where to look instead).

### Download sources

A file with only a download source (RPM Fusion's setup file,
`packages-microsoft-prod.deb`) offers **Add it**, then lists the apps it has. The
one you pick updates from that source.

### Printer drivers

Most printers need no driver, so it recommends **Open Printers** first.
**Install the driver** (.rpm) adds it to the system, from Fedora when Fedora has
it. A .deb driver can't go on the system; the window says how to get the .rpm
from the maker.

### Start Apps at Login

**Start Apps at Login** switches box apps on or off at login. An app's own
open-at-login setting (Discord) is pointed at its box.

### Removing apps

**Remove Apps** lists what Install Package File installed, with each box's size.
**Remove** takes out the app, its entry and any rule it added. When a box is
left empty, it recommends **Delete the box**; **Keep it** saves setup time. A
Flathub app or system app removed another way (Bazaar, `rpm-ostree uninstall`)
is left off the list, and an app that's already gone just comes off it. The record is
`~/.local/share/evenkeel-os/apps.json`.

### Repairing a box

If a box stops working, **Repair the box** rebuilds it and puts its apps back.
**Repair App Boxes** does it any time. Your files aren't touched.

### Disk space

It checks free space first. When it's low it recommends **Cancel**; **Try
anyway** stops safely if space runs out.

### One at a time

If another install or removal is running, it waits for it, with Cancel.

### Progress and notifications

Progress shows plain steps, with **Cancel** while a box is set up; a cancelled
setup leaves nothing behind. Each box gets zenity and notify-send, which apps
expect.

### Starting and stopping box apps

Box apps start through `evenkeel-os-box-run`, with their output in
`~/.cache/evenkeel-os/logs/<app>.log`, so they don't crash if their link goes
away. Right-click a box app for two Quit items: **Quit <app name>** really stops
it (it takes a few seconds, and GNOME may show "not responding"; wait), while
GNOME's plain **Quit** only closes its windows.

### When something goes wrong

The window says what failed in plain words, or shows the end of the log. The
full log is `~/.cache/evenkeel-os/packages/last.log`. To see what a package
needs: `evenkeel-os-packages check FILE`.

## Windows programs (.exe and .msi)

Windows programs can't run here. Opening an .exe or .msi file starts
**Windows Program**, which reads the file's own name, maker, product code and
description (nothing in it is ever run) and offers a Linux app, first match
wins:

| What the file is | What's offered |
| --- | --- |
| Zoom | Opens Zoom in the web browser: nothing to install |
| A program whose maker has a Linux version | That version: from Flathub, or else from Fedora or Ubuntu into the Fedora box (or Ubuntu box) |
| An Adobe program | The matching ArtCraft app (Photoshop: PhotoCraft, Illustrator: VectorCraft, Premiere: FilmCraft, Acrobat: PdfCraft, and so on) |
| A known program with no Linux version (Office, iTunes, Skype, MSN Messenger, Publisher) | The Linux app picked for it, from the replacements list |
| Any other program winget knows | A Linux app of the same kind, from its winget tags |
| A program nobody lists | A Linux app for the job its installer describes ("Digital Media Player") |
| Nothing fits | Windows programs can't run here, with where to look |

The window says why ("For video calls, Zoom does the same job") and offers
**Install**, or **Open** when the app is already installed. Apps installed this
way are listed in **Remove Apps**.

The list is made fresh at every build from
[winget](https://github.com/microsoft/winget-pkgs)'s program index, the app
lists of [Flathub](https://flathub.org/), Fedora and Ubuntu, and
`build_files/windows-replacements.json`. Same-program matches are sure ones
only: the same name from the same maker.

ArtCraft apps come straight from [ArtCraft](https://getartcraft.com/)'s
releases on GitHub and are installed only when ArtCraft's signature checks out
against its release key, which the image pins. They stay in their sandbox: the
permission ArtCraft's apps ask for to run programs outside it is turned off.
Once a day at login they are updated the same way.

To see what a file is without any window:
`evenkeel-os-packages check-windows FILE`.
