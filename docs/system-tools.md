# System Tools

[Back to the EvenKeelOS README](../README.md)

## System Tools

**System Tools** (in Show Apps) puts useful `ujust` jobs in plain windows.

| Tool | What it does |
|------|--------------|
| Update firmware | Installs BIOS and device firmware updates. Keep it plugged in |
| Unlock disk automatically | Lets the security chip (TPM) unlock an encrypted disk at startup |
| Free up disk space | Removes unused app parts, old update files and container images. Your files aren't touched |
| Restart into BIOS settings | Restarts straight into the BIOS screen |
| Automatic updates | Turns daily updates on or off. On is recommended. After an undo it shows the pause, with **Resume now** |
| Undo the last update | Goes back to the version before the last update |
| Save problem details | Saves recent errors to one file to email your helper |
| Setup checklist | Codecs, disk unlock and apps. See [First login](install.md#first-login) |
| Test automatic rollback | Checks that the computer goes back by itself when a new version doesn't start. See below |
| Desktop layout | Switches between the standard top bar and the Windows-style bottom bar and start menu, which opens on the desktop at login. Log out and back in to see it |

**Passwords.** No password for an admin at the computer: automatic updates on,
the pause after an undo and resuming it, disk unlock (it asks the disk password
instead) and freeing space. These keep the admin password, because a bad
program could misuse them: automatic updates off, undo, firmware, the rollback
test, and adding apps to the system.
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
test worked. The test copy takes the place of the earlier version kept for
Undo, so Undo has nothing to go back to until the next update. Needs the admin
password, and a computer installed from a newer live USB (see
[Automatic rollback](install.md#updating-and-rolling-back)). If the computer is
still running a test copy, the tool offers to remove its marker instead
(`rpm-ostree kargs --delete=evenkeel_os.test_rollback=KIND`).

**Save problem details.** Saves `problem-details-<date>.txt` to Documents:
system version and hardware, recent warnings and errors, the last 3 days of
updates, Flatpaks and boxes, and the logs of Install Package File and System
Tools. Box apps' own logs stay out. Nothing is sent anywhere.
