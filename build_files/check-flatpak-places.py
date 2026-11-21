#!/usr/bin/python3 -I
"""Build test: every flatpak install and uninstall in our tools names the system or the person's own apps.

Usage: check-flatpak-places.py DIR... (each file in each DIR: Python by its AST, shell scripts line by line)
"""
import ast
import re
import sys
from pathlib import Path

PLACES = {"--system", "--user"}
ACTIONS = {"install", "uninstall"}


def words_of(node):
    """The string words of a command list, counting "--user" if ... else "--system" written in it."""
    out = []
    for e in node.elts:
        if isinstance(e, ast.Constant) and isinstance(e.value, str):
            out.append(e.value)
        elif isinstance(e, ast.IfExp) and all(isinstance(b, ast.Constant) and b.value in PLACES
                                              for b in (e.body, e.orelse)):
            out.append("--system")
    return out


def python_problems(path, text):
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, (ast.List, ast.Tuple)) and node.elts:
            words = words_of(node)
            if words and words[0].endswith("flatpak") and ACTIONS & set(words) and not PLACES & set(words):
                yield f"{path}:{node.lineno}"


def shell_problems(path, text):
    for n, line in enumerate(text.splitlines(), 1):
        if re.search(r"\bflatpak\b.*\b(un)?install\b", line) and not PLACES & set(line.split()):
            yield f"{path}:{n}"


bad = []
for folder in sys.argv[1:]:
    for path in sorted(p for p in Path(folder).iterdir() if p.is_file() and "evenkeel" in p.name or
                       p.suffix == ".py" and p.parent.name == "evenkeel_os_packages"):
        text = path.read_text(errors="replace")
        if "flatpak" not in text:
            continue
        python = path.suffix == ".py" or text.startswith(("#!/usr/bin/python", "#!/usr/bin/env python"))
        bad += python_problems(path, text) if python else shell_problems(path, text)
if bad:
    sys.exit("ERROR: flatpak install or uninstall without --system or --user: " + ", ".join(bad))
print("Every flatpak install and uninstall names where it goes")
