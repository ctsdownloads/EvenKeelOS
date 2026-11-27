#!/usr/bin/python3 -I
"""Build check: certificate alerts catch expired, soon-expiring and removed certificates, and nothing else."""
import datetime
import json
import os
import sys
import tempfile
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding

sys.path.insert(0, "/usr/lib/evenkeel-os")
from evenkeel_os_ui import load_program  # noqa: E402

HELPER = Path(sys.argv[1] if len(sys.argv) > 1 else "/usr/libexec/evenkeel-os-certs")


def die(msg):
    sys.exit(f"ERROR: certificate alerts: {msg}")


def make(name, days_left):
    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.datetime.now(datetime.timezone.utc)
    subject = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, name)])
    return (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(days=400))
            .not_valid_after(now + datetime.timedelta(days=days_left)).sign(key, hashes.SHA256()))


def kinds(m):
    return {(a["name"], a["kind"], a["added"]) for a in json.loads(m.ALERTS.read_text())}


def read_removed(m):
    """The removed certificate's alert, marked as read; its fingerprint."""
    gone = next(a["fingerprint"] for a in json.loads(m.ALERTS.read_text()) if a["kind"] == "removed")
    m.seen(gone)
    return gone


def main():
    m = load_program(HELPER, "certs")
    real = m.TRUSTED
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        m.TRUSTED, m.BUILT_IN, m.ADDED, m.STATE = d / "trusted.pem", d / "built-in.pem", d / "anchors", d / "state"
        m.ALERTS, m.KNOWN, m.NOTIFIED = m.STATE / "a.json", m.STATE / "k.json", m.STATE / "n.json"
        m.ADDED.mkdir()
        fine, old, soon = make("Built-in fine", 900), make("Built-in expired", -3), make("Built-in soon", 10)
        mine_old, mine_ok, mine_gone = make("Mine expired", -1), make("Mine fine", 500), make("Mine removed", 500)
        builtin = [fine, old, soon]
        m.BUILT_IN.write_bytes(b"".join(c.public_bytes(Encoding.PEM) for c in builtin))
        m.TRUSTED.write_bytes(b"".join(c.public_bytes(Encoding.PEM) for c in builtin + [mine_old, mine_ok]))
        (m.ADDED / "old.pem").write_bytes(mine_old.public_bytes(Encoding.PEM))
        (m.ADDED / "ok.cer").write_bytes(mine_ok.public_bytes(Encoding.DER))
        (m.ADDED / "gone.pem").write_bytes(mine_gone.public_bytes(Encoding.PEM))
        os.symlink("/etc/shadow", m.ADDED / "link.pem")
        m.check(False)
        want = {("Built-in expired", "expired", False), ("Built-in soon", "expiring", False),
                ("Mine expired", "expired", True)}
        if kinds(m) != want:
            die(f"alerts {sorted(kinds(m))}, not {sorted(want)}")
        (m.ADDED / "gone.pem").unlink()
        m.check(False)
        if kinds(m) != want | {("Mine removed", "removed", True)}:
            die(f"a removed certificate isn't called out: {sorted(kinds(m))}")
        m.check(False)
        if ("Mine removed", "removed", True) not in kinds(m):
            die("a removed certificate's alert goes away by itself before it's read")
        gone = read_removed(m)
        m.check(False)
        if kinds(m) != want:
            die("a removed certificate's alert stays after it was read")
        if m.main(["", "seen", "../../x"]) != 2 or m.main(["", "trusted", "a" * 64 + "\n"]) != 2:
            die("a bad fingerprint isn't refused")
        fp = {a["name"]: a["fingerprint"] for a in json.loads(m.ALERTS.read_text())}
        if m.trusted(fp["Mine expired"]) != 0:
            die("an added certificate isn't reported as trusted")
        # A file holding two certificates is counted, so removing it isn't offered for one of them.
        two = make("Two A", -1).public_bytes(Encoding.PEM) + make("Two B", 300).public_bytes(Encoding.PEM)
        (m.ADDED / "two.pem").write_bytes(two)
        m.check(False)
        both = [a for a in json.loads(m.ALERTS.read_text()) if a["name"] == "Two A"]
        if not both or both[0].get("in_file") != 2:
            die("a file with two certificates isn't counted as two")
        (m.ADDED / "old.pem").unlink()
        m.check(False)
        gone = read_removed(m)
        m.TRUSTED.write_bytes(fine.public_bytes(Encoding.PEM))
        if m.trusted(gone) != 1:
            die("a removed certificate is still reported as trusted")
        # A notification that isn't shown is tried again at the next check.
        for rc, want_saved in ((1, False), (0, True)):
            fake = d / f"notify{rc}"
            fake.write_text(f"#!/bin/sh\nexit {rc}\n")
            fake.chmod(0o755)
            m.NOTIFY = str(fake)
            m.NOTIFIED.unlink(missing_ok=True)
            m.check(True)
            if m.NOTIFIED.exists() != want_saved:
                die(f"a notification that exits {rc} is {'not ' if want_saved else ''}marked as shown")
    m = load_program(HELPER, "certs")
    with tempfile.TemporaryDirectory() as d:
        m.STATE = Path(d)
        m.ALERTS, m.KNOWN, m.NOTIFIED = m.STATE / "a.json", m.STATE / "k.json", m.STATE / "n.json"
        m.BUILT_IN = real
        m.check(False)
        alerts = json.loads(m.ALERTS.read_text())
        if not m.certs(m.read(real)):
            die(f"no certificates read from {real}")
        # Not a build failure: Fedora's list is Fedora's; people with this version see the alert, as they should.
        for a in alerts:
            print(f"WARNING: this image trusts a certificate that {a['kind']}: {a['name']} ({a['ends'][:10]})")
    print(f"Certificate alerts: expired and soon-expiring (built-in and added) and removed ones are called out, links "
          f"aren't followed, a read alert goes away; this image's own list has {len(alerts)} today")


if __name__ == "__main__":
    main()
