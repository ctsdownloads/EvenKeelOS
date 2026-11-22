# VPNs

[Back to the EvenKeelOS README](../README.md)

## VPNs

**Get a VPN** (in System Tools) adds a VPN app: Mullvad, Proton, IVPN or NordVPN. It comes from that company's own
download source, so it keeps updating. Nothing is installed until someone picks one.

### Getting a VPN

1. Open **System Tools**, go to Apps and pick **Get a VPN**.
2. Pick Mullvad, Proton, IVPN or NordVPN.
3. Confirm, then type the password.
4. It adds that company's download source to the system, and adds the app to the system (not a box).
5. It offers a restart: **Restart now** or **Later**.

Each company's download source is locked to that company's signing key. The key is pinned in the image and checked at
every build. Packages not signed by that key are refused.

From the command line: `evenkeel-os-packages vpn` (pick one), `evenkeel-os-packages vpn mullvad|proton|ivpn|nordvpn`,
or `evenkeel-os-tools vpn`.

### After the restart

At login it asks **Turn it on**. It needs the password once. That turns on the VPN's background service and starts it.

Why: this kind of system ignores an app installer's own step that turns on its service. So EvenKeelOS does that step
after the restart.

For NordVPN it also adds your account to NordVPN's group. Log out and back in once after that, so NordVPN lets your
account use it.

If you choose **Later**, it asks again at the next login.

### From a downloaded file or a Windows installer

Opening a downloaded VPN file with **Install a package file** installs that VPN from its company's own download source
instead of the file, so it keeps updating. This covers:

- Mullvad's or IVPN's .rpm.
- Proton's or NordVPN's setup file, for example `protonvpn-stable-release` or `nordvpn-release`.
- .deb files with the same package names.

There is no **Use the file** choice for these. A VPN from a file would never update. IVPN's files are only part of the
app. Proton's and NordVPN's setup files only add the download source.

Opening the Windows installer (an .exe or .msi) of Mullvad VPN, Proton VPN, IVPN or NordVPN offers that VPN's Linux
version the same way, from the company's own source. See
[Windows programs](apps.md#windows-programs-exe-and-msi).

### Updates

A daily check (`evenkeel-os-app-updates.timer`) asks the download sources of every app added to the system by name
whether a newer version exists. That means the VPNs, apps added "from Fedora", and media codecs.

If there is one, it runs the system upgrade. The new version starts at the next restart, like any system update.

- It only runs while automatic updates are on.
- It doesn't run during the 3-day pause after **Undo the last update**.
- It skips if System Update is already running, or if a new version is already waiting for a restart.

Why: System Update looks for a new EvenKeelOS version. Without this check, an app from its own download source would
wait for the next EvenKeelOS build. This was tested on a real install: a newer version in a non-Fedora download
source was picked up by the system upgrade with no new EvenKeelOS build.

### Removing a VPN

Open System Tools, Apps, **Remove apps** and remove it. That turns off its background service, removes the app and
removes its download source. For NordVPN it also removes the group it added for your account, and its log folder.
Then restart. Nothing is left behind. See [Removing apps](apps.md#removing-apps).

### Good to know

- Connecting needs an account with that VPN company. EvenKeelOS doesn't sign you up for anything.
- Not supported: PIA (Private Internet Access) and other VPNs that only offer a .run or script installer, or that
  require subscribing before download.
- Proton uses a different signing key for each Fedora version. If the running Fedora version has no pinned Proton key
  yet, Get a VPN says Proton isn't available for that Fedora version yet.
- Any app added to the system from an .rpm file whose installer turns on a background service (not only VPNs) gets the
  same **Turn it on** question after the restart. Only services that belong to that app, and that its own installer
  asks for, are turned on.
- Not yet tested on a real machine: connecting with each VPN, and IVPN's and NordVPN's service setup.
