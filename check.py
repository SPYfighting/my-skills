#!/usr/bin/env python3
"""Check every skill in this repository. Nothing here changes when a skill is added.

A skill is any top-level directory holding a SKILL.md. For each one this runs
whatever verification it already ships, found by convention:

    <skill>/tests/            pytest, falling back to unittest discovery
    <skill>/scripts/*.py      import-time syntax check
    <skill>/scripts/*.js      node --check

It also checks that the SKILL.md frontmatter parses and that its `name` matches
the directory, which is what makes the skill discoverable once installed.

A skill with nothing runnable is reported as unverified rather than passing
silently: knowing which skills have no test is more useful than a green tick
that means nothing.

    python check.py
    python check.py novel-writing

Standard library only. Exit code 0 when nothing failed.
"""

import argparse
import ast
import glob
import os
import re
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.abspath(__file__))


def find_skills():
    for name in sorted(os.listdir(REPO)):
        path = os.path.join(REPO, name)
        if name.startswith(".") or not os.path.isdir(path):
            continue
        if os.path.isfile(os.path.join(path, "SKILL.md")):
            yield name, path


def check_frontmatter(name, path, problems):
    text = open(os.path.join(path, "SKILL.md"), encoding="utf-8").read()
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        print("  FAIL  SKILL.md has no frontmatter block")
        problems.append("{}: SKILL.md has no frontmatter".format(name))
        return
    # Minimal parse: enough to read `name` without requiring PyYAML.
    declared = None
    for line in match.group(1).splitlines():
        if line.startswith("name:"):
            declared = line.split(":", 1)[1].strip().strip("\"'")
            break
    if declared is None:
        print("  FAIL  frontmatter has no name field")
        problems.append("{}: frontmatter has no name".format(name))
    elif declared != name:
        print("  FAIL  frontmatter name {!r} does not match the directory".format(declared))
        problems.append("{}: name is {!r}".format(name, declared))
    else:
        print("  ok    SKILL.md frontmatter, name matches the directory")


def check_python_scripts(path, problems, name):
    files = sorted(glob.glob(os.path.join(path, "scripts", "*.py")))
    for f in files:
        try:
            ast.parse(open(f, encoding="utf-8").read())
        except SyntaxError as exc:
            print("  FAIL  {} does not parse: {}".format(os.path.relpath(f, path), exc))
            problems.append("{}: {} does not parse".format(name, os.path.basename(f)))
    if files:
        print("  ok    {} python script(s) parse".format(len(files)))
    return bool(files)


def check_js_scripts(path, problems, name):
    files = sorted(glob.glob(os.path.join(path, "scripts", "*.js")))
    if not files:
        return False
    if not shutil.which("node"):
        print("  skip  {} js script(s): node not on PATH".format(len(files)))
        return False
    for f in files:
        proc = subprocess.run(["node", "--check", f], capture_output=True, text=True)
        if proc.returncode != 0:
            print("  FAIL  {}: {}".format(os.path.relpath(f, path), proc.stderr.strip()[:200]))
            problems.append("{}: {} does not parse".format(name, os.path.basename(f)))
    print("  ok    {} js script(s) parse".format(len(files)))
    return True


def run_tests(path, problems, name):
    tests = os.path.join(path, "tests")
    if not os.path.isdir(tests):
        return False
    for argv, label in (
        (["-m", "pytest", "tests", "-q"], "pytest"),
        (["-m", "unittest", "discover", "-s", "tests", "-q"], "unittest"),
    ):
        proc = subprocess.run([sys.executable] + argv, cwd=path,
                              capture_output=True, text=True)
        if proc.returncode == 0:
            last = [l for l in proc.stdout.strip().splitlines() if l.strip()]
            print("  ok    {}: {}".format(label, last[-1] if last else "passed"))
            return True
        if label == "pytest" and "No module named pytest" in (proc.stderr + proc.stdout):
            continue
        print("  FAIL  {} in tests/".format(label))
        print((proc.stdout + proc.stderr).strip()[-800:])
        problems.append("{}: tests failed".format(name))
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skills", nargs="*", help="skill names; default is all of them")
    args = ap.parse_args()

    skills = [(n, p) for n, p in find_skills() if not args.skills or n in args.skills]
    if not skills:
        print("no skill matched", file=sys.stderr)
        return 1

    problems, unverified = [], []
    for name, path in skills:
        print("=" * 70)
        print(name)
        print("=" * 70)
        check_frontmatter(name, path, problems)
        ran = False
        ran |= check_python_scripts(path, problems, name)
        ran |= check_js_scripts(path, problems, name)
        ran |= run_tests(path, problems, name)
        if not ran:
            print("  --    nothing runnable found under scripts/ or tests/")
            unverified.append(name)
        print("")

    print("=" * 70)
    for p in problems:
        print("FAILED: " + p)
    if unverified:
        print("UNVERIFIED (no scripts or tests): " + ", ".join(unverified))
    if not problems:
        print("{} skill(s) checked, nothing failed".format(len(skills)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
