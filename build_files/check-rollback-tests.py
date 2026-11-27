#!/usr/bin/python3
"""Build check: every test in Wheelhouse's Test automatic rollback list reaches the piece that breaks that thing."""
import ast
import re
import subprocess
import sys
import tempfile
from pathlib import Path

GB = "/usr/lib/greenboot/check/required.d"
HEALTH = "/usr/lib/evenkeel-os/evenkeel_os_health.py"
# test: (the name shown in Wheelhouse, file that breaks it, text that file must contain)
PIECES = {
    "quick": ("Quick test", f"{GB}/00-evenkeel-os-test-quick.sh", "evenkeel_os.test_rollback=quick"),
    "no-login-screen": ("No login screen", "/usr/lib/systemd/system/gdm.service.d/50-evenkeel-os-test.conf",
                        "evenkeel-os-test-fail no-login-screen"),
    "no-networking": ("No networking", "/usr/lib/systemd/system/NetworkManager.service.d/50-evenkeel-os-test.conf",
                      "evenkeel-os-test-fail no-networking"),
    "stuck": ("Stuck while starting", "/usr/lib/systemd/system/evenkeel-os-test-stuck.service",
              "ConditionKernelCommandLine=evenkeel_os.test_rollback=stuck"),
    "login-loop": ("Login loop", "/usr/lib/systemd/user/org.gnome.Shell@user.service.d/50-evenkeel-os-test.conf",
                   "evenkeel-os-test-fail login-loop"),
    "freeze": ("Freeze", "/usr/lib/systemd/system/evenkeel-os-test-freeze.service",
               "ConditionKernelCommandLine=evenkeel_os.test_rollback=freeze"),
    # Driver tests: the admin helper blocks the driver this computer uses (evenkeel_os_health.test_args).
    "sound": ("Sound driver blocked", HEALTH, '"sound": (sound, "sound:")'),
    "wifi": ("Wi-Fi driver blocked", HEALTH, '"wifi": (networks, "wifi:")'),
    "bluetooth": ("Bluetooth driver blocked", HEALTH, '"bluetooth": (bluetooth, "bluetooth:")'),
    "graphics": ("Graphics driver blocked", HEALTH, '"graphics": (graphics, "graphics:")'),
    "printing": ("Printing service off", "/usr/lib/systemd/system/cups.service.d/50-evenkeel-os-test.conf",
                 "evenkeel-os-test-fail printing"),
    "firewall": ("Firewall off", "/usr/lib/systemd/system/firewalld.service.d/50-evenkeel-os-test.conf",
                 "evenkeel-os-test-fail firewall"),
    "update-program": ("Update program broken", "/usr/lib/systemd/system/evenkeel-os-test-update.service",
                       "ConditionKernelCommandLine=evenkeel_os.test_rollback=update-program"),
    "service": ("A system service fails", "/usr/lib/systemd/system/ModemManager.service.d/50-evenkeel-os-test.conf",
                "evenkeel-os-test-fail service"),
}


class Words(ast.NodeTransformer):
    """N_("text") is marked for translation, but is just the text."""

    def visit_Call(self, node):
        if getattr(node.func, "id", None) == "N_" and len(node.args) == 1:
            return node.args[0]
        return self.generic_visit(node)


def assigned(path, name):
    for node in ast.parse(Path(path).read_text()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(Words().visit(node.value))
    sys.exit(f"ERROR: {name} not found in {path}")


def later_checks():
    # greenboot runs green.d scripts with noclobber: a plain > can't replace the note of an earlier rollback.
    rolled = Path("/usr/lib/greenboot/green.d/90-evenkeel-os-rolled-back.sh").read_text()
    if re.search(r'(?<!>)>"\$(note|pause)"', rolled):
        sys.exit("ERROR: 90-evenkeel-os-rolled-back.sh writes its note with > instead of >|, so only the first "
                 "rollback ever gets a message")
    with tempfile.TemporaryDirectory() as d:
        old = Path(d, "note")
        old.write_text("test 1\n")
        rc = subprocess.run(["bash", "-C", "-c", f'echo "test 2" >|"{old}"']).returncode
        if rc != 0 or old.read_text() != "test 2\n":
            sys.exit("ERROR: >| doesn't replace a file under noclobber")
    # greenboot must never wait for the login screen: the Stuck test holds the login screen forever.
    for unit in Path("/usr/lib/systemd/system").glob("evenkeel-os-*.service"):
        for line in unit.read_text().splitlines():
            if line.startswith("Before=") and "greenboot-healthcheck.service" in line.split("=", 1)[1].split():
                sys.exit(f"ERROR: {unit} makes greenboot wait for it, so a stuck start never rolls back")
    gb = Path("/usr/lib/systemd/system/greenboot-healthcheck.service").read_text()
    if re.search(r"^After=.*\b(display-manager|gdm)\.service", gb, re.M):
        sys.exit("ERROR: greenboot-healthcheck waits for the login screen, so a stuck start never rolls back")
    # The login-loop check counts logins from these logind records; a login that ends in under a second counts.
    logind = Path("/usr/lib/systemd/systemd-logind").read_bytes()
    desktop = Path(f"{GB}/30-evenkeel-os-desktop.sh").read_text()
    for need in (b"MESSAGE_ID=8d45620c1a4348dbb17410da57c60c66", b"MESSAGE_ID=3354939424b4456d9802ca8333ed424a",
                 b"CLASS=%s", b"TYPE=%s", b"SESSION_ID=%s", b"USER_ID=%s"):
        if need not in logind:
            sys.exit(f"ERROR: systemd-logind no longer logs {need.decode()}; update 30-evenkeel-os-desktop.sh")
        if need.startswith(b"MESSAGE_ID") and need.split(b"=")[1].decode() not in desktop:
            sys.exit(f"ERROR: 30-evenkeel-os-desktop.sh doesn't read the logind record {need.decode()}")


def main():
    tests = assigned("/usr/bin/evenkeel-os-tools", "ROLLBACK_TESTS")
    listed = [kind for kind, _, _ in tests]
    accepted = list(assigned("/usr/libexec/evenkeel-os-tools-admin", "TEST_KINDS"))
    if listed != accepted:
        sys.exit(f"ERROR: the Wheelhouse list {listed} doesn't match what the admin helper accepts {accepted}")
    if sorted(listed) != sorted(PIECES):
        sys.exit(f"ERROR: tests without a breaking piece checked here: {sorted(set(listed) ^ set(PIECES))}")
    for kind, name, _ in tests:
        if name != PIECES[kind][0]:
            sys.exit(f"ERROR: test {kind} is shown as {name!r}, not {PIECES[kind][0]!r}")
    for kind, (_, path, text) in PIECES.items():
        if text not in Path(path).read_text():
            sys.exit(f"ERROR: test {kind}: {path} doesn't contain {text!r}")
    # Switched on from /usr, which systemctl is-enabled doesn't read: deleting /etc can't switch them off.
    for unit in ("evenkeel-os-test-stuck.service", "evenkeel-os-test-freeze.service",
                 "evenkeel-os-test-update.service"):
        if not Path(f"/usr/lib/systemd/system/multi-user.target.wants/{unit}").is_file():
            sys.exit(f"ERROR: {unit} isn't switched on from /usr/lib/systemd/system/multi-user.target.wants")
    # Every test has its short line for the list.
    short = assigned("/usr/bin/evenkeel-os-tools", "TEST_SHORT")
    if set(short) != set(listed) | {"settings"}:
        sys.exit(f"ERROR: the test list's short lines {sorted(short)} don't match the tests {sorted(listed)}")
    # Every setting the settings test deletes has a plain-word name in its message.
    names = set(assigned("/usr/bin/evenkeel-os-tools", "SETTINGS_NAMES"))
    deletes = {f"/etc/{n}" for n in assigned("/usr/libexec/evenkeel-os-settings", "TEST_DELETE")}
    if deletes - names:
        sys.exit(f"ERROR: the settings test deletes {sorted(deletes - names)}, which have no plain-word name")
    # evenkeel-os-test-fail, run against a made-up kernel command line for each test
    script = Path("/usr/libexec/evenkeel-os-test-fail").read_text()
    with tempfile.TemporaryDirectory() as d:
        for running in [None, *PIECES]:
            cmdline = Path(d, "cmdline")
            cmdline.write_text("root=x rhgb quiet" + (f" evenkeel_os.test_rollback={running}" if running else ""))
            for kind in ("no-login-screen", "no-networking", "login-loop", "printing", "firewall", "service"):
                rc = subprocess.run(["bash", "-c", script.replace("/proc/cmdline", str(cmdline)), "x", kind],
                                    capture_output=True).returncode
                want = 3 if kind == running else 0
                if rc != want:
                    sys.exit(f"ERROR: evenkeel-os-test-fail {kind} exits {rc} while running {running}, not {want}")
    # Every real service the "A system service fails" test may break fails with it.
    for unit in assigned(HEALTH, "TEST_SERVICES"):
        conf = Path(f"/usr/lib/systemd/system/{unit}.d/50-evenkeel-os-test.conf")
        if "evenkeel-os-test-fail service" not in (conf.read_text() if conf.exists() else ""):
            sys.exit(f"ERROR: {unit} has no test drop-in for the \"A system service fails\" test")
    # The tests that need a login say so when picked.
    after = set(assigned("/usr/bin/evenkeel-os-tools", "AFTER_LOGIN_TESTS"))
    if after != set(PIECES) - {"quick", "no-login-screen", "no-networking", "stuck", "login-loop", "freeze"}:
        sys.exit(f"ERROR: the tests that wait for a login {sorted(after)} don't match the tests added for the trial "
                 "check")
    later_checks()
    print(f"Rollback tests: {len(listed)} listed, each reaches its breaking piece; test-fail exits 3 only for its own; "
          "note, start order and login records OK")


if __name__ == "__main__":
    main()
