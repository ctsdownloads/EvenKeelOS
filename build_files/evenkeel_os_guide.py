"""New to Linux: a short guide for people coming from Windows, shown in System Tools and in docs/new-to-linux.md.

Each section is (title, icon, lines); a line is (text, System Tools page it opens, or "").
"""

TITLE = "New to Linux?"
INTRO = ("Most of what you did on Windows works the same way here. This is where things are, and what's different. "
         "It's in System Tools, Get help, any time.")

SECTIONS = [
    ("Where things are", "system-search-symbolic", [
        ("Start menu: with the Windows-style layout, the sailboat button at the bottom left. With the standard layout, "
         "press the Windows key, or open Show Apps in the dock.", "yours"),
        ("Control Panel: Settings for Wi-Fi, screens, sound, printers and accounts. System Tools for updates, apps "
         "and fixes.", ""),
        ("File Explorer: Files.", ""),
        ("Task Manager: Resources. Find it in the start menu, or Show Apps.", ""),
        ("Word, Excel and PowerPoint: LibreOffice Writer, Calc and Impress. They open and save Office files.", ""),
        ("Notepad: Text Editor. Photos: Image Viewer. Videos: Celluloid. Music: Lollypop. PDFs: Papers.", ""),
    ]),
    ("Getting apps", "system-software-install-symbolic", [
        ("Most apps come from Bazaar, the app store. Apps from there update on their own.", "apps"),
        ("A Windows program (.exe or .msi) can't run here. Open it anyway: System Tools tells you its Linux version, "
         "or a replacement when there is one, and installs it.", "apps"),
        ("An app that comes as a .rpm or .deb file installs when you open the file.", "apps"),
        ("Remove apps in System Tools, Apps.", "apps"),
    ]),
    ("Updates", "software-update-available-symbolic", [
        ("Updates install on their own, for the system and your apps. System updates start at your next "
         "restart.", "updates"),
        ("If an update stops the computer starting properly, it goes back to the version before by itself and tells "
         "you.", ""),
        ("If something stopped working after an update, Undo the last update goes back one version. Your files and "
         "apps aren't touched.", "updates"),
    ]),
    ("Your files", "folder-symbolic", [
        ("Your Documents, Downloads, Pictures, Music and Videos folders are in your home folder, in Files.", ""),
        ("USB drives show in the left side of Files. Eject them there before you unplug them.", ""),
        ("To open your folders from other computers at home, use Shared folders.", "sharing"),
    ]),
    ("Networks and printers", "network-wireless-symbolic", [
        ("Every network is Home, Work or a Public place. A new one is a Public place, where nothing can reach your "
         "computer.", "network"),
        ("Printers: Settings, Printers. Many printers are found and work with no driver to install. If your "
         "printer's maker gives you a driver file, open it like any app file.", ""),
    ]),
    ("What works differently", "dialog-information-symbolic", [
        ("Copy and paste, right-click and the window buttons work as on Windows. Alt+Tab switches between apps.",
         ""),
        ("Print Screen opens the screenshot tool, to pick the whole screen, a window or an area.", ""),
        ("The system itself is read-only: apps and mistakes can't change it. Each update replaces it whole.", ""),
        ("If you want a virus scanner, ClamUI is in Bazaar.", ""),
    ]),
    ("Getting help", "help-about-symbolic", [
        ("Something not right? Save problem details makes one file of recent errors to send to your helper.", "help"),
    ]),
]


def markdown():
    """The guide as docs/new-to-linux.md."""
    out = [f"# {TITLE}", "", INTRO, ""]
    for title, _, lines in SECTIONS:
        out += [f"## {title}", ""] + [f"- {text}" for text, _ in lines] + [""]
    return "\n".join(out)
