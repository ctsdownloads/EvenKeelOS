#!/usr/bin/python3 -I
"""Fails on a comment or docstring over one line, an error dropped silently, or a forbidden word, in any file."""
import ast
import io
import re
import subprocess
import sys
import tokenize

SELF = "build_files/check-rules.py"
WORDS = ["-e", "co-authored-by", "-e", "easy ?speak"]
HEREDOC = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_]\w*)\1")


def tracked():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.split()
    return [p for p in out if not p.startswith("po/")]


def kind(path, text):
    first = text.split("\n", 1)[0]
    if path.endswith(".py") or first.startswith("#!") and "python" in first:
        return "python"
    if path.endswith(".sh") or first.startswith("#!") and re.search(r"\b(ba)?sh\b", first) or path == "Justfile":
        return "shell"
    if path.endswith((".yml", ".yaml")):
        return "yaml"
    if path.endswith((".rules", ".js")):
        return "js"
    if path.endswith((".conf", ".txt", ".service", ".timer", ".path", ".preset")):
        return "config"
    return None


def comment_rows(kind_, text):
    if kind_ == "python":
        rows = set()
        for t in tokenize.generate_tokens(io.StringIO(text).readline):
            if t.type == tokenize.COMMENT and not t.line[:t.start[1]].strip() and not t.string.startswith("#!"):
                rows.add(t.start[0])
        return rows
    mark, end, rows = ("//" if kind_ == "js" else "#"), None, set()
    for i, line in enumerate(text.split("\n"), 1):
        if end is not None:
            end = None if line.strip() == end else end
        elif line.strip().startswith(mark) and not line.startswith(("#!", "# shellcheck ")):
            rows.add(i)
        elif kind_ == "shell" and (m := HEREDOC.search(line)):
            end = m.group(2)
    return rows


def python_problems(path, text):
    tree = ast.parse(text, path)
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            help_text = isinstance(n, ast.Module) and "__doc__" in text
            if "\n" in (ast.get_docstring(n, clean=False) or "").strip() and not help_text:
                yield getattr(n, "lineno", 1), "docstring over one line"
        if isinstance(n, ast.ExceptHandler) and all(
                isinstance(s, ast.Pass) or isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
                for s in n.body):
            yield n.lineno, "except that does nothing: handle the error or let it show"
        if isinstance(n, ast.ImportFrom) and n.module == "contextlib" and any(a.name == "suppress" for a in n.names) \
                or isinstance(n, ast.Attribute) and n.attr == "suppress" and getattr(n.value, "id", "") == "contextlib":
            yield n.lineno, "contextlib.suppress drops errors silently"


problems = []
for path in tracked():
    try:
        text = open(path, encoding="utf-8").read()
    except UnicodeDecodeError:
        continue
    k = kind(path, text)
    if k:
        rows = comment_rows(k, text)
        problems += [(path, i, "comment over one line") for i in sorted(rows) if i + 1 in rows and i - 1 not in rows]
    if k == "python":
        problems += [(path, i, why) for i, why in python_problems(path, text)]
found = subprocess.run(["git", "grep", "-nIiE", *WORDS, "--", ".", f":!{SELF}", ":!po"], capture_output=True, text=True)
problems += [(line.split(":", 2)[0], line.split(":", 2)[1], "forbidden word") for line in found.stdout.splitlines()]
for path, line, why in problems:
    print(f"{path}:{line}: {why}")
print(f"{len(problems)} rule problems" if problems else "Code rules: all followed.")
sys.exit(1 if problems else 0)
