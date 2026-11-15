"""Hardware rules from box packages."""
import os
import re
import subprocess
from pathlib import Path
from evenkeel_os_packages import boxes, reading



def box_rules(box):
    """Hardware rule files in a box, by file name."""
    r = subprocess.run(boxes.in_box(box, "sh", "-c", "ls /usr/lib/udev/rules.d /etc/udev/rules.d 2>/dev/null"),
                       capture_output=True, text=True)
    return {l.strip() for l in r.stdout.splitlines() if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*\.rules", l.strip())}


def new_box_rules(box, before, info):
    """Hardware rules from packages the install pulled in that the system lacks."""
    host = {p.name for d in ("/usr/lib/udev/rules.d", "/etc/udev/rules.d") for p in Path(d).glob("*.rules")}
    own = {os.path.basename(p) for p in info["safe_rules"]}
    for name in sorted(box_rules(box) - before - host - own):
        r = subprocess.run(boxes.in_box(box, "sh", "-c", f"cat /etc/udev/rules.d/{name} 2>/dev/null || "
                                  f"cat /usr/lib/udev/rules.d/{name}"), capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.strip():
            continue
        if reading.rule_runs_program(r.stdout):
            if "a hardware rule that runs a program" not in info["notes"]:
                info["notes"].append("a hardware rule that runs a program")
        else:
            info["safe_rules"]["/usr/lib/udev/rules.d/" + name] = r.stdout
