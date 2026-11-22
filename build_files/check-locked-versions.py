"""Build check: every package not signed by Fedora's key is on the locked list, at exactly that version.

Usage: check-locked-versions.py locked-versions.txt FEDORA-KEY-FILE [rpm options, such as --dbpath DIR]
"""
import os
import subprocess
import sys
import tempfile


def key_id(key_file):
    """The 16-character key ID rpm shows for packages signed by this key."""
    with tempfile.TemporaryDirectory() as home:
        out = subprocess.run(["gpg", "--batch", "--show-keys", "--with-colons", key_file], capture_output=True,
                             text=True, check=True, env={**os.environ, "GNUPGHOME": home}).stdout
    fingerprints = [line.split(":")[9] for line in out.splitlines() if line.startswith("fpr:")]
    if len(fingerprints) != 1 or len(fingerprints[0]) != 40:
        sys.exit(f"ERROR: {key_file} is not one signing key")
    return fingerprints[0][-16:].lower()


locked = {}
with open(sys.argv[1], encoding="utf-8") as f:
    for line in f:
        fields = line.split()
        if fields and fields[0] == "copr":
            locked[fields[2]] = fields[3]
fedora = key_id(sys.argv[2])

signature = "%|RSAHEADER?{%{RSAHEADER:pgpsig}}:{%|DSAHEADER?{%{DSAHEADER:pgpsig}}:{unsigned}|}|"
query = ["rpm", "-qa", "--qf", rf"%{{NAME}}\t%{{VERSION}}-%{{RELEASE}}\t{signature}\n", *sys.argv[3:]]
rows = subprocess.run(query, capture_output=True, text=True, check=True).stdout.splitlines()
installed, problems = {}, []
for row in rows:
    name, version, signed = row.split("\t")
    if name == "gpg-pubkey" or signed.endswith(f"Key ID {fedora}"):
        continue
    installed[name] = version
    if name not in locked:
        problems.append(f"{name} {version} (signature: {signed}) is not on the locked list")
    elif version != locked[name]:
        problems.append(f"{name} is {version}, but the locked version is {locked[name]}")
problems += [f"{name} {version} is locked but not installed" for name, version in locked.items()
             if name not in installed]
if not locked or problems:
    print("ERROR: the outside packages do not match locked-versions.txt", *problems, sep="\n  ")
    sys.exit(1)
print(f"All {len(locked)} packages not signed by Fedora are at their locked versions")
