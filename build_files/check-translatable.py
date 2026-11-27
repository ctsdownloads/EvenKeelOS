#!/usr/bin/python3
"""Fails when words that go on screen are written straight into a window instead of through _()."""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYWORDS = {"label", "title", "subtitle", "heading", "body", "description", "tooltip_text", "placeholder_text",
            "text", "secondary_text", "ok", "cancel", "extra", "rest", "button_label"}
METHODS = {"set_label", "set_title", "set_subtitle", "set_text", "set_markup", "set_tooltip_text",
           "set_placeholder_text", "set_description", "set_heading", "set_body", "set_button_label",
           "say", "ask", "notify", "offer_restart", "choose", "add_toast", "add_response", "Toast", "toast"}
WORDS = re.compile(r"[A-Za-z]{2,}[ .,:?!'…]")      # a word followed by a space or punctuation: a sentence
SHELL = re.compile(r"""(notify-send|zenity|evenkeel-os-dialog|--text=|--title=)[^#\n]*?["'][A-Z][a-z]+[ .,]""")


def words(node):
    """True for a plain string or f-string with words in it."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return bool(WORDS.search(node.value + " "))
    if isinstance(node, ast.JoinedStr):
        return any(words(v) for v in node.values)
    if isinstance(node, ast.BinOp):
        return words(node.left) or words(node.right)
    return False


SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp,
          ast.GeneratorExp)


def own(scope):
    """The nodes that belong to a function, lambda or comprehension, not to the ones inside it."""
    todo = list(ast.iter_child_nodes(scope))
    while todo:
        node = todo.pop()
        yield node
        if not isinstance(node, SCOPES + (ast.ClassDef,)):
            todo += ast.iter_child_nodes(node)


def binds(scope):
    return any(isinstance(n, ast.Name) and n.id == "_" and isinstance(n.ctx, ast.Store) or
               isinstance(n, ast.arg) and n.arg == "_" for n in own(scope))


def python(path):
    out = []
    tree = ast.parse(path.read_text(), str(path))
    parent = {c: n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
    for scope in (n for n in ast.walk(tree) if isinstance(n, SCOPES)):
        if not any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_" for n in own(scope)):
            continue
        s = scope
        while s is not None and not (isinstance(s, SCOPES) and binds(s)):
            s = parent.get(s)
        if s is not None:
            out.append(f"{path.relative_to(ROOT)}:{scope.lineno}: a variable named _ hides the translation")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "attr", getattr(node.func, "id", ""))
        args = [k.value for k in node.keywords if k.arg in KEYWORDS]
        if name in METHODS:
            args += node.args[1:2] if name == "add_response" else node.args[:1]
        out += [f"{path.relative_to(ROOT)}:{a.lineno}: text on screen without _() or gettext"
                for a in args if words(a)]
    return out


def shell(path):
    return [f"{path.relative_to(ROOT)}:{n}: text on screen without _() or gettext"
            for n, line in enumerate(path.read_text().splitlines(), 1)
            if SHELL.search(line) and "gettext" not in line]


def main():
    found = []
    for path in sorted(p for p in ROOT.glob("build_files/**/*") if p.is_file()) + \
            sorted(p for p in ROOT.glob("iso/src/**/*") if p.is_file()):
        if path.name.startswith(("check-", "make-")) or path.suffix not in ("", ".py", ".sh"):
            continue
        first = path.read_text(errors="replace").split("\n", 1)[0]
        if path.suffix == ".py" or "python" in first:
            found += python(path)
        elif "bash" in first or first.endswith("/sh") or path.suffix == ".sh":
            found += shell(path)
    for f in found:
        print(f)
    if found:
        sys.exit(f"ERROR: {len(found)} places where screen text can't be translated")
    print("Every line of screen text can be translated.")


main()
