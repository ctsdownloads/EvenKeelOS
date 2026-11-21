# Zoom meetings

[Back to the EvenKeelOS README](../README.md)

## Zoom meetings

Zoom runs in the browser here; the Zoom app isn't needed. Joining a meeting
from a Zoom invite opens it in Zoom's web version, in **Google Chrome**, with
its passcode already filled in.

### Joining a meeting

1. Click the Zoom invite link. Zoom's page opens in Firefox and tries to start
   the Zoom app.
2. Firefox asks whether to open the link. Choose to open it (tick the box to always
   allow it, so it doesn't ask again).
3. The meeting opens in Zoom's web version, in Chrome.

The first time, if Chrome isn't installed, one window asks:

| Button | What happens |
| --- | --- |
| **Install Chrome** | Installs Chrome from Flathub (it updates by itself), then opens the meeting in it. If Chrome can't be installed, the meeting opens in the usual browser |
| **Use the usual browser** | Opens the meeting there, now and from then on |
| Cancel | Opens nothing |

To be asked about Chrome again, delete `~/.local/share/evenkeel-os/zoom-browser`.

### Why Chrome

In a Zoom meeting, Chrome can share a browser tab with its sound (a video
playing in a tab, say); Firefox can't. On Linux no browser can share the whole
computer's sound, only a tab's. Video, the microphone and sharing the screen
work in both.

### Good to know

- Zoom's web version has fewer features than the Zoom app; meetings, video,
  sound and screen sharing work.
- Host links (starting a meeting you host) open Zoom's sign-in page first.
- Zoom for Government links stay on Zoom for Government.
- Only Zoom's own sites are ever opened from a Zoom link.
- If the Zoom app itself is installed from Flathub, Zoom links open in the app
  instead.
- If another app tool is busy installing, the meeting opens in the usual
  browser without asking.
- Opening the Windows Zoom installer (an .exe or .msi) offers the same thing:
  Zoom in the browser.

### Trying it

Go to [zoom.us/test](https://zoom.us/test) in Firefox and click **Join**:
Zoom's test meeting opens the same way, with no account needed.
