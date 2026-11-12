#!/usr/bin/env python3
"""Validate to-another-agent handoff, task, review-request, or review-result files.

Usage:
    python check_relay.py <document> [--workspace <dir>] [--tasks <task-file>]

Documents marked ``to-another-agent/v2`` use the closed-loop contract.
Legacy review request/result files remain valid under the earlier rules.
"""

import argparse
import math
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path


PROTOCOL = "to-another-agent/v2"
REVIEW_NAME_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})-(?P<task>.+)-r(?P<round>\d+)-(?P<role>请求|审查)\.md$"
)
ANCHOR_RE = re.compile(r"`([^`\r\n]+):(\d+)(?:-(\d+))?`")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$")
TASK_RE = re.compile(r"^\s*-\s*\[\s\]\s+(.+?)\s*$")
FINE_TASK_RE = re.compile(
    r"^-\s*\[([ xX])\]\s+(T[\w.-]+)\s+(.+?)\s*$"
)
FINE_STEP_RE = re.compile(
    r"^\s+\d+\.\s*\[([ xX])\]\s+(S[\w.-]+)\s+(.+?)\s*$"
)
EXECUTION_REPORT_RE = re.compile(r"^###\s+(R[\w.-]+)\s*$")
SKILL_REFERENCE_RE = re.compile(
    r"(?:\$to-another-agent\b|`to-another-agent`(?:\s*(?:skill|技能))?|"
    r"(?<![\w/.-])to-another-agent\s+(?:skill|技能))",
    re.I,
)
SUBAGENT_TERM_RE = re.compile(r"(?:子智能体|子\s*agent|sub-?agent)", re.I)
MANDATORY_SUBAGENT_PATTERNS = (
    re.compile(
        r"(?:必须|务必|应当|需要|请)\s*"
        r"(?:创建|使用|调用|启动|派遣|安排|要求)"
        r"[^，。；\n]{0,20}(?:子智能体|子\s*agent|sub-?agent)",
        re.I,
    ),
    re.compile(
        r"\b(?:must|always|please|required\s+to)\s+"
        r"(?:use|spawn|create|launch|delegate\s+to)\b"
        r"[^.\n;]{0,30}\bsub-?agent\b",
        re.I,
    ),
    re.compile(
        r"(?:让|由)\s*(?:一个|某个)?\s*"
        r"(?:子智能体|子\s*agent|sub-?agent)\s*"
        r"(?:负责|执行|检查|核验|审查|处理)",
        re.I,
    ),
    re.compile(
        r"(?:^|[；。！!\n>])\s*(?:创建|使用|调用|启动|派遣)"
        r"[^，。；\n]{0,20}(?:子智能体|子\s*agent|sub-?agent)",
        re.I,
    ),
    re.compile(r"\b(?:have|let)\s+(?:a\s+)?sub-?agent\b", re.I),
)
MODEL_OR_RUNTIME_NAME = (
    r"(?:gpt(?:[-\s]?[0-9][\w.-]*)?|luna|"
    r"claude(?:[-\s](?:code|opus|sonnet|haiku|[0-9][\w.-]*))?|"
    r"gemini(?:[-\s][\w.-]+)?|codex|opencode|"
    r"deepseek(?:[-\s][\w.-]+)?|qwen(?:[-\s][\w.-]+)?|"
    r"llama(?:[-\s][\w.-]+)?|mistral(?:[-\s][\w.-]+)?)"
)
CONCRETE_RUNTIME_ASSIGNMENT_PATTERNS = (
    re.compile(
        r"(?:请|必须|务必|应当|需要)?\s*"
        r"(?:使用|采用|指定|选择|调用)\s*"
        + MODEL_OR_RUNTIME_NAME
        + r"(?:\s*模型)?",
        re.I,
    ),
    re.compile(
        r"\b(?:must\s+|always\s+|please\s+|required\s+to\s+)?"
        r"(?:use|select|choose|run(?:\s+this)?\s+on)\s+"
        + MODEL_OR_RUNTIME_NAME
        + r"\b",
        re.I,
    ),
    re.compile(
        r"(?:由|交给)\s*"
        + MODEL_OR_RUNTIME_NAME
        + r"(?:\s*模型)?\s*(?:执行|完成|处理|审查|核验)",
        re.I,
    ),
    re.compile(
        r"\bdelegate(?:\s+this|\s+the\s+\w+)?\s+to\s+"
        + MODEL_OR_RUNTIME_NAME
        + r"\b",
        re.I,
    ),
)
RUNTIME_CONTROL_RE = re.compile(
    r"\b(?:spawn_agent|fork_turns|reasoning_effort|service_tier|"
    r"model_override)\b|(?:^|[\s(,])model\s*[:=]",
    re.I | re.M,
)
FINDING_HEADER_RE = re.compile(
    r"^###\s+(F\d+)\s+`(阻断|重要|可选)·(已核实|存疑)`(?:\s+.+)?$"
)
PLACEHOLDER_RE = re.compile(r"<[^>\n]+>|YYYY-MM-DD|path/to/")
COMMAND_ANCHOR_RE = re.compile(
    r"(?:命令|command)\s*[：:]\s*`[^`\r\n]+`",
    re.I,
)
SECRET_PATTERNS = (
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
    ),
    re.compile(
        r"https?://[^\s]+[?&](?:X-Amz-Signature|X-Goog-Signature|Signature)="
        r"[A-Za-z0-9%_-]{16,}",
        re.I,
    ),
    re.compile(
        r"https?://[^\s]+\.blob\.core\.windows\.net/[^\s?]*\?"
        r"(?=[^\s]*\bsv=)(?=[^\s]*[&?]sig=[A-Za-z0-9%_-]{16,})[^\s]+",
        re.I,
    ),
    re.compile(
        r"\b(?:cookie|set-cookie)\s*:\s*[^\r\n;=]+="
        r"[A-Za-z0-9._~+/%-]{16,}",
        re.I,
    ),
    re.compile(
        r"\b(?:sessionid|session_id|access_token|refresh_token)\s*[:=]\s*"
        r"[A-Za-z0-9._~+/%-]{16,}",
        re.I,
    ),
    re.compile(
        r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://"
        r"[^\s/:@]+:[^\s/@]+@",
        re.I,
    ),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
)

HANDOFF_SECTIONS = (
    ("项目现场", "project scene"),
    ("已完成与证据", "completed work and evidence"),
    ("进行中工作", "work in progress"),
    ("结果与验证", "results and validation"),
    ("远程任务", "remote work"),
    ("决策、边界与风险", "decisions, boundaries, and risks"),
    ("接手入口", "takeover entry"),
    ("下一位 agent 接手", "next-agent prompt"),
)
TASK_SECTIONS = (
    ("接手先验收", "acceptance-first tasks"),
    ("待执行", "pending tasks"),
    ("受阻", "blocked tasks"),
)
REQUEST_SECTIONS = (
    ("用户原始需求", "user requirement, verbatim"),
    ("交付物", "deliverables"),
    ("关键决策", "key decisions"),
    ("判断依据", "evidence grades"),
    ("已验证", "verified and unverified"),
    ("最不确定处", "top uncertainties"),
    ("不在范围内", "out of scope"),
)
RESULT_SECTIONS = (
    ("核对轨迹", "verification trail"),
    ("发现", "findings"),
    ("逐条回应", "responses to uncertainties"),
    ("盲区扫描", "blind-spot sweep"),
    ("未能核实", "unverified items"),
)
HANDOFF_METADATA = (
    ("更新时间", "updated"),
    ("当前角色", "current role"),
    ("当前目标", "current objective"),
    ("状态基线", "state baseline"),
    ("后续任务", "follow-up task"),
)
EXPECTED_TYPES = {
    "handoff": {"continue"},
    "task": {"continue", "address-findings"},
    "request": {"review-request"},
    "result": {"review-result"},
}
NEXT_ROLES = {
    "接续方",
    "工作方",
    "审查方",
    "监控方",
    "执行方",
    "规划方",
    "验收方",
}
ROLE_SOURCES = {"default", "explicit"}
OUTPUT_LABELS = {
    "执行策略": "execution strategy",
    "下一角色": "next role",
    "结束时间": "ending time",
    "收尾开始": "wrap-up time",
    "接手时间": "takeover time",
    "收尾策略": "wrap-up strategy",
    "目标": "objective",
    "输入": "input",
    "输出": "output",
    "完成判据": "completion criterion",
    "默认回退": "default fallback",
    "回报节点": "report milestone",
    "操作": "operation",
    "核验": "verification",
    "通过条件": "pass condition",
    "未通过动作": "failure action",
    "预计耗时": "estimated duration",
    "证据": "evidence",
    "时间": "time",
    "状态": "status",
    "完成步骤": "completed steps",
    "关键结果": "key result",
    "核验证据": "verification evidence",
    "剩余事项": "remaining work",
    "建议下一角色": "suggested next role",
}
MAX_OPTIONAL = 5


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
        report.fail("cannot read file: " + str(exc))
        return ""


def split_sections(text):
    sections = [("", [])]
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            sections.append((match.group(1), []))
        else:
            sections[-1][1].append(line)
    return sections


def section_body(sections, keyword):
    for heading, body in sections:
        if keyword in heading:
            return "\n".join(body)
    return ""


def level2_section(text, keyword):
    """Return a level-2 section including any nested level-3 content."""
    lines = text.splitlines()
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if re.match(r"^##\s+", line) and keyword in line
        ),
        None,
    )
    if start is None:
        return ""
    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if re.match(r"^##\s+", lines[index])
        ),
        len(lines),
    )
    return "\n".join(lines[start + 1:end])


def has_anchor_or_command(text):
    return bool(ANCHOR_RE.search(text) or COMMAND_ANCHOR_RE.search(text))


def metadata_value(text, key):
    preamble_lines = []
    for line in text.splitlines():
        if re.match(r"^##\s+", line):
            break
        preamble_lines.append(line)
    preamble = "\n".join(preamble_lines)
    match = re.search(
        r"^-\s*" + re.escape(key) + r"\s*[：:]\s*(.+?)\s*$",
        preamble,
        re.M,
    )
    return match.group(1).strip() if match else None


def plain_value(value):
    if value is None:
        return None
    return value.strip().strip("`").strip().strip("*").strip()


def backtick_path(value):
    if value is None:
        return None
    match = re.search(r"`([^`]+)`", value)
    return match.group(1) if match else None


def is_v2(text):
    return plain_value(metadata_value(text, "协议")) == PROTOCOL


def has_v2_signals(text):
    """Return whether a review document visibly opts into the v2 contract.

    Historical review documents can share generic sections such as 本轮范围,
    so only fields introduced by v2 count as signals. A document that removes
    every v2-only field is indistinguishable from a real legacy document and is
    intentionally handled by the compatibility path.
    """
    relay_type = plain_value(metadata_value(text, "交接类型"))
    headings = {heading for heading, _ in split_sections(text)}
    return relay_type in {"review-request", "review-result"} or any(
        "下一位 agent 接手" in heading for heading in headings
    )


def detect_kind(path, text):
    if path.name == "AGENT_HANDOFF.md":
        return "handoff"
    if path.name == "next-agent.md":
        return "task"
    match = REVIEW_NAME_RE.match(path.name)
    if match:
        return "request" if match.group("role") == "请求" else "result"
    heading_text = " | ".join(heading for heading, _ in split_sections(text))
    if "项目现场" in heading_text and "接手入口" in heading_text:
        return "handoff"
    if all(keyword in heading_text for keyword, _ in TASK_SECTIONS):
        return "task"
    if "用户原始需求" in heading_text and "交付物" in heading_text:
        return "request"
    if "核对轨迹" in heading_text and "发现" in heading_text:
        return "result"
    return None


def check_sections(sections, required, label, report):
    headings = " | ".join(heading for heading, _ in sections)
    for keyword, description in required:
        if keyword not in headings:
            report.fail(label + " missing section: " + description)
    report.ok(label + " section check examined " + str(len(required)) + " heading(s)")


def without_fenced_code(text):
    kept = []
    fence_char = None
    for line in text.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            char = match.group(1)[0]
            if fence_char is None:
                fence_char = char
            elif fence_char == char:
                fence_char = None
            continue
        if fence_char is None:
            kept.append(line)
    return "\n".join(kept)


def check_common(text, label, report):
    placeholders = sorted(set(PLACEHOLDER_RE.findall(without_fenced_code(text))))
    if placeholders:
        report.fail(label + " contains unfilled template placeholder(s)")
    else:
        report.ok(label + " has no template placeholders")
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            report.fail(label + " appears to contain a credential or private key")
            return
    report.ok(label + " has no recognized credential pattern")


def check_anchors(text, workspace, report):
    checked = 0
    for match in ANCHOR_RE.finditer(text):
        raw_path, start_s, end_s = match.groups()
        if raw_path.startswith("path/to/") or "<" in raw_path or ">" in raw_path:
            continue
        target = Path(raw_path)
        if not target.is_absolute():
            target = workspace / target
        checked += 1
        if not target.is_file():
            report.fail("anchor target missing: " + match.group(0))
            continue
        try:
            total = len(
                target.read_text(encoding="utf-8", errors="replace").splitlines()
            )
        except OSError as exc:
            report.fail("anchor target unreadable: " + str(exc))
            continue
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
        report.warn("no resolvable file:line anchors found")


def check_v2_metadata(text, kind, report):
    protocol = plain_value(metadata_value(text, "协议"))
    relay_type = plain_value(metadata_value(text, "交接类型"))
    if protocol != PROTOCOL:
        report.fail("missing or invalid v2 protocol marker")
    else:
        report.ok("v2 protocol marker present")
    if relay_type not in EXPECTED_TYPES[kind]:
        report.fail("invalid relay type for " + kind)
    else:
        report.ok("relay type matches " + kind)
    check_role_metadata(text, report)


def check_role_metadata(text, report):
    role = plain_value(metadata_value(text, "下一角色"))
    source = plain_value(metadata_value(text, "角色来源"))
    if role and role not in NEXT_ROLES:
        report.fail("invalid declared next role")
    if source and source not in ROLE_SOURCES:
        report.fail("invalid role source")
    if source and not role:
        report.fail("role source is set without a next role")
    if role and not source:
        report.warn("legacy next-role metadata has no role source")
    if source == "default" and role != "接续方":
        report.fail("default role source must use the continuation role")
    if role and source:
        report.ok("next role and role source are consistent")


def check_next_prompt(text, sections, kind, path, report):
    body = section_body(sections, "下一位 agent 接手")
    if not body.strip():
        report.fail("missing next-agent prompt body")
        return
    skill_references = SKILL_REFERENCE_RE.findall(body)
    if not skill_references:
        report.fail("next-agent prompt does not name the to-another-agent skill")
    if path.name not in body:
        report.fail("next-agent prompt does not name its source document")
    role_word = {"request": "审查方", "result": "工作方"}.get(kind)
    if role_word and role_word not in body:
        report.fail("next-agent prompt does not name the required role")
    declared_role = plain_value(metadata_value(text, "下一角色"))
    if declared_role:
        if declared_role not in NEXT_ROLES:
            report.fail("invalid declared next role")
        elif declared_role not in body:
            report.fail("next-agent prompt does not name declared role")
        if len(skill_references) < 2:
            report.fail("next-agent prompt does not require relay callback")
    mandatory_subagent = any(
        pattern.search(body) for pattern in MANDATORY_SUBAGENT_PATTERNS
    )
    if mandatory_subagent:
        report.fail("next-agent prompt mandates subagent orchestration")
    elif SUBAGENT_TERM_RE.search(body) and not (
        kind == "request" or declared_role == "审查方"
    ):
        report.fail("subagent suggestion is outside an independent review handoff")
    if any(
        pattern.search(body) for pattern in CONCRETE_RUNTIME_ASSIGNMENT_PATTERNS
    ):
        report.fail("next-agent prompt assigns a concrete runtime or model")
    if RUNTIME_CONTROL_RE.search(body):
        report.fail("next-agent prompt contains runtime-specific controls")
    report.ok("next-agent prompt contract examined")


def check_review_filename(path, expected_role, report):
    match = REVIEW_NAME_RE.match(path.name)
    if not match:
        report.fail("review filename does not follow <date>-<task>-r<n>-<role>.md")
        return None
    if match.group("role") != expected_role:
        report.fail("review filename role does not match document kind")
    else:
        report.ok("review filename and role match")
    if int(match.group("round")) < 1:
        report.fail("review round must start at r1")
    return match


def is_none_value(value):
    return plain_value(value or "").rstrip("。.").lower() in {
        "无",
        "none",
        "n/a",
        "not applicable",
    }


def parse_aware_time(value, key, report):
    raw = plain_value(value)
    try:
        parsed = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        report.fail(key + " must be an ISO 8601 absolute time")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        report.fail(key + " must include a timezone")
        return None
    return parsed


def calculate_auto_wrapup(takeover, ending):
    remaining_minutes = (ending - takeover).total_seconds() / 60
    if remaining_minutes < 10:
        return takeover
    reserve_minutes = max(10, min(30, math.ceil(remaining_minutes * 0.20)))
    return ending - timedelta(minutes=reserve_minutes)


def check_deadline_metadata(text, report):
    ending_value = metadata_value(text, "结束时间")
    if ending_value is None or is_none_value(ending_value):
        wrapup_value = metadata_value(text, "收尾开始")
        if wrapup_value is not None and not is_none_value(wrapup_value):
            report.fail("wrap-up time is set while ending time is none")
        return False

    values = {
        key: metadata_value(text, key)
        for key in ("接手时间", "结束时间", "收尾开始", "收尾策略")
    }
    for key, value in values.items():
        if not value:
            report.fail("deadline mode missing metadata: " + OUTPUT_LABELS[key])
    takeover = (
        parse_aware_time(values["接手时间"], "takeover time", report)
        if values["接手时间"]
        else None
    )
    ending = parse_aware_time(values["结束时间"], "ending time", report)
    wrapup = (
        parse_aware_time(values["收尾开始"], "wrap-up time", report)
        if values["收尾开始"]
        else None
    )
    strategy = plain_value(values["收尾策略"])
    if strategy and strategy not in {"auto", "user-specified"}:
        report.fail("invalid wrap-up strategy")
    if takeover and ending and ending <= takeover:
        report.fail("ending time must be after takeover time")
    if takeover and wrapup and wrapup < takeover:
        report.fail("wrap-up time must not precede takeover time")
    if wrapup and ending and wrapup >= ending:
        report.fail("wrap-up time must be earlier than ending time")
    if takeover and ending and wrapup and strategy == "auto":
        expected = calculate_auto_wrapup(takeover, ending)
        if wrapup != expected:
            report.fail("auto wrap-up time does not match the adaptive formula")
    report.ok("deadline and wrap-up metadata examined")
    return True


def check_handoff_prompt_state(text, sections, workspace, report):
    prompt = section_body(sections, "下一位 agent 接手")
    follow_up = metadata_value(text, "后续任务")
    if is_none_value(follow_up):
        if re.search(r"tasks?[/\\]|读取[^\n。]*任务文件", prompt, re.I):
            report.fail("prompt references a task file but follow-up task is none")
    else:
        task_reference = backtick_path(follow_up)
        if not task_reference:
            report.fail("follow-up task must name a backticked task-file path or none")
        else:
            target = Path(task_reference)
            if not target.is_absolute():
                target = workspace / target
            if not target.is_file():
                report.fail("referenced follow-up task file is missing")
            if task_reference not in prompt and Path(task_reference).name not in prompt:
                report.fail("next-agent prompt does not name the follow-up task file")

    remote = level2_section(text, "远程任务").strip()
    no_remote = remote in {"无活动远程任务", "无活动远程任务。"}
    prompt_mentions_remote = bool(
        re.search(r"远程(?:任务|进程)|(?:接管|监控|接收)[^\n。]*远程", prompt)
    )
    if no_remote and prompt_mentions_remote:
        report.fail("prompt mentions remote takeover but no remote task is active")
    elif not no_remote and not prompt_mentions_remote:
        report.fail("active remote work is missing from the next-agent prompt")
    report.ok("handoff prompt matches task and remote-work state")


def check_handoff(text, sections, path, workspace, report):
    check_sections(sections, HANDOFF_SECTIONS, "handoff", report)
    for key, description in HANDOFF_METADATA:
        if not metadata_value(text, key):
            report.fail("handoff missing metadata: " + description)
    report.ok("handoff metadata check examined " + str(len(HANDOFF_METADATA)) + " field(s)")
    check_v2_metadata(text, "handoff", report)
    check_next_prompt(text, sections, "handoff", path, report)
    check_remote_section(text, report)
    check_handoff_prompt_state(text, sections, workspace, report)
    check_deadline_metadata(text, report)


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
        yield section, lines[start + 1:end]


def fine_task_blocks(text):
    """Yield top-level fine tasks without confusing their numbered steps."""
    lines = text.splitlines()
    starts = []
    current_heading = ""
    for index, line in enumerate(lines):
        heading = HEADING_RE.match(line)
        if heading:
            current_heading = heading.group(1)
        match = FINE_TASK_RE.match(line)
        if match:
            starts.append((index, current_heading, match))
    for index, (start, section, match) in enumerate(starts):
        next_task = starts[index + 1][0] if index + 1 < len(starts) else len(lines)
        next_section = next(
            (
                candidate
                for candidate in range(start + 1, len(lines))
                if re.match(r"^##\s+", lines[candidate])
            ),
            len(lines),
        )
        end = min(next_task, next_section)
        yield {
            "section": section,
            "completed": match.group(1).lower() == "x",
            "id": match.group(2),
            "title": match.group(3),
            "lines": lines[start + 1:end],
        }


def fine_steps(lines):
    starts = []
    for index, line in enumerate(lines):
        match = FINE_STEP_RE.match(line)
        if match:
            starts.append((index, match))
    for index, (start, match) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(lines)
        yield {
            "completed": match.group(1).lower() == "x",
            "id": match.group(2),
            "title": match.group(3),
            "body": "\n".join(lines[start + 1:end]),
        }


def list_field(text, key):
    match = re.search(
        r"^\s*-\s*" + re.escape(key) + r"\s*[：:]\s*(\S.*)$",
        text,
        re.M,
    )
    return match.group(1).strip() if match else None


def execution_reports(text, report):
    body = level2_section(text, "执行回报").strip()
    if not body or body in {"无", "无。"}:
        return []
    lines = body.splitlines()
    starts = []
    for index, line in enumerate(lines):
        match = EXECUTION_REPORT_RE.match(line)
        if match:
            starts.append((index, match.group(1)))
    if not starts:
        report.fail("execution-report section needs an R-prefixed level-3 heading")
        return []
    records = []
    seen = set()
    required = (
        "时间",
        "状态",
        "完成步骤",
        "关键结果",
        "核验证据",
        "剩余事项",
        "建议下一角色",
    )
    allowed_status = {
        "milestone",
        "complete",
        "blocked",
        "deadline-handoff",
        "remote-running",
    }
    for index, (start, report_id) in enumerate(starts):
        end = starts[index + 1][0] if index + 1 < len(starts) else len(lines)
        record_body = "\n".join(lines[start + 1:end])
        if report_id in seen:
            report.fail("duplicate execution report id: " + report_id)
        seen.add(report_id)
        values = {field: list_field(record_body, field) for field in required}
        for field, value in values.items():
            if not value:
                report.fail(
                    "execution report "
                    + report_id
                    + " missing field: "
                    + OUTPUT_LABELS[field]
                )
        if values["状态"] and plain_value(values["状态"]) not in allowed_status:
            report.fail("execution report " + report_id + " has invalid status")
        if values["时间"]:
            parse_aware_time(
                values["时间"], "execution report " + report_id + " time", report
            )
        role = plain_value(values["建议下一角色"])
        if role and role not in NEXT_ROLES:
            report.fail("execution report " + report_id + " has invalid next role")
        records.append({"id": report_id, **values})
    report.ok(str(len(records)) + " execution report(s) examined")
    return records


def is_placeholder_evidence(value):
    return plain_value(value or "").rstrip("。.").lower() in {
        "",
        "无",
        "待执行",
        "待补",
        "pending",
        "todo",
        "n/a",
    }


def check_fine_task(text, report):
    required_metadata = {
        "执行策略": "persistent",
        "下一角色": None,
    }
    for key, expected in required_metadata.items():
        value = plain_value(metadata_value(text, key))
        if not value:
            report.fail("fine task missing metadata: " + OUTPUT_LABELS[key])
        elif expected and value != expected:
            report.fail("fine task has invalid " + OUTPUT_LABELS[key])
    role = plain_value(metadata_value(text, "下一角色"))
    if role and role not in NEXT_ROLES:
        report.fail("fine task has invalid next role")

    if not level2_section(text, "执行回报"):
        report.fail("fine task file missing execution-report section")
    reports = execution_reports(text, report)
    if reports and role:
        latest_role = plain_value(reports[-1].get("建议下一角色"))
        if latest_role and latest_role != role:
            report.fail("latest execution-report role differs from task next role")
    tasks = list(fine_task_blocks(text))
    if not tasks:
        report.fail("fine task file contains no top-level task")
        return
    task_fields = ("目标", "输入", "输出", "完成判据", "默认回退", "回报节点")
    step_fields = ("操作", "核验", "通过条件", "未通过动作", "证据")
    ending_value = metadata_value(text, "结束时间")
    deadline_active = ending_value is not None and not is_none_value(ending_value)
    step_count = 0
    seen_steps = set()
    for task in tasks:
        task_text = "\n".join(task["lines"])
        for field in task_fields:
            if not list_field(task_text, field):
                report.fail(
                    "fine task "
                    + task["id"]
                    + " missing field: "
                    + OUTPUT_LABELS[field]
                )
        steps = list(fine_steps(task["lines"]))
        if not steps:
            report.fail("fine task " + task["id"] + " contains no execution step")
        for step in steps:
            step_count += 1
            if step["id"] in seen_steps:
                report.fail("duplicate fine step id: " + step["id"])
            seen_steps.add(step["id"])
            for field in step_fields:
                if not list_field(step["body"], field):
                    report.fail(
                        "fine step "
                        + step["id"]
                        + " missing field: "
                        + OUTPUT_LABELS[field]
                    )
            if deadline_active and not list_field(step["body"], "预计耗时"):
                report.fail(
                    "fine step "
                    + step["id"]
                    + " missing field: estimated duration"
                )
            failure_action = list_field(step["body"], "未通过动作") or ""
            repair = "修复" in failure_action or re.search(r"\brepair\b", failure_action, re.I)
            reverify = "重验" in failure_action or re.search(
                r"\bre-?verif(?:y|ication)\b", failure_action, re.I
            )
            if failure_action and not (repair and reverify):
                report.fail(
                    "fine step "
                    + step["id"]
                    + " failure action must require repair and reverification"
                )
            evidence = list_field(step["body"], "证据")
            if step["completed"] and is_placeholder_evidence(evidence):
                report.fail(
                    "completed fine step "
                    + step["id"]
                    + " has placeholder evidence"
                )
        if task["completed"] and any(not step["completed"] for step in steps):
            report.fail(
                "completed fine task " + task["id"] + " has unfinished steps"
            )
        if task["completed"] and not any(
            plain_value(record.get("状态")) == "complete" for record in reports
        ):
            report.fail(
                "completed fine task " + task["id"] + " has no completion report"
            )
        if task["completed"]:
            completion_reports = [
                record
                for record in reports
                if plain_value(record.get("状态")) == "complete"
            ]
            for step in steps:
                if not any(
                    re.search(
                        r"(?<![A-Za-z0-9])"
                        + re.escape(step["id"])
                        + r"(?![A-Za-z0-9])",
                        record.get("完成步骤") or "",
                    )
                    for record in completion_reports
                ):
                    report.fail(
                        "completion report does not cover step " + step["id"]
                    )
        milestone_value = list_field(task_text, "回报节点") or ""
        milestone_ids = set(re.findall(r"\bS[\w.-]+\b", milestone_value))
        if not milestone_ids:
            report.fail("fine task " + task["id"] + " needs at least one report milestone")
        known_step_ids = {step["id"] for step in steps}
        for milestone_id in sorted(milestone_ids - known_step_ids):
            report.fail("unknown report milestone " + milestone_id)
        completed_milestones = {
            step["id"]
            for step in steps
            if step["completed"] and step["id"] in milestone_ids
        }
        for milestone_id in sorted(completed_milestones):
            if not any(
                re.search(
                    r"(?<![A-Za-z0-9])"
                    + re.escape(milestone_id)
                    + r"(?![A-Za-z0-9])",
                    record.get("完成步骤") or "",
                )
                for record in reports
            ):
                report.fail(
                    "milestone " + milestone_id + " has no execution report"
                )
    report.ok(
        str(len(tasks)) + " fine task(s) and " + str(step_count) + " step(s) examined"
    )


def check_task(text, sections, report):
    check_sections(sections, TASK_SECTIONS, "task file", report)
    check_v2_metadata(text, "task", report)
    total = 0
    for section, body in task_blocks(text):
        total += 1
        body_text = "\n".join(body)
        if not re.search(r"^\s+-\s*完成判据\s*：\s*\S", body_text, re.M):
            report.fail("unchecked task " + str(total) + " lacks a completion criterion")
        if "接手先验收" in section:
            if not re.search(r"^\s+-\s*验收动作\s*：\s*\S", body_text, re.M):
                report.fail("acceptance-first task " + str(total) + " lacks a validation action")
    if total:
        report.ok(str(total) + " unchecked task(s) examined")
    else:
        report.warn("task file contains no unchecked tasks")
    granularity = plain_value(metadata_value(text, "任务粒度"))
    if granularity == "fine":
        check_fine_task(text, report)
    elif granularity:
        report.fail("unsupported task granularity")
    check_deadline_metadata(text, report)


def check_remote_section(text, report):
    lines = text.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if line.strip() == "## 远程任务"),
        None,
    )
    if start is None:
        report.fail("remote-work section is missing")
        return
    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if lines[index].startswith("## ")
        ),
        len(lines),
    )
    body = "\n".join(lines[start + 1:end]).strip()
    if not body:
        report.fail("remote-work section is empty")
        return
    if body in ("无活动远程任务", "无活动远程任务。"):
        report.ok("remote-work section records no active task")
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
        report.fail("active remote work needs a level-3 task heading")
        return
    for index, job in enumerate(jobs, 1):
        for field in fields:
            pattern = r"^-\s*" + re.escape(field) + r"\s*：\s*\S"
            if not re.search(pattern, job, re.M):
                report.fail(
                    "remote task " + str(index) + " missing required takeover field"
                )
    report.ok(str(len(jobs)) + " active remote-task record(s) examined")


def check_request(text, sections, path, workspace, report):
    match = check_review_filename(path, "请求", report)
    check_sections(sections, REQUEST_SECTIONS, "review request", report)
    body = section_body(sections, "最不确定处")
    items = [
        line for line in body.splitlines()
        if re.match(r"^\s*(\d+\.|[-*])\s+\S", line)
    ]
    if items:
        report.ok(str(len(items)) + " uncertainty item(s) listed")
    else:
        report.fail("review request needs at least one uncertainty item")

    if not (is_v2(text) or has_v2_signals(text)):
        report.warn("legacy review request: v2 relay fields are not required")
        return

    check_v2_metadata(text, "request", report)
    check_sections(
        sections,
        (("本轮范围", "current-round scope"), ("下一位 agent 接手", "next-agent prompt")),
        "v2 review request",
        report,
    )
    check_next_prompt(text, sections, "request", path, report)
    check_request_evidence_details(text, report)
    if match and int(match.group("round")) > 1:
        previous = metadata_value(text, "上一轮")
        previous_path = backtick_path(previous)
        if not previous_path or plain_value(previous) == "无":
            report.fail("review request r2+ must point to the previous result")
        else:
            target = Path(previous_path)
            if not target.is_absolute():
                target = workspace / target
            if not target.is_file():
                report.fail("previous review result is missing")
            else:
                previous_match = REVIEW_NAME_RE.match(target.name)
                if (
                    not previous_match
                    or previous_match.group("role") != "审查"
                ):
                    report.fail("previous review result has an invalid filename or role")
                elif match and previous_match.group("task") != match.group("task"):
                    report.fail("previous result must be the same task")
                elif match and int(previous_match.group("round")) != int(
                    match.group("round")
                ) - 1:
                    report.fail("previous result must be from round rN-1")
                else:
                    report.ok("previous result matches the same task and prior round")
        round_body = section_body(sections, "本轮范围")
        if "上一轮未闭合" not in round_body:
            report.fail("review request r2+ must list unresolved prior findings")


def check_request_evidence_details(text, report):
    decisions = level2_section(text, "关键决策")
    decision_starts = [
        match.start()
        for match in re.finditer(r"^###\s+决策\b.*$", decisions, re.M)
    ]
    if not decision_starts:
        report.fail("v2 review request needs at least one key decision")
    for index, start in enumerate(decision_starts, 1):
        end = (
            decision_starts[index]
            if index < len(decision_starts)
            else len(decisions)
        )
        if not has_anchor_or_command(decisions[start:end]):
            report.fail(
                "decision " + str(index) + " needs an anchor or rerunnable command"
            )

    uncertainty = level2_section(text, "最不确定处")
    lines = uncertainty.splitlines()
    item_starts = [
        index
        for index, line in enumerate(lines)
        if re.match(r"^(?:\d+\.|[-*])\s+\S", line)
    ]
    for index, start in enumerate(item_starts, 1):
        end = item_starts[index] if index < len(item_starts) else len(lines)
        if not has_anchor_or_command("\n".join(lines[start:end])):
            report.fail(
                "uncertainty " + str(index) + " needs an anchor or rerunnable command"
            )
    if decision_starts and item_starts:
        report.ok("key decisions and uncertainties have individual evidence anchors")


def parse_findings(lines, report):
    findings = []
    optional = 0
    seen = set()
    for line in lines:
        if not re.match(r"^###\s+F\d+\b", line):
            continue
        match = FINDING_HEADER_RE.match(line)
        if not match:
            report.fail("finding header has an invalid severity/confidence label")
            continue
        finding_id, severity, confidence = match.groups()
        if finding_id in seen:
            report.fail("duplicate finding id: " + finding_id)
        seen.add(finding_id)
        findings.append((finding_id, severity, confidence))
        if severity == "可选":
            optional += 1
    if optional > MAX_OPTIONAL:
        report.fail("optional-level findings exceed the cap of " + str(MAX_OPTIONAL))
    if findings:
        report.ok(str(len(findings)) + " finding label(s) are valid")
    else:
        report.warn("no formal findings listed")
    return findings


def finding_blocks(text):
    lines = text.splitlines()
    starts = [
        index
        for index, line in enumerate(lines)
        if re.match(r"^###\s+F\d+\b", line)
    ]
    for index, start in enumerate(starts):
        end = len(lines)
        for candidate in range(start + 1, len(lines)):
            if re.match(r"^#{1,3}\s+", lines[candidate]):
                end = candidate
                break
        yield lines[start], "\n".join(lines[start + 1:end])


def finding_field(body, key):
    match = re.search(
        r"^\s*-\s*" + re.escape(key) + r"\s*[：:]\s*(\S.*)$",
        body,
        re.M,
    )
    return match.group(1).strip() if match else None


def check_finding_details(text, findings, report):
    valid_by_id = {
        finding_id: (severity, confidence)
        for finding_id, severity, confidence in findings
    }
    checked = 0
    for header, body in finding_blocks(text):
        match = FINDING_HEADER_RE.match(header)
        if not match:
            continue
        finding_id = match.group(1)
        _, confidence = valid_by_id[finding_id]
        checked += 1
        position = finding_field(body, "位置")
        if not position:
            report.fail(finding_id + " missing required field: position")
        elif not ANCHOR_RE.search(position):
            report.fail(finding_id + " position needs a file:line anchor")
        if not finding_field(body, "问题"):
            report.fail(finding_id + " missing required field: problem")
        evidence_key = "证据" if confidence == "已核实" else "为何存疑"
        evidence_label = "evidence" if confidence == "已核实" else "reason for doubt"
        if not finding_field(body, evidence_key):
            report.fail(finding_id + " missing required field: " + evidence_label)
        if not finding_field(body, "建议动作"):
            report.fail(finding_id + " missing required field: suggested action")
    if checked:
        report.ok(str(checked) + " v2 finding block(s) contain required evidence fields")


def parse_verdict(text, report):
    verdict = plain_value(metadata_value(text, "结论"))
    allowed = {"通过", "有条件通过", "需返工"}
    if verdict not in allowed:
        report.fail("missing or invalid review verdict")
        return None
    report.ok("review verdict is valid")
    return verdict


def check_verdict_mapping(verdict, findings, report):
    blockers = sum(1 for _, severity, _ in findings if severity == "阻断")
    important = sum(1 for _, severity, _ in findings if severity == "重要")
    valid = (
        (verdict == "通过" and blockers == 0 and important == 0)
        or (verdict == "有条件通过" and blockers == 0 and important > 0)
        or (verdict == "需返工" and blockers > 0)
    )
    if valid:
        report.ok("verdict matches open finding severity")
    else:
        report.fail("verdict conflicts with open finding severity")


def check_corresponding_request(text, result_match, workspace, report):
    value = metadata_value(text, "对应请求")
    request_path = backtick_path(value)
    if not request_path:
        report.fail("v2 review result does not point to its request")
        return
    target = Path(request_path)
    if not target.is_absolute():
        target = workspace / target
    if not target.is_file():
        report.fail("corresponding review request is missing")
        return
    request_match = REVIEW_NAME_RE.match(target.name)
    if not request_match or request_match.group("role") != "请求":
        report.fail("corresponding request has an invalid filename")
        return
    if result_match and request_match.group("round") != result_match.group("round"):
        report.fail("review request/result rounds do not match")
    elif result_match and request_match.group("task") != result_match.group("task"):
        report.fail("review request/result task names do not match")
    else:
        report.ok("review result points to the same-task, same-round request")


def check_result(text, sections, path, workspace, report):
    match = check_review_filename(path, "审查", report)
    check_sections(sections, RESULT_SECTIONS, "review result", report)
    lines = text.splitlines()
    findings = parse_findings(lines, report)
    verdict = parse_verdict(text, report)

    if not (is_v2(text) or has_v2_signals(text)):
        report.warn("legacy review result: v2 relay and verdict mapping are not required")
        return

    check_v2_metadata(text, "result", report)
    check_sections(
        sections,
        (
            ("上一轮未闭合发现", "prior unresolved findings"),
            ("下一位 agent 接手", "next-agent prompt"),
        ),
        "v2 review result",
        report,
    )
    check_next_prompt(text, sections, "result", path, report)
    check_corresponding_request(text, match, workspace, report)
    check_finding_details(text, findings, report)
    if verdict:
        check_verdict_mapping(verdict, findings, report)


def validate_document(path, workspace, report):
    text = read_document(path, report)
    if not text:
        return None
    kind = detect_kind(path, text)
    if kind is None:
        report.fail("cannot detect document kind")
        return None
    print("  kind  " + kind)
    sections = split_sections(text)
    check_common(text, kind, report)
    check_anchors(text, workspace, report)
    if kind == "handoff":
        check_handoff(text, sections, path, workspace, report)
    elif kind == "task":
        check_task(text, sections, report)
    elif kind == "request":
        check_request(text, sections, path, workspace, report)
    elif kind == "result":
        check_result(text, sections, path, workspace, report)
    return kind


def check_result_task_coverage(result_path, task_path, report):
    """Require each open blocker/important finding to have a task item."""
    try:
        result_text = result_path.read_text(encoding="utf-8")
        task_text = task_path.read_text(encoding="utf-8")
    except OSError as exc:
        report.fail("cannot cross-check review result and task file: " + str(exc))
        return
    if not is_v2(result_text):
        return

    required = []
    for line in result_text.splitlines():
        match = FINDING_HEADER_RE.match(line)
        if match and match.group(2) in {"阻断", "重要"}:
            required.append(match.group(1))
    if not required:
        report.ok("review result has no blocker/important finding to map to tasks")
        return

    result_match = REVIEW_NAME_RE.match(result_path.name)
    if not result_match:
        return
    round_number = result_match.group("round")

    task_items = []
    for line in task_text.splitlines():
        match = re.match(r"^\s*-\s*\[([ xX])\]\s+(\S.*)$", line)
        if match:
            task_items.append((match.group(1).lower() == "x", match.group(2)))
    open_findings = []
    unmapped = False
    for finding_id in required:
        expected_id = "r" + round_number + "-" + finding_id
        reference = re.compile(
            r"(?<![A-Za-z0-9])"
            + re.escape(expected_id)
            + r"(?![A-Za-z0-9])"
        )
        matching = [
            completed
            for completed, title in task_items
            if reference.search(title)
        ]
        if not matching:
            report.fail(
                finding_id
                + " is not represented in the task file; expected "
                + expected_id
            )
            unmapped = True
        elif not all(matching):
            open_findings.append(finding_id)

    relay_type = plain_value(metadata_value(task_text, "交接类型"))
    if not unmapped and open_findings and relay_type != "address-findings":
        report.fail("task file must use address-findings while findings remain open")
    elif not unmapped and not open_findings and relay_type != "continue":
        report.fail("task file must return to continue after all findings are closed")
    report.ok(str(len(required)) + " blocker/important finding(s) checked against tasks")


def check_handoff_task_argument(handoff_path, task_path, workspace, report):
    try:
        text = handoff_path.read_text(encoding="utf-8")
    except OSError as exc:
        report.fail("cannot cross-check handoff and task file: " + str(exc))
        return
    follow_up = metadata_value(text, "后续任务")
    if is_none_value(follow_up):
        report.fail("--tasks was provided but handoff says follow-up task is none")
        return
    reference = backtick_path(follow_up)
    if not reference:
        return
    expected = Path(reference)
    if not expected.is_absolute():
        expected = workspace / expected
    expected_key = os.path.normcase(os.path.abspath(str(expected)))
    actual_key = os.path.normcase(os.path.abspath(str(task_path)))
    if expected_key != actual_key:
        report.fail("--tasks does not match handoff follow-up task")
    else:
        report.ok("--tasks matches the handoff follow-up task")


def check_handoff_task_contract(handoff_path, task_path, report):
    try:
        handoff_text = handoff_path.read_text(encoding="utf-8")
        task_text = task_path.read_text(encoding="utf-8")
    except OSError as exc:
        report.fail("cannot compare handoff and task contract: " + str(exc))
        return
    handoff_role = plain_value(metadata_value(handoff_text, "下一角色"))
    task_role = plain_value(metadata_value(task_text, "下一角色"))
    if (handoff_role or task_role) and handoff_role != task_role:
        report.fail("next role differs between handoff and task")
    handoff_source = plain_value(metadata_value(handoff_text, "角色来源"))
    task_source = plain_value(metadata_value(task_text, "角色来源"))
    if (handoff_source or task_source) and handoff_source != task_source:
        report.fail("role source differs between handoff and task")

    handoff_end = metadata_value(handoff_text, "结束时间")
    task_end = metadata_value(task_text, "结束时间")
    deadline_active = any(
        value is not None and not is_none_value(value)
        for value in (handoff_end, task_end)
    )
    if deadline_active:
        if not handoff_end or not task_end:
            report.fail("deadline must be recorded in both handoff and task")
        elif plain_value(handoff_end) != plain_value(task_end):
            report.fail("ending time differs between handoff and task")
        handoff_wrapup = metadata_value(handoff_text, "收尾开始")
        task_wrapup = metadata_value(task_text, "收尾开始")
        if not handoff_wrapup or not task_wrapup:
            report.fail("wrap-up time must be recorded in both handoff and task")
        elif plain_value(handoff_wrapup) != plain_value(task_wrapup):
            report.fail("wrap-up time differs between handoff and task")
    report.ok("handoff and task relay contract compared")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", help="handoff, task, review request, or review result")
    parser.add_argument(
        "--workspace",
        default=".",
        help="root for relative paths and file anchors (default: current directory)",
    )
    parser.add_argument("--tasks", help="optional task file to validate with the document")
    args = parser.parse_args(argv)

    report = Report()
    workspace = Path(args.workspace)
    document = Path(args.document)

    print("=" * 70)
    print(document.name)
    print("=" * 70)
    document_kind = validate_document(document, workspace, report)

    task_kind = None
    task_path = None
    if args.tasks:
        task_path = Path(args.tasks)
        if task_path != document:
            print("=" * 70)
            print(task_path.name)
            print("=" * 70)
            task_kind = validate_document(task_path, workspace, report)
            if task_kind and task_kind != "task":
                report.fail("--tasks does not point to a task document")

    if document_kind == "result" and task_kind == "task":
        check_result_task_coverage(document, task_path, report)
    if document_kind == "handoff" and task_kind == "task":
        check_handoff_task_argument(document, task_path, workspace, report)
        check_handoff_task_contract(document, task_path, report)

    print("")
    print("FAILED" if report.failed else "PASSED")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
