#!/usr/bin/env python3
"""Check a cross-agent-review request or result document.

Usage:
    python check_review_doc.py <doc.md> [--workspace <dir>]

Validates file naming, required sections, anchor resolvability, and the
role-specific rules that can be checked mechanically. Exits 1 on failure.

Anchors are written as `path/to/file:88-104` inside backticks. Template
placeholders (path/to/..., or anything with angle brackets) are skipped.
"""

import argparse
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-.+-r\d+-(请求|审查)\.md$")
ANCHOR_RE = re.compile(r"`([^`\s]+?):(\d+)(?:-(\d+))?`")
FINDING_RE = re.compile(r"^###\s+(F\d+)\s+`([^`]+)`")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")

REQUEST_SECTIONS = [
    ("用户原始需求", "user requirement, verbatim"),
    ("交付物", "deliverables"),
    ("关键决策", "key decisions"),
    ("判断依据", "evidence grades"),
    ("已验证", "verified / unverified"),
    ("最不确定处", "top uncertainties"),
    ("不在范围内", "out of scope"),
]

RESULT_SECTIONS = [
    ("核对轨迹", "verification trail"),
    ("发现", "findings"),
    ("逐条回应", "response to flagged uncertainties"),
    ("盲区扫描", "blind-spot sweep"),
    ("未能核实", "could not verify"),
]

SEVERITY = {"阻断", "重要", "可选"}
CONFIDENCE = {"已核实", "存疑"}
MAX_OPTIONAL = 5


class Report:
    def __init__(self):
        self.failed = False

    def ok(self, msg):
        print("  ok    " + msg)

    def warn(self, msg):
        print("  warn  " + msg)

    def fail(self, msg):
        print("  FAIL  " + msg)
        self.failed = True


def split_sections(lines):
    """Return [(heading_text, [body lines])], plus a leading preamble entry."""
    sections = [("", [])]
    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            sections.append((m.group(1), []))
        else:
            sections[-1][1].append(line)
    return sections


def is_placeholder(path_text):
    return path_text.startswith("path/to/") or "<" in path_text or ">" in path_text


def check_anchors(text, workspace, report):
    checked = 0
    for match in ANCHOR_RE.finditer(text):
        raw_path, start_s, end_s = match.group(1), match.group(2), match.group(3)
        if is_placeholder(raw_path):
            continue
        checked += 1
        anchor = match.group(0).strip("`")
        target = Path(raw_path)
        if not target.is_absolute():
            target = workspace / raw_path
        if not target.exists():
            report.fail("anchor target missing: " + anchor)
            continue
        try:
            total = len(target.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError as exc:
            report.fail("anchor unreadable: " + anchor + " (" + str(exc) + ")")
            continue
        start = int(start_s)
        end = int(end_s) if end_s else start
        if start < 1 or start > total or end > total or end < start:
            report.fail(
                "anchor out of range: " + anchor + " (file has " + str(total) + " lines)"
            )
    if checked:
        report.ok(str(checked) + " anchor(s) resolve to real lines")
    else:
        report.warn("no resolvable anchors found (template only?)")


def check_sections(sections, required, report):
    headings = " | ".join(h for h, _ in sections)
    for keyword, label in required:
        if keyword not in headings:
            report.fail("missing section: " + label + " (expected heading with " + keyword + ")")
    report.ok("section check done, " + str(len(required)) + " required heading(s) examined")


def section_body(sections, keyword):
    for heading, body in sections:
        if keyword in heading:
            return body
    return []


def check_request(sections, report):
    body = section_body(sections, "最不确定处")
    items = [ln for ln in body if re.match(r"^\s*(\d+\.|[-*])\s+\S", ln)]
    if items:
        report.ok(str(len(items)) + " uncertainty item(s) listed")
    else:
        report.fail("top uncertainties section lists no item; at least one is required")

    for keyword in ("关键决策", "最不确定处"):
        for line in section_body(sections, keyword):
            if "锚点" in line and not ANCHOR_RE.search(line):
                report.warn(
                    "anchor without a line range in " + keyword + ": " + line.strip()[:60]
                )


def check_result(lines, report):
    optional = 0
    total = 0
    for line in lines:
        m = FINDING_RE.match(line)
        if not m:
            continue
        total += 1
        label = m.group(2)
        parts = [p.strip() for p in label.split("·")]
        if len(parts) != 2 or parts[0] not in SEVERITY or parts[1] not in CONFIDENCE:
            report.fail(
                "finding " + m.group(1) + " has an invalid label: " + label
                + " (expected <阻断|重要|可选>·<已核实|存疑>)"
            )
            continue
        if parts[0] == "可选":
            optional += 1
    if total:
        report.ok(str(total) + " finding(s) carry a well-formed label")
    else:
        report.warn("no findings found; a clean review is fine, an unfilled template is not")
    if optional > MAX_OPTIONAL:
        report.fail(
            str(optional) + " optional-level findings exceed the cap of " + str(MAX_OPTIONAL)
        )

    verdict_lines = [ln for ln in lines if "结论" in ln and ln.strip().startswith("-")]
    if not verdict_lines:
        report.fail("no verdict line found (expected a line with 结论)")
    elif all(w in verdict_lines[0] for w in ("通过", "有条件通过", "需返工")):
        report.fail("verdict line still lists every option; pick one")
    else:
        report.ok("verdict line present")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("doc", help="path to the request or result markdown file")
    parser.add_argument(
        "--workspace",
        default=".",
        help="root that anchor paths are relative to (default: current directory)",
    )
    args = parser.parse_args(argv)

    doc = Path(args.doc)
    workspace = Path(args.workspace)
    report = Report()

    print("=" * 70)
    print(doc.name)
    print("=" * 70)

    if not doc.is_file():
        report.fail("file not found: " + str(doc))
        return 1

    if NAME_RE.match(doc.name):
        report.ok("filename follows <date>-<task>-r<n>-<role>.md")
    else:
        report.fail(
            "filename does not follow <YYYY-MM-DD>-<task>-r<n>-请求.md or -审查.md: " + doc.name
        )

    text = doc.read_text(encoding="utf-8")
    lines = text.splitlines()
    sections = split_sections(lines)

    if doc.name.endswith("-审查.md"):
        check_sections(sections, RESULT_SECTIONS, report)
        check_result(lines, report)
    else:
        check_sections(sections, REQUEST_SECTIONS, report)
        check_request(sections, report)

    check_anchors(text, workspace, report)

    print("")
    print("FAILED" if report.failed else "PASSED")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
