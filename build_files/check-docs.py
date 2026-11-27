#!/usr/bin/python3 -I
"""Build test: the README's contents list and every link in the README and guides are right."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []


def slug(text):
    """GitHub's anchor for a heading."""
    text = re.sub(r"[`*_]", "", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def read(path):
    """A page's lines, its heading anchors, and its headings as (level, words, anchor)."""
    lines = (ROOT / path).read_text().splitlines()
    headings, anchors, seen, fence = [], set(), {}, False
    for line in lines:
        if line.startswith("```"):
            fence = not fence
        if fence:
            continue
        m = re.match(r"^(#{1,3}) (.+?)\s*$", line)
        if m:
            text = m.group(2)
            a = slug(text)
            n = seen.get(a, 0)
            seen[a] = n + 1
            a = a if n == 0 else f"{a}-{n}"
            anchors.add(a)
            if text != "Contents" and len(m.group(1)) > 1:
                headings.append((len(m.group(1)), text, a))
    return lines, anchors, headings


PAGES = ["README.md"] + sorted(str(p.relative_to(ROOT)) for p in (ROOT / "docs").glob("*.md"))
pages = {p: read(p) for p in PAGES}
readme, anchors, headings = pages["README.md"]

try:
    first = readme.index("<!-- contents -->")
    last = readme.index("<!-- /contents -->")
except ValueError:
    errors.append("README.md has no table of contents between <!-- contents --> and <!-- /contents -->")
    first = last = 0
listed = []
for line in readme[first + 1:last]:
    if not line.strip():
        continue
    m = re.match(r"^( *)- \[(.+)\]\(#([^)]+)\)$", line)
    if not m:
        errors.append(f"README.md table of contents: not a contents line: {line!r}")
        continue
    listed.append((2 if m.group(1) == "" else 3, m.group(2), m.group(3)))

for i in range(max(len(headings), len(listed))):
    h = headings[i] if i < len(headings) else None
    t = listed[i] if i < len(listed) else None
    if h != t:
        want = f"{'  ' * (h[0] - 2)}- [{h[1]}](#{h[2]})" if h else "(nothing more)"
        got = f"{'  ' * (t[0] - 2)}- [{t[1]}](#{t[2]})" if t else "(nothing)"
        errors.append(f"README.md table of contents, line {i + 1}: should be {want}, is {got}")
        break

# ---------------------------------------------------------------- every link, in every page
for page, (lines, page_anchors, _h) in pages.items():
    here = Path(page).parent
    for line in lines:
        for target in re.findall(r"\]\(([^)]+)\)", line):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            path, _, a = target.partition("#")
            if not path:                                        # "#name": a section of this same page
                if a not in page_anchors:
                    errors.append(f"{page} links to a section that is not in it: #{a}")
                continue
            other = (ROOT / here / path).resolve()
            try:
                name = str(other.relative_to(ROOT))
            except ValueError:
                errors.append(f"{page} links outside the repository: {target}")
                continue
            if not other.exists():
                errors.append(f"{page} links to a file that is not there: {target}")
            elif a and name in pages and a not in pages[name][1]:
                errors.append(f"{page} links to a section that is not in {name}: #{a}")

# ---------------------------------------------------------------- no guide left unlinked
linked = {str((Path("README.md").parent / t.partition("#")[0]).as_posix())
          for line in readme for t in re.findall(r"\]\(([^)]+)\)", line) if t.partition("#")[0]}
for page in PAGES[1:]:
    if page not in linked:
        errors.append(f"{page} is not linked from README.md, so nobody will find it")

# ---------------------------------------------------------------- the guide matches Wheelhouse's own text
sys.path.insert(0, str(ROOT / "build_files"))
import evenkeel_os_guide  # noqa: E402
if (ROOT / "docs" / "guide.md").read_text() != evenkeel_os_guide.markdown():
    errors.append("docs/guide.md isn't the guide Wheelhouse shows: write it from "
                  "build_files/evenkeel_os_guide.py")

if errors:
    print("\n".join("ERROR: " + e for e in errors))
    sys.exit(1)
print(f"README: {len(headings)} sections, all listed and linked. "
      f"Guides: {len(PAGES) - 1} in docs/, every link good.")
