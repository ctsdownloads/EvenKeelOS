"""The EvenKeelOS guide: how to do things, step by step, in Wheelhouse and in docs/guide.md.

A topic is (key, title, icon, what it covers, articles); an article is (title, steps); a step is (text, show), where
show is "" or what its Show me button opens: "page:KEY" (a Wheelhouse page), "settings:PANEL" (a Settings page),
or "topic:KEY" (another topic of this guide).
"""

from evenkeel_os_ui import N_

TITLE = N_("EvenKeelOS guide")
INTRO = N_("How to do things on EvenKeelOS, step by step.")
WELCOME = "welcome"

TOPICS = [
    ("welcome", N_("New to EvenKeelOS?"), "dialog-information-symbolic",
     N_("Coming from Windows: where things are, and what's different"), [
         (N_("Where things are"), [
             (N_("Start menu: with the Windows-style layout, the sailboat button at the bottom left. With the standard "
                 "layout, press the Windows key."), "topic:desktop"),
             (N_("Control Panel: Settings, for Wi-Fi, screens, sound, printers and accounts. Wheelhouse, for updates, "
                 "apps and fixes. A ship is steered from its wheelhouse; this is where you steer your computer."), ""),
             (N_("File Explorer: Files."), "topic:files"),
             (N_("Task Manager: Resources. Find it in the start menu."), ""),
             (N_("Word, Excel and PowerPoint: LibreOffice Writer, Calc and Impress. They open and save Office "
                 "files."), ""),
             (N_("Notepad: Text Editor. Photos: Image Viewer. Videos: Celluloid. Music: Lollypop. PDFs: Papers."), ""),
         ]),
         (N_("What's different"), [
             (N_("Windows programs (.exe and .msi) don't run here. Open one anyway: Wheelhouse tells you the version "
                 "for EvenKeelOS, or a replacement when there is one, and installs it."), "topic:apps"),
             (N_("Updates install on their own. If one stops the computer starting properly, it goes back to the "
                 "version "
                 "before by itself and tells you."), "page:updates"),
             (N_("The system itself can't be changed by apps or by mistake. Each update replaces it whole."), ""),
             (N_("Every network is Home, Work or a Public place. A new one is a Public place, where nothing can reach "
                 "your computer."), "page:network"),
         ]),
     ]),
    ("desktop", N_("The desktop"), "video-display-symbolic",
     N_("The start menu, windows, the menu at the end of the bar, notifications, screenshots and shortcuts"), [
         (N_("Open an app"), [
             (N_("With the Windows-style layout: click the sailboat button at the bottom left, then click the app, or "
                 "start typing its name and press Enter."), ""),
             (N_("With the standard layout: press the Windows key, start typing the app's name, and press Enter. Or "
                 "press Windows key + A to see every app."), ""),
         ]),
         (N_("Open Wheelhouse"), [
             (N_("With the Windows-style layout: click the sailboat button at the bottom left, then Wheelhouse."), ""),
             (N_("With the standard layout: click the logo at the top left, then Wheelhouse."), ""),
         ]),
         (N_("Change the layout"), [
             (N_("Open Wheelhouse, Make it yours."), "page:yours"),
             (N_("Pick Windows-style (a bar at the bottom and a start menu) or Standard (a bar at the top and a "
                 "dock)."),
              ""),
             (N_("Log out and back in to see it."), ""),
         ]),
         (N_("Move and arrange windows"), [
             (N_("The buttons at a window's top right minimize, maximize and close it, as on Windows."), ""),
             (N_("Drag a window to the top of the screen to fill the screen. Drag it to the left or right edge to fill "
                 "that half."), ""),
             (N_("Or use the keyboard: Windows key + Up fills the screen, Windows key + Left or Right fills a half, "
                 "and "
                 "Windows key + H minimizes."), ""),
             (N_("Alt+Tab switches between apps. Alt and the key above Tab switches between windows of the same app."),
              ""),
         ]),
         (N_("Wi-Fi, sound, brightness and power"), [
             (N_("Click the icons at the end of the bar: the bottom right with the Windows-style layout, the top right "
                 "with the standard one. Or press Windows key + S."), ""),
             (N_("The menu that opens has Wi-Fi, Bluetooth, the sound volume, the screen brightness, the power mode, "
                 "dark style and night light."), ""),
             (N_("The power button in that menu has Suspend, Restart, Power Off and Log Out."), ""),
             (N_("Windows key + L locks the screen."), ""),
         ]),
         (N_("Notifications"), [
             (N_("Click the clock to see your notifications and the calendar. Or press Windows key + V."), ""),
             (N_("Do Not Disturb, in the same place, keeps notifications quiet until you turn it off."), ""),
             (N_("To choose which apps can notify you: Settings, Notifications."), "settings:notifications"),
         ]),
         (N_("Take a screenshot or record the screen"), [
             (N_("Press Print Screen. Pick the whole screen, a window, or drag over an area, then click the round "
                 "button."), ""),
             (N_("The picture is copied, ready to paste, and saved in Pictures, Screenshots."), ""),
             (N_("To record a video instead, click the video camera icon in the same tool before you start. Recordings "
                 "go to Videos, Screencasts."), ""),
             (N_("Shift+Print Screen takes a picture of the whole screen straight away."), ""),
         ]),
     ]),
    ("files", N_("Files"), "folder-symbolic",
     N_("Your folders, USB drives, the trash, searching, zip files and sharing with other computers"), [
         (N_("Find your files"), [
             (N_("Open Files from the start menu or the dock. It opens on your home folder."), ""),
             (N_("Documents, Downloads, Pictures, Music and Videos are there, as on Windows."), ""),
             (N_("Click the magnifying glass, or press Ctrl+F, and type to search this folder and the folders in it."),
              ""),
             (N_("Ctrl+H shows hidden files and folders, whose names start with a dot. Most hold app settings: leave "
                 "them alone."), ""),
         ]),
         (N_("USB drives and memory cards"), [
             (N_("Plug it in. It shows in the left side of Files."), ""),
             (N_("Copy files by dragging them onto it, or with Ctrl+C and Ctrl+V."), ""),
             (N_("Before you unplug it, click the eject button next to its name, and wait until it's gone from the "
                 "list."), ""),
         ]),
         (N_("Delete a file, or get it back"), [
             (N_("Select it and press Delete. It goes to the Trash."), ""),
             (N_("To get it back: open Trash in the left side of Files, right-click the file, and choose Restore From "
                 "Trash."), ""),
             (N_("To free the space for good: open Trash and click Empty."), ""),
         ]),
         (N_("Zip files"), [
             (N_("To make one: select the files, right-click, choose Compress, give it a name, and click Create."), ""),
             (N_("To open one: right-click it and choose Extract. The files go in a folder next to it."), ""),
         ]),
         (N_("Choose which app opens a file"), [
             (N_("Right-click the file and choose Open With."), ""),
             (N_("Pick the app. To use it every time for that kind of file, turn on Always use for this file type "
                 "first."), ""),
             (N_("For the web browser, email, calendar, music, videos and photos: Settings, Apps, Default Apps."),
              "settings:applications"),
         ]),
         (N_("Open your folders from another computer at home"), [
             (N_("Open Wheelhouse, Shared folders."), "page:sharing"),
             (N_("Set a sharing password, then turn on Share folders on Home networks."), ""),
             (N_("Click Add a folder and pick it. It starts as Read only: change it to Read and write if the other "
                 "computer should save there too."), ""),
             (N_("On a Windows PC: File Explorer, Network. The Windows PC's own network must be set to Private."), ""),
             (N_("On a Mac: Finder, Network. On another Linux computer: Files, Network."), ""),
             (N_("Open this computer, type your user name and the sharing password, and the folders are there."), ""),
             (N_("Away from home, the switch shows off: sharing only runs on a Home network, and comes back by itself "
                 "there."), ""),
         ]),
     ]),
    ("apps", N_("Apps"), "system-software-install-symbolic",
     N_("Getting apps, Windows programs, package files, removing apps, default apps, Zoom, VPNs and codecs"), [
         (N_("Get an app"), [
             (N_("Open Bazaar, the app store, from the start menu or the dock."), "page:apps"),
             (N_("Search for the app, open it, and click Install."), ""),
             (N_("Apps from Bazaar update on their own. Remove them in Bazaar too."), ""),
         ]),
         (N_("A Windows program you downloaded (.exe or .msi)"), [
             (N_("Open the file, or drop it on Wheelhouse, Apps."), "page:apps"),
             (N_("It tells you whether there's a version for EvenKeelOS, or a replacement that does the same "
                 "job."), ""),
             (N_("Click Install, and it installs that instead."), ""),
         ]),
         (N_("An app that comes as a .rpm or .deb file"), [
             (N_("Open the file, or use Install a package file in Wheelhouse, Apps."), "page:apps"),
             (N_("It says first whether the app keeps itself updated, then installs it."), ""),
             (N_("Some, like printer drivers, are added to the system: they're ready after the next restart."), ""),
         ]),
         (N_("Remove an app"), [
             (N_("Apps from Bazaar: open Bazaar and remove it there."), ""),
             (N_("Apps from a file, Get a VPN or a Windows program: Wheelhouse, Apps, Remove apps."), "page:apps"),
         ]),
         (N_("Start an app when you log in"), [
             (N_("Apps from Bazaar have this setting inside the app."), ""),
             (N_("Apps from a file: open Wheelhouse, Apps, Start apps at login, and pick the app. Picking it again "
                 "stops it."), "page:apps"),
         ]),
         (N_("Default apps"), [
             (N_("Open Settings, Apps, Default Apps."), "settings:applications"),
             (N_("Pick the app for the web, mail, calendar, music, videos and photos."), ""),
         ]),
         (N_("Zoom meetings"), [
             (N_("Click the meeting link you were sent."), ""),
             (N_("The first time, choose Install Chrome or Use the usual browser. The meeting opens in Zoom's web "
                 "version."), ""),
             (N_("To be asked again: Wheelhouse, Apps, Zoom meetings."), "page:apps"),
         ]),
         (N_("A VPN"), [
             (N_("Open Wheelhouse, Apps, Get a VPN."), "page:apps"),
             (N_("Pick Mullvad, Proton, IVPN or NordVPN. It's added from that company's own download source, and kept "
                 "up to date."), ""),
             (N_("Restart, then sign in with your account from that company."), ""),
         ]),
         (N_("Media codecs, for some videos"), [
             (N_("Open Wheelhouse, Apps, Media codecs."), "page:apps"),
             (N_("Pick what you need. It explains each choice."), ""),
         ]),
         (N_("A broken app box"), [
             (N_("Some apps from .rpm or .deb files run in an app box. If one stops starting, open Wheelhouse, Apps, "
                 "Repair app boxes."), "page:apps"),
             (N_("Pick the box. It's set up again, with its apps. Your files aren't touched."), ""),
         ]),
     ]),
    ("internet", N_("Internet and networks"), "network-wireless-symbolic",
     N_("Wi-Fi, how safe each network is, and Bluetooth"), [
         (N_("Join a Wi-Fi network"), [
             (N_("Click the icons at the end of the bar, then the arrow next to Wi-Fi. Or open Settings, Wi-Fi."),
              "settings:wifi"),
             (N_("Click the network's name, type its password, and press Enter."), ""),
             (N_("For a network with a password, a small window then asks where it is: Home, Work or Public place. "
                 "Not sure? Keep Public place."), "page:network"),
         ]),
         (N_("Home, Work or Public place"), [
             (N_("Open Wheelhouse, Network safety. Your networks lists every network this computer has joined."),
              "page:network"),
             (N_("Public place: nothing on the network can reach your computer. Pick it for cafes, hotels and "
                 "airports."),
              ""),
             (N_("Home: your phone and other computers can reach apps that ask for it, like file sharing."), ""),
             (N_("Work: like a Public place, nothing gets in and your folders aren't shared. The office's own shared "
                 "drives still open."), ""),
             (N_("Pick the place next to a network. It changes at once."), ""),
             (N_("Open Wi-Fi, with no password, is always a Public place, because anyone can make one with the same "
                 "name."), ""),
         ]),
         (N_("Let other computers in"), [
             (N_("Open Wheelhouse, Network safety. Under Also let in, on Home, there are two switches."),
              "page:network"),
             (N_("Log in from another computer (SSH): for people who use a terminal. Leave it off if you don't know "
                 "it."),
              ""),
             (N_("Share my printer: lets other computers use a printer plugged into this one."), ""),
             (N_("Both ask for your password, and work only on Home."), ""),
         ]),
         (N_("Let an app or game in"), [
             (N_("Open Wheelhouse, Network safety. Under Apps and ports let in, pick the place."), "page:network"),
             (N_("Click Let an app in, type its name, like Minecraft or Jellyfin, and click it."), ""),
             (N_("Not in the list? Click Open a port and type the number the app's own instructions give."), ""),
             (N_("On a Public place it asks first, because strangers could reach it too. The bin next to it closes it "
                 "again."), ""),
         ]),
         (N_("Connect a Bluetooth device"), [
             (N_("Open Settings, Bluetooth, and turn on the switch at the top."), "settings:bluetooth"),
             (N_("Put the device in pairing mode. Its instructions say how, often by holding its power button."), ""),
             (N_("Click the device's name when it shows in the list."), ""),
         ]),
     ]),
    ("printing", N_("Printing"), "printer-symbolic",
     N_("Adding a printer, and printer driver files from the maker"), [
         (N_("Add a printer"), [
             (N_("Turn the printer on. Plug it in with its cable, or join it to the same Wi-Fi."), ""),
             (N_("Open Settings, Printers, and click Add Printer."), "settings:printers"),
             (N_("Click the printer when it shows, then Add. Most printers need nothing else."), ""),
             (N_("To print, press Ctrl+P in any app."), ""),
         ]),
         (N_("A driver file from the maker"), [
             (N_("Most printers don't need one. Try Add a printer first."), ""),
             (N_("If yours does, download the maker's .rpm file and open it from Downloads. Wheelhouse sees that "
                 "it's a printer driver."), ""),
             (N_("Click Install the driver, type your password, and restart. Then add the printer."), ""),
             (N_("A .deb driver can't be installed. The window says how to get the .rpm from the maker."), ""),
         ]),
     ]),
    ("updates", N_("Updates and safety"), "software-update-available-symbolic",
     N_("Automatic updates, undoing an update, firmware and certificate alerts"), [
         (N_("Updates happen on their own"), [
             (N_("Every day at 4 am, or at the next start, the system, your apps and app boxes update."), ""),
             (N_("A new system version is used from the next restart. Keep working, and restart when it suits you."),
              ""),
             (N_("To update now: open Wheelhouse, Updates, System Update."), "page:updates"),
         ]),
         (N_("Turn automatic updates off or on"), [
             (N_("Open Wheelhouse, Updates, Automatic updates. On is recommended."), "page:updates"),
             (N_("Click Turn off or Turn on. Turning them off asks for your password."), ""),
         ]),
         (N_("Undo the last update"), [
             (N_("If something stopped working after an update, open Wheelhouse, Updates, Undo the last update."),
              "page:updates"),
             (N_("Click Undo the update, type your password, and restart. Your files and apps aren't touched."), ""),
             (N_("Automatic updates pause for 3 days, so the same update doesn't come straight back. They turn back on "
                 "by themselves."), ""),
             (N_("Changed your mind? Open Undo the last update again and click Use the newer version."), ""),
         ]),
         (N_("If the computer won't start properly"), [
             (N_("You don't need to do anything. If a new version fails to start twice in a row, the computer goes "
                 "back "
                 "to the version before by itself."), ""),
             (N_("A new version also goes back if something that worked before is broken after you log in, like "
                 "sound, Wi-Fi, Bluetooth, the camera or printing. Unplugged or switched-off things don't count."), ""),
             (N_("A note at the next login says so and names what broke, and automatic updates pause for 3 days."), ""),
             (N_("To check that this works on your computer, see Getting help."), "topic:help"),
         ]),
         (N_("Update firmware"), [
             (N_("Firmware is the software built into the computer's own parts, like the BIOS."), ""),
             (N_("Plug the computer in. Open Wheelhouse, Updates, Update firmware."), "page:updates"),
             (N_("If updates are listed, click Update and type your password. Some finish while the computer "
                 "restarts."),
              ""),
         ]),
         (N_("Certificate alerts"), [
             (N_("Certificates are how the computer knows a secure website is real. An alert shows when one has "
                 "expired, "
                 "expires soon, or was removed."), ""),
             (N_("Open Wheelhouse, Get help, Certificate alerts to see them."), "page:help"),
             (N_("For an expired one that was added to this computer, it offers Remove it. Fedora's own ones are "
                 "replaced by updates, so keep automatic updates on."), ""),
         ]),
     ]),
    ("yours", N_("Making it yours"), "applications-graphics-symbolic",
     N_("The layout, colors, wallpaper, dark at night, fonts, screen size, night light, sound and accounts"), [
         (N_("Layout"), [
             (N_("Open Wheelhouse, Make it yours, Desktop layout."), "page:yours"),
             (N_("Pick Windows-style or Standard, click Switch, then log out and back in."), ""),
         ]),
         (N_("Colors and wallpaper"), [
             (N_("Open Settings, Appearance."), "settings:background"),
             (N_("Style: Default (light) or Dark. Accent Color: the color of buttons and folder icons."), ""),
             (N_("Background: click a picture. To use your own photo, click Add Picture."), ""),
         ]),
         (N_("Dark at night, light in the day"), [
             (N_("Open Wheelhouse, Make it yours, Light and dark."), "page:yours"),
             (N_("Pick Sunset to sunrise, or Custom times and pick when dark starts and ends."), ""),
             (N_("You can still switch it yourself. It stays that way until the next change."), ""),
         ]),
         (N_("A slideshow of your own pictures"), [
             (N_("Put the pictures in one folder, for example in Pictures."), ""),
             (N_("Open Wheelhouse, Make it yours, Wallpaper slideshow, and click Choose."), "page:yours"),
             (N_("Pick the folder, then how often it changes: every hour, every day or at each login."), ""),
         ]),
         (N_("Fonts and text size"), [
             (N_("Open Wheelhouse, Make it yours, Fonts and text."), "page:yours"),
             (N_("Click a font to pick another, or change Text size. 1.00 is the normal size."), ""),
             (N_("Click Back to the original to undo all of it."), ""),
         ]),
         (N_("Make everything bigger or smaller"), [
             (N_("Open Settings, Displays."), "settings:display"),
             (N_("Change Scale. A bigger number makes everything bigger."), ""),
             (N_("Click Apply, then Keep Changes if it looks right."), ""),
         ]),
         (N_("Night light"), [
             (N_("Night light makes the screen warmer in the evening, which is easier on the eyes."), ""),
             (N_("Open Settings, Displays, Night Light, and turn it on. It follows sunset and sunrise, or set your own "
                 "times."), "settings:display"),
         ]),
         (N_("Sound"), [
             (N_("Open Settings, Sound."), "settings:sound"),
             (N_("Pick the speakers or headphones under Output Device, and the microphone under Input Device."), ""),
             (N_("Click Test to hear each speaker."), ""),
         ]),
         (N_("Your password and other people's accounts"), [
             (N_("Open Settings, System, Users."), "settings:users"),
             (N_("To change your password, click Password."), ""),
             (N_("To give someone their own account, click Add User. Leave Administrator off for children and guests."),
              ""),
         ]),
     ]),
    ("startup", N_("Disk and startup"), "drive-harddisk-symbolic",
     N_("Freeing space, the disk password, boot options and BIOS settings"), [
         (N_("Free up disk space"), [
             (N_("Open Wheelhouse, Disk and startup. The bar shows how much is free."), "page:disk"),
             (N_("Click Free up disk space, then Free up space. Your files and apps aren't touched."), ""),
         ]),
         (N_("Skip the disk password at startup"), [
             (N_("If you type a disk password every time the computer starts, it can unlock by itself with the "
                 "computer's security chip."), ""),
             (N_("Open Wheelhouse, Disk and startup, Unlock disk automatically."), "page:disk"),
             (N_("Click Turn on, type the disk password once, and restart."), ""),
             (N_("After a BIOS update, it may ask for the disk password again. Turn it on again here."), ""),
         ]),
         (N_("Fix screen flicker or a drive that freezes"), [
             (N_("Open Wheelhouse, Disk and startup. Under Common fixes, turn on the one that matches the problem."),
              "page:disk"),
             (N_("Type your password, then restart. The fix starts at the restart."), ""),
             (N_("Didn't help? Turn it off again, and restart."), ""),
             (N_("Told to add a setting by a helper? Type it under Your own settings. Risky ones are explained first."),
              ""),
         ]),
         (N_("BIOS settings"), [
             (N_("Open Wheelhouse, Disk and startup, Restart into BIOS settings."), "page:disk"),
             (N_("Save your work, then click Restart now."), ""),
             (N_("The BIOS screen uses the keyboard. When you're done, choose Save and Exit, or Exit."), ""),
         ]),
     ]),
    ("help", N_("Getting help"), "help-about-symbolic",
     N_("Sending details to your helper, checking rollback, and terminal commands"), [
         (N_("Send details to your helper"), [
             (N_("Open Wheelhouse, Get help, Save problem details."), "page:help"),
             (N_("Click Save details. It makes one file of recent errors, in Documents. Nothing is sent "
                 "anywhere."), ""),
             (N_("Click Show the file, then attach it to an email to your helper."), ""),
         ]),
         (N_("Something stopped working after an update"), [
             (N_("Undo it. See Updates and safety."), "topic:updates"),
         ]),
         (N_("Check that automatic rollback works"), [
             (N_("Open Wheelhouse, Get help, Test automatic rollback. Save your work first."), "page:help"),
             (N_("Pick a test, click Start the test, and type your password."), ""),
             (N_("For the tests that break one thing, like Sound driver blocked, log in when the login screen "
                 "shows."), ""),
             (N_("For those, a window asks before each restart. Click Restart now, or Not yet to save your work "
                 "first."), ""),
             (N_("The computer restarts, fails on purpose, then goes back by itself. A note at login says the test "
                 "worked and what the test copy found broken."), ""),
         ]),
         (N_("Prefer the terminal?"), [
             (N_("Open Wheelhouse, Get help, and scroll to the end. Every tool has its command there."), "page:help"),
             (N_("Click the copy button next to a command, then paste it in Terminal."), ""),
         ]),
     ]),
]


def topic(key):
    return next(t for t in TOPICS if t[0] == key)


def markdown():
    """The guide as docs/guide.md: always the English text, never translated."""
    out = [f"# {TITLE}", "", INTRO, ""]
    for _key, title, _icon, about, articles in TOPICS:
        out += [f"## {title}", "", f"{about}.", ""]
        for heading, steps in articles:
            out += [f"### {heading}", ""] + [f"{n}. {text}" for n, (text, _) in enumerate(steps, 1)] + [""]
    return "\n".join(out)
