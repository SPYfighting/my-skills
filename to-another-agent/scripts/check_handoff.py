#!/usr/bin/env python3
"""Validate fallback handoff files created by to-another-agent.

Usage:
    python check_handoff.py --handoff AGENT_HANDOFF.md \
        [--tasks tasks/next-agent.md] [--workspace .]

Projects with an established handoff format should use their own checks.
"""

import argparse
import re
import sys
from pathlib import Path


HANDOFF_SECTIONS = (
    "项目现场",
    "已完成与证据",
    "进行中工作",
    "结果与验证",
    "远程任务",
    "决策、边界与风险",
    "接手入口",
)
TASK_SECTIONS = ("接手先验收", "待执行", "受阻")
METADATA = ("更新时间", "当前角色", "当前目标", "状态基线", "后续任务")
ANCHOR_RE = re.compile(r"`([^`\r\n]+):(\d+)(?:-(\d+))?`")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
TASK_RE = re.compile(r"^\s*-\s*\[\s\]\s+(.+?)\s*$")
PLACEHOLDER_RE = re.compile(r"<[^>\n]+>|YYYY-MM-DD|path/to/")
SECRET_PATTERNS = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
)


class Report:
    def __init__(self):
        self.failed = False

    def ok(self, message):
        print("  ok    " + message)

    def warn(self, message):
        print("  warn  " + message)

    def fail(self, message):
        print("  FAIL  " + message)
        self.failed = True


def read_document(path, report):
    if not path.is_file():
        report.fail("file not found: " + str(path))
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        report.fail("cannot read " + str(path) + ": " + str(exc))
        return ""


def headings(text):
    found = []
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            found.append(match.group(1))
    return found


def check_headings(text, required, label, report):
    found = " | ".join(headings(text))
    for section in required:
        if section not in found:
            report.fail(label + " missing section: " + section)
    report.ok(label + " section check examined " + str(len(required)) + " heading(s)")


def check_metadata(text, report):
    for field in METADATA:
        pattern = r"^-\s*" + re.escape(field) + r"\s*：\s*\S"
        if not re.search(pattern, text, re.M):
            report.fail("handoff missing metadata value: " + field)
    report.ok("handoff metadata check examined " + str(len(METADATA)) + " field(s)")


def check_placeholders(text, label, report):
    matches = sorted(set(PLACEHOLDER_RE.findall(text)))
    if matches:
        report.fail(label + " contains unfilled placeholder(s): " + ", ".join(matches[:5]))
    else:
        report.ok(label + " has no template placeholders")


def check_secrets(text, label, report):
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            report.fail(label + " appears to contain a credential or private key")
            return
    report.ok(label + " has no recognized credential pattern")


def check_anchors(text, workspace, report):
    checked = 0
    for match in ANCHOR_RE.finditer(text):
        raw_path, start_s, end_s = match.groups()
        target = Path(raw_path)
        if not target.is_absolute():
            target = workspace / target
        checked += 1
        if not target.is_file():
            report.fail("anchor target missing: " + match.group(0))
            continue
        total = len(target.read_text(encoding="utf-8", errors="replace").splitlines())
        start = int(start_s)
        end = int(end_s) if end_s else start
        if start < 1 or end < start or end > total:
            report.fail(
                "anchor out of range: " + match.group(0)
                + " (file has " + str(total) + " lines)"
            )
    if checked:
        report.ok(str(checked) + " file anchor(s) resolve")
    else:
        report.warn("no file:line anchors found; output paths or commands may be the evidence")


def task_blocks(text):
    lines = text.splitlines()
    current_heading = ""
    starts = []
    for index, line in enumerate(lines):
        heading = HEADING_RE.match(line)
        if heading:
            current_heading = heading.group(1)
        if TASK_RE.match(line):
            starts.append((index, current_heading))
    for index, (start, section) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(lines)
        yield section, lines[start], lines[start + 1:end]


def check_tasks(text, report):
    total = 0
    for section, task_line, body in task_blocks(text):
        total += 1
        body_text = "\n".join(body)
        if not re.search(r"^\s+-\s*完成判据\s*：\s*\S", body_text, re.M):
            report.fail("unchecked task lacks 完成判据: " + task_line.strip())
        if "接手先验收" in section:
            if not re.search(r"^\s+-\s*验收动作\s*：\s*\S", body_text, re.M):
                report.fail("acceptance-first task lacks 验收动作: " + task_line.strip())
    if total:
        report.ok(str(total) + " unchecked task(s) have been examined")
    else:
        report.warn("task file contains no unchecked tasks")


def check_remote_section(text, report):
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "## 远程任务"), None)
    if start is None:
        return
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    body = "\n".join(lines[start + 1:end]).strip()
    if not body:
        report.fail("remote-work section is empty; record no active tasks or the active jobs")
        return
    if body in ("无活动远程任务", "无活动远程任务。"):
        report.ok("remote-work section explicitly records no active task")
        return
    fields = (
        "任务标识",
        "当前状态",
        "最近核查",
        "日志或输出",
        "监控方式",
        "接管动作",
        "停止条件",
    )
    blocks = re.split(r"^###\s+", body, flags=re.M)
    jobs = [block for block in blocks[1:] if block.strip()]
    if not jobs:
        report.fail("active remote task needs a level-3 task heading")
        return
    for job in jobs:
        job_name = job.splitlines()[0].strip()
        for field in fields:
            pattern = r"^-\s*" + re.escape(field) + r"\s*：\s*\S"
            if not re.search(pattern, job, re.M):
                report.fail("remote task " + job_name + " missing field: " + field)
    report.ok(str(len(jobs)) + " active remote-task record(s) examined")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", required=True, help="fallback AGENT_HANDOFF.md")
    parser.add_argument("--tasks", help="fallback tasks/next-agent.md")
    parser.add_argument("--workspace", default=".", help="root for relative file anchors")
    args = parser.parse_args(argv)

    report = Report()
    workspace = Path(args.workspace)
    handoff = Path(args.handoff)

    print("=" * 70)
    print(handoff)
    print("=" * 70)
    handoff_text = read_document(handoff, report)
    if handoff_text:
        check_headings(handoff_text, HANDOFF_SECTIONS, "handoff", report)
        check_metadata(handoff_text, report)
        check_placeholders(handoff_text, "handoff", report)
        check_secrets(handoff_text, "handoff", report)
        check_anchors(handoff_text, workspace, report)
        check_remote_section(handoff_text, report)

    if args.tasks:
        task_path = Path(args.tasks)
        print("=" * 70)
        print(task_path)
        print("=" * 70)
        task_text = read_document(task_path, report)
        if task_text:
            check_headings(task_text, TASK_SECTIONS, "task file", report)
            check_placeholders(task_text, "task file", report)
            check_secrets(task_text, "task file", report)
            check_tasks(task_text, report)

    print("")
    print("FAILED" if report.failed else "PASSED")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
