"""The EvenKeelOS guide: how to do things, step by step, in System Tools and in docs/guide.md.

A topic is (key, title, icon, what it covers, articles); an article is (title, steps); a step is (text, show), where
show is "" or what its Show me button opens: "page:KEY" (a System Tools page), "settings:PANEL" (a Settings page),
or "topic:KEY" (another topic of this guide).
"""

TITLE = "EvenKeelOS guide"
INTRO = "How to do things on EvenKeelOS, step by step."
WELCOME = "welcome"

TOPICS = [
    ("welcome", "New to EvenKeelOS?", "dialog-information-symbolic",
     "Coming from Windows: where things are, and what's different", [
         ("Where things are", [
             ("Start menu: with the Windows-style layout, the sailboat button at the bottom left. With the standard "
              "layout, press the Windows key.", "topic:desktop"),
             ("Control Panel: Settings, for Wi-Fi, screens, sound, printers and accounts. System Tools, for updates, "
              "apps and fixes.", ""),
             ("File Explorer: Files.", "topic:files"),
             ("Task Manager: Resources. Find it in the start menu.", ""),
             ("Word, Excel and PowerPoint: LibreOffice Writer, Calc and Impress. They open and save Office files.", ""),
             ("Notepad: Text Editor. Photos: Image Viewer. Videos: Celluloid. Music: Lollypop. PDFs: Papers.", ""),
         ]),
         ("What's different", [
             ("Windows programs (.exe and .msi) don't run here. Open one anyway: System Tools tells you the version "
              "for EvenKeelOS, or a replacement when there is one, and installs it.", "topic:apps"),
             ("Updates install on their own. If one stops the computer starting properly, it goes back to the version "
              "before by itself and tells you.", "page:updates"),
             ("The system itself can't be changed by apps or by mistake. Each update replaces it whole.", ""),
             ("Every network is Home, Work or a Public place. A new one is a Public place, where nothing can reach "
              "your computer.", "page:network"),
         ]),
     ]),
    ("desktop", "The desktop", "video-display-symbolic",
     "The start menu, windows, the menu at the end of the bar, notifications, screenshots and shortcuts", [
         ("Open an app", [
             ("With the Windows-style layout: click the sailboat button at the bottom left, then click the app, or "
              "start typing its name and press Enter.", ""),
             ("With the standard layout: press the Windows key, start typing the app's name, and press Enter. Or "
              "press Windows key + A to see every app.", ""),
         ]),
         ("Open System Tools", [
             ("With the Windows-style layout: click the sailboat button at the bottom left, then System Tools.", ""),
             ("With the standard layout: click the logo at the top left, then System Tools.", ""),
         ]),
         ("Change the layout", [
             ("Open System Tools, Make it yours.", "page:yours"),
             ("Pick Windows-style (a bar at the bottom and a start menu) or Standard (a bar at the top and a dock).",
              ""),
             ("Log out and back in to see it.", ""),
         ]),
         ("Move and arrange windows", [
             ("The buttons at a window's top right minimize, maximize and close it, as on Windows.", ""),
             ("Drag a window to the top of the screen to fill the screen. Drag it to the left or right edge to fill "
              "that half.", ""),
             ("Or use the keyboard: Windows key + Up fills the screen, Windows key + Left or Right fills a half, and "
              "Windows key + H minimizes.", ""),
             ("Alt+Tab switches between apps. Alt and the key above Tab switches between windows of the same app.",
              ""),
         ]),
         ("Wi-Fi, sound, brightness and power", [
             ("Click the icons at the end of the bar: the bottom right with the Windows-style layout, the top right "
              "with the standard one. Or press Windows key + S.", ""),
             ("The menu that opens has Wi-Fi, Bluetooth, the sound volume, the screen brightness, the power mode, "
              "dark style and night light.", ""),
             ("The power button in that menu has Suspend, Restart, Power Off and Log Out.", ""),
             ("Windows key + L locks the screen.", ""),
         ]),
         ("Notifications", [
             ("Click the clock to see your notifications and the calendar. Or press Windows key + V.", ""),
             ("Do Not Disturb, in the same place, keeps notifications quiet until you turn it off.", ""),
             ("To choose which apps can notify you: Settings, Notifications.", "settings:notifications"),
         ]),
         ("Take a screenshot or record the screen", [
             ("Press Print Screen. Pick the whole screen, a window, or drag over an area, then click the round "
              "button.", ""),
             ("The picture is copied, ready to paste, and saved in Pictures, Screenshots.", ""),
             ("To record a video instead, click the video camera icon in the same tool before you start. Recordings "
              "go to Videos, Screencasts.", ""),
             ("Shift+Print Screen takes a picture of the whole screen straight away.", ""),
         ]),
     ]),
    ("files", "Files", "folder-symbolic",
     "Your folders, USB drives, the trash, searching, zip files and sharing with other computers", [
         ("Find your files", [
             ("Open Files from the start menu or the dock. It opens on your home folder.", ""),
             ("Documents, Downloads, Pictures, Music and Videos are there, as on Windows.", ""),
             ("Click the magnifying glass, or press Ctrl+F, and type to search this folder and the folders in it.",
              ""),
             ("Ctrl+H shows hidden files and folders, whose names start with a dot. Most hold app settings: leave "
              "them alone.", ""),
         ]),
         ("USB drives and memory cards", [
             ("Plug it in. It shows in the left side of Files.", ""),
             ("Copy files by dragging them onto it, or with Ctrl+C and Ctrl+V.", ""),
             ("Before you unplug it, click the eject button next to its name, and wait until it's gone from the "
              "list.", ""),
         ]),
         ("Delete a file, or get it back", [
             ("Select it and press Delete. It goes to the Trash.", ""),
             ("To get it back: open Trash in the left side of Files, right-click the file, and choose Restore From "
              "Trash.", ""),
             ("To free the space for good: open Trash and click Empty.", ""),
         ]),
         ("Zip files", [
             ("To make one: select the files, right-click, choose Compress, give it a name, and click Create.", ""),
             ("To open one: right-click it and choose Extract. The files go in a folder next to it.", ""),
         ]),
         ("Choose which app opens a file", [
             ("Right-click the file and choose Open With.", ""),
             ("Pick the app. To use it every time for that kind of file, turn on Always use for this file type "
              "first.", ""),
             ("For the web browser, email, calendar, music, videos and photos: Settings, Apps, Default Apps.",
              "settings:applications"),
         ]),
         ("Open your folders from another computer at home", [
             ("Open System Tools, Shared folders.", "page:sharing"),
             ("Set a sharing password, then turn on Share folders on Home networks.", ""),
             ("Click Add a folder and pick it. It starts as Read only: change it to Read and write if the other "
              "computer should save there too.", ""),
             ("On a Windows PC: File Explorer, Network. The Windows PC's own network must be set to Private.", ""),
             ("On a Mac: Finder, Network. On another Linux computer: Files, Other Locations.", ""),
             ("Open this computer, type your user name and the sharing password, and the folders are there.", ""),
         ]),
     ]),
    ("apps", "Apps", "system-software-install-symbolic",
     "Getting apps, Windows programs, package files, removing apps, default apps, Zoom, VPNs and codecs", [
         ("Get an app", [
             ("Open Bazaar, the app store, from the start menu or the dock.", "page:apps"),
             ("Search for the app, open it, and click Install.", ""),
             ("Apps from Bazaar update on their own. Remove them in Bazaar too.", ""),
         ]),
         ("A Windows program you downloaded (.exe or .msi)", [
             ("Open the file, or drop it on System Tools, Apps.", "page:apps"),
             ("It tells you whether there's a version for EvenKeelOS, or a replacement that does the same job.", ""),
             ("Click Install, and it installs that instead.", ""),
         ]),
         ("An app that comes as a .rpm or .deb file", [
             ("Open the file, or use Install a package file in System Tools, Apps.", "page:apps"),
             ("It says first whether the app keeps itself updated, then installs it.", ""),
             ("Some, like printer drivers, are added to the system: they're ready after the next restart.", ""),
         ]),
         ("Remove an app", [
             ("Apps from Bazaar: open Bazaar and remove it there.", ""),
             ("Apps from a file, Get a VPN or a Windows program: System Tools, Apps, Remove apps.", "page:apps"),
         ]),
         ("Start an app when you log in", [
             ("Apps from Bazaar have this setting inside the app.", ""),
             ("Apps from a file: open System Tools, Apps, Start apps at login, and pick the app. Picking it again "
              "stops it.", "page:apps"),
         ]),
         ("Default apps", [
             ("Open Settings, Apps, Default Apps.", "settings:applications"),
             ("Pick the app for the web, mail, calendar, music, videos and photos.", ""),
         ]),
         ("Zoom meetings", [
             ("Click the meeting link you were sent.", ""),
             ("The first time, choose Install Chrome or Use the usual browser. The meeting opens in Zoom's web "
              "version.", ""),
             ("To be asked again: System Tools, Apps, Zoom meetings.", "page:apps"),
         ]),
         ("A VPN", [
             ("Open System Tools, Apps, Get a VPN.", "page:apps"),
             ("Pick Mullvad, Proton, IVPN or NordVPN. It's added from that company's own download source, and kept "
              "up to date.", ""),
             ("Restart, then sign in with your account from that company.", ""),
         ]),
         ("Media codecs, for some videos", [
             ("Open System Tools, Apps, Media codecs.", "page:apps"),
             ("Pick what you need. It explains each choice.", ""),
         ]),
         ("A broken app box", [
             ("Some apps from .rpm or .deb files run in an app box. If one stops starting, open System Tools, Apps, "
              "Repair app boxes.", "page:apps"),
             ("Pick the box. It's set up again, with its apps. Your files aren't touched.", ""),
         ]),
     ]),
    ("internet", "Internet and networks", "network-wireless-symbolic",
     "Wi-Fi, how safe each network is, and Bluetooth", [
         ("Join a Wi-Fi network", [
             ("Click the icons at the end of the bar, then the arrow next to Wi-Fi. Or open Settings, Wi-Fi.",
              "settings:wifi"),
             ("Click the network's name, type its password, and press Enter.", ""),
             ("For a network with a password, a small window then asks where it is: Home, Work or Public place. "
              "Not sure? Keep Public place.", "page:network"),
         ]),
         ("Home, Work or Public place", [
             ("Open System Tools, Network safety. Your networks lists every network this computer has joined.",
              "page:network"),
             ("Public place: nothing on the network can reach your computer. Pick it for cafes, hotels and airports.",
              ""),
             ("Home or Work: your phone and other computers can reach apps that ask for it, like file sharing.", ""),
             ("Pick the place next to a network. It changes at once.", ""),
             ("Open Wi-Fi, with no password, is always a Public place, because anyone can make one with the same "
              "name.", ""),
         ]),
         ("Let other computers in", [
             ("Open System Tools, Network safety. Under Also let in, on Home and Work, there are two switches.",
              "page:network"),
             ("Log in from another computer (SSH): for people who use a terminal. Leave it off if you don't know it.",
              ""),
             ("Share my printer: lets other computers use a printer plugged into this one.", ""),
             ("Both ask for your password, and never work on a Public place.", ""),
         ]),
         ("Connect a Bluetooth device", [
             ("Open Settings, Bluetooth, and turn on the switch at the top.", "settings:bluetooth"),
             ("Put the device in pairing mode. Its instructions say how, often by holding its power button.", ""),
             ("Click the device's name when it shows in the list.", ""),
         ]),
     ]),
    ("printing", "Printing", "printer-symbolic",
     "Adding a printer, and printer driver files from the maker", [
         ("Add a printer", [
             ("Turn the printer on. Plug it in with its cable, or join it to the same Wi-Fi.", ""),
             ("Open Settings, Printers, and click Add Printer.", "settings:printers"),
             ("Click the printer when it shows, then Add. Most printers need nothing else.", ""),
             ("To print, press Ctrl+P in any app.", ""),
         ]),
         ("A driver file from the maker", [
             ("Most printers don't need one. Try Add a printer first.", ""),
             ("If yours does, download the maker's .rpm file and open it from Downloads. System Tools sees that "
              "it's a printer driver.", ""),
             ("Click Install the driver, type your password, and restart. Then add the printer.", ""),
             ("A .deb driver can't be installed. The window says how to get the .rpm from the maker.", ""),
         ]),
     ]),
    ("updates", "Updates and safety", "software-update-available-symbolic",
     "Automatic updates, undoing an update, firmware and certificate alerts", [
         ("Updates happen on their own", [
             ("Every day at 4 am, or at the next start, the system, your apps and app boxes update.", ""),
             ("A new system version is used from the next restart. Keep working, and restart when it suits you.",
              ""),
             ("To update now: open System Tools, Updates, System Update.", "page:updates"),
         ]),
         ("Turn automatic updates off or on", [
             ("Open System Tools, Updates, Automatic updates. On is recommended.", "page:updates"),
             ("Click Turn off or Turn on. Turning them off asks for your password.", ""),
         ]),
         ("Undo the last update", [
             ("If something stopped working after an update, open System Tools, Updates, Undo the last update.",
              "page:updates"),
             ("Click Undo the update, type your password, and restart. Your files and apps aren't touched.", ""),
             ("Automatic updates pause for 3 days, so the same update doesn't come straight back. They turn back on "
              "by themselves.", ""),
             ("Changed your mind? Open Undo the last update again and click Use the newer version.", ""),
         ]),
         ("If the computer won't start properly", [
             ("You don't need to do anything. If a new version fails to start twice in a row, the computer goes back "
              "to the version before by itself.", ""),
             ("A note at the next login says so, and automatic updates pause for 3 days.", ""),
             ("To check that this works on your computer, see Getting help.", "topic:help"),
         ]),
         ("Update firmware", [
             ("Firmware is the software built into the computer's own parts, like the BIOS.", ""),
             ("Plug the computer in. Open System Tools, Updates, Update firmware.", "page:updates"),
             ("If updates are listed, click Update and type your password. Some finish while the computer restarts.",
              ""),
         ]),
         ("Certificate alerts", [
             ("Certificates are how the computer knows a secure website is real. An alert shows when one has expired, "
              "expires soon, or was removed.", ""),
             ("Open System Tools, Get help, Certificate alerts to see them.", "page:help"),
             ("For an expired one that was added to this computer, it offers Remove it. Fedora's own ones are "
              "replaced by updates, so keep automatic updates on.", ""),
         ]),
     ]),
    ("yours", "Making it yours", "applications-graphics-symbolic",
     "The layout, colors, wallpaper, screen size, night light, sound and accounts", [
         ("Layout", [
             ("Open System Tools, Make it yours, Desktop layout.", "page:yours"),
             ("Pick Windows-style or Standard, click Switch, then log out and back in.", ""),
         ]),
         ("Colors and wallpaper", [
             ("Open Settings, Appearance.", "settings:background"),
             ("Style: Default (light) or Dark. Accent Color: the color of buttons and folder icons.", ""),
             ("Background: click a picture. To use your own photo, click Add Picture.", ""),
         ]),
         ("Make everything bigger or smaller", [
             ("Open Settings, Displays.", "settings:display"),
             ("Change Scale. A bigger number makes everything bigger.", ""),
             ("Click Apply, then Keep Changes if it looks right.", ""),
         ]),
         ("Night light", [
             ("Night light makes the screen warmer in the evening, which is easier on the eyes.", ""),
             ("Open Settings, Displays, Night Light, and turn it on. It follows sunset and sunrise, or set your own "
              "times.", "settings:display"),
         ]),
         ("Sound", [
             ("Open Settings, Sound.", "settings:sound"),
             ("Pick the speakers or headphones under Output Device, and the microphone under Input Device.", ""),
             ("Click Test to hear each speaker.", ""),
         ]),
         ("Your password and other people's accounts", [
             ("Open Settings, System, Users.", "settings:users"),
             ("To change your password, click Password.", ""),
             ("To give someone their own account, click Add User. Leave Administrator off for children and guests.",
              ""),
         ]),
     ]),
    ("startup", "Disk and startup", "drive-harddisk-symbolic",
     "Freeing space, the disk password, boot options and BIOS settings", [
         ("Free up disk space", [
             ("Open System Tools, Disk and startup. The bar shows how much is free.", "page:disk"),
             ("Click Free up disk space, then Free up space. Your files and apps aren't touched.", ""),
         ]),
         ("Skip the disk password at startup", [
             ("If you type a disk password every time the computer starts, it can unlock by itself with the "
              "computer's security chip.", ""),
             ("Open System Tools, Disk and startup, Unlock disk automatically.", "page:disk"),
             ("Click Turn on, type the disk password once, and restart.", ""),
             ("After a BIOS update, it may ask for the disk password again. Turn it on again here.", ""),
         ]),
         ("Fix screen flicker or a drive that freezes", [
             ("Open System Tools, Disk and startup. Under Common fixes, turn on the one that matches the problem.",
              "page:disk"),
             ("Type your password, then restart. The fix starts at the restart.", ""),
             ("Didn't help? Turn it off again, and restart.", ""),
             ("Told to add a setting by a helper? Type it under Your own settings. Risky ones are explained first.",
              ""),
         ]),
         ("BIOS settings", [
             ("Open System Tools, Disk and startup, Restart into BIOS settings.", "page:disk"),
             ("Save your work, then click Restart now.", ""),
             ("The BIOS screen uses the keyboard. When you're done, choose Save and Exit, or Exit.", ""),
         ]),
     ]),
    ("help", "Getting help", "help-about-symbolic",
     "Sending details to your helper, checking rollback, and terminal commands", [
         ("Send details to your helper", [
             ("Open System Tools, Get help, Save problem details.", "page:help"),
             ("Click Save details. It makes one file of recent errors, in Documents. Nothing is sent anywhere.", ""),
             ("Click Show the file, then attach it to an email to your helper.", ""),
         ]),
         ("Something stopped working after an update", [
             ("Undo it. See Updates and safety.", "topic:updates"),
         ]),
         ("Check that automatic rollback works", [
             ("Open System Tools, Get help, Test automatic rollback. Save your work first.", "page:help"),
             ("Pick a test, click Start the test, and type your password.", ""),
             ("The computer restarts, fails on purpose, then goes back by itself. A note at login says the test "
              "worked.", ""),
         ]),
         ("Prefer the terminal?", [
             ("Open System Tools, Get help, and scroll to the end. Every tool has its command there.", "page:help"),
             ("Click the copy button next to a command, then paste it in Terminal.", ""),
         ]),
     ]),
]


def topic(key):
    return next(t for t in TOPICS if t[0] == key)


def markdown():
    """The guide as docs/guide.md."""
    out = [f"# {TITLE}", "", INTRO, ""]
    for _key, title, _icon, about, articles in TOPICS:
        out += [f"## {title}", "", f"{about}.", ""]
        for heading, steps in articles:
            out += [f"### {heading}", ""] + [f"{n}. {text}" for n, (text, _) in enumerate(steps, 1)] + [""]
    return "\n".join(out)
