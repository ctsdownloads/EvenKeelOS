#!/usr/bin/python3
"""Build check: every test in System Tools' Test automatic rollback list reaches the piece that breaks that thing.

The list in evenkeel-os-tools must name the same tests, in the same order, as evenkeel-os-tools-admin accepts, each
under its own name; each test's breaking piece must be in the image; and evenkeel-os-test-fail must fail only for its
own test.
"""
import ast
import subprocess
import sys
import tempfile
from pathlib import Path

GB = "/usr/lib/greenboot/check/required.d"
# test: (the name shown in System Tools, file that breaks it, text that file must contain)
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
}


def assigned(path, name):
    for node in ast.parse(Path(path).read_text()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    sys.exit(f"ERROR: {name} not found in {path}")


def main():
    tests = assigned("/usr/bin/evenkeel-os-tools", "ROLLBACK_TESTS")
    listed = [kind for kind, _, _ in tests]
    accepted = list(assigned("/usr/libexec/evenkeel-os-tools-admin", "TEST_KINDS"))
    if listed != accepted:
        sys.exit(f"ERROR: the System Tools list {listed} doesn't match what the admin helper accepts {accepted}")
    if sorted(listed) != sorted(PIECES):
        sys.exit(f"ERROR: tests without a breaking piece checked here: {sorted(set(listed) ^ set(PIECES))}")
    for kind, name, _ in tests:
        if name != PIECES[kind][0]:
            sys.exit(f"ERROR: test {kind} is shown as {name!r}, not {PIECES[kind][0]!r}")
    for kind, (_, path, text) in PIECES.items():
        if text not in Path(path).read_text():
            sys.exit(f"ERROR: test {kind}: {path} doesn't contain {text!r}")
    for unit in ("evenkeel-os-test-stuck.service", "evenkeel-os-test-freeze.service"):
        if subprocess.run(["systemctl", "is-enabled", "-q", unit]).returncode != 0:
            sys.exit(f"ERROR: {unit} isn't enabled")
    # evenkeel-os-test-fail, run against a made-up kernel command line for each test
    script = Path("/usr/libexec/evenkeel-os-test-fail").read_text()
    with tempfile.TemporaryDirectory() as d:
        for running in [None, *PIECES]:
            cmdline = Path(d, "cmdline")
            cmdline.write_text("root=x rhgb quiet" + (f" evenkeel_os.test_rollback={running}" if running else ""))
            for kind in ("no-login-screen", "no-networking", "login-loop"):
                rc = subprocess.run(["bash", "-c", script.replace("/proc/cmdline", str(cmdline)), "x", kind],
                                    capture_output=True).returncode
                want = 3 if kind == running else 0
                if rc != want:
                    sys.exit(f"ERROR: evenkeel-os-test-fail {kind} exits {rc} while running {running}, not {want}")
    print(f"Rollback tests: {len(listed)} listed, each reaches its breaking piece; test-fail exits 3 only for its own")


if __name__ == "__main__":
    main()
