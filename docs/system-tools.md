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
| Automatic updates | Turns daily updates on or off. On is recommended |
| Undo the last update | Goes back to the version before the last update |
| Save problem details | Saves recent errors to one file to email your helper |
| Setup checklist | Codecs, disk unlock and apps. See [First login](install.md#first-login) |

**Passwords.** No password for an admin at the computer: automatic updates on,
disk unlock (it asks the disk password instead) and freeing space. These keep
the admin password, because a bad program could misuse them: automatic updates
off, undo, firmware, and adding apps to the system.

**Unlock disk automatically.**

- Needs a disk encrypted at install and a TPM 2.0 chip. Secure Boot should be on.
- Asks for the disk password once, then a restart. Five wrong passwords lock it
  for an hour.
- If the disk moves or startup settings change (a BIOS update, Secure Boot off),
  the disk password is asked again. Turn it back on in System Tools.

**Undo the last update.** Sets the previous version to start next time (like
`rpm-ostree rollback`). A downloaded update waiting for a restart can be dropped
with **Don't use it**. After an undo, **Use the newer version** goes forward
again. The next automatic update puts the newest version back; if the problem
returns, turn off Automatic updates and tell your helper.

**Save problem details.** Saves `problem-details-<date>.txt` to Documents:
system version and hardware, recent warnings and errors, the last 3 days of
updates, Flatpaks and boxes, and the logs of Install Package File and System
Tools. Box apps' own logs stay out. Nothing is sent anywhere.
