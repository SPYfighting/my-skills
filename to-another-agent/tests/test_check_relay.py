"""Tests for scripts/check_relay.py."""

import importlib.util
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "check_relay.py"
SPEC = importlib.util.spec_from_file_location("check_relay", SCRIPT)
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


HANDOFF = """# 项目交接

- 协议：to-another-agent/v2
- 交接类型：continue
- 更新时间：2026-11-11 12:00 +08:00
- 当前角色：负责者
- 当前目标：交接验证
- 状态基线：main@abc123
- 后续任务：`tasks/next-agent.md`

## 项目现场
可继续。

## 已完成与证据
- 建立记录。

## 进行中工作
无。

## 结果与验证
- 已运行检查。

## 远程任务
无活动远程任务。

## 决策、边界与风险
- 无额外风险。

## 接手入口
1. 验收任务。

## 下一位 agent 接手
> 请使用 `$to-another-agent` 接手当前项目。读取 `AGENT_HANDOFF.md` 和 `tasks/next-agent.md`，然后继续。
"""

TASKS = """# 下一位 agent 任务

- 协议：to-another-agent/v2
- 交接类型：continue

## 接手先验收

- [ ] T1 核验现场
  - 现场：结果文件
  - 疑点：尚未复核
  - 验收动作：重新运行检查
  - 完成判据：检查退出码为 0

## 待执行

- [ ] T2 完成任务
  - 输入：现有文件
  - 输出：最终产物
  - 完成判据：产物存在且可读

## 受阻

无。
"""

LEGACY_REQUEST = """# 审查请求：demo r1

## 1. 用户原始需求（逐字引用）

> 把这件事做完

## 2. 交付物

| 路径 | 说明 | 状态 |
|---|---|---|
| `target.txt` | demo | 完成 |

## 3. 关键决策

### 决策 1：选了甲方案

- 锚点：`target.txt:1-2`

## 4. 判断依据与证据等级

| 依据 | 性质 |
|---|---|
| 跑过了 | 实际验证过 |

## 5. 已验证与未验证

**已验证**
- 跑了 demo

## 6. 最不确定处

1. **也许错了** —— 锚点：`target.txt:2-3`
   如果这里错了：交付不成立

## 7. 明确不在范围内

- 没做乙
"""

LEGACY_RESULT = """# 审查结果：demo r1

- 结论：**通过**

## 1. 核对轨迹

- `target.txt:1-2`

## 2. 发现

### F1 `阻断·已核实` 有个错

- 位置：`target.txt:1-1`

## 3. 对“最不确定处”的逐条回应

| 问题 | 结论 |
|---|---|
| 也许错了 | 确认没问题 |

## 4. 盲区扫描

- 未发现问题

## 5. 未能核实的

- 无
"""


def v2_request(name, round_number=1, previous="无"):
    scope = "首轮：完成 demo。"
    if round_number > 1:
        scope = """变更：
- 修正问题 —— 锚点：`target.txt:1-2`

上一轮未闭合的发现：
- r1-F1 已修正 —— 锚点：`target.txt:1-2`"""
    return f"""# 审查请求：demo r{round_number}

- 协议：to-another-agent/v2
- 交接类型：review-request
- 日期：2026-11-11
- 工作区：测试目录
- 范围：target.txt
- 分支 / commit：main@abc123
- 任务文件：`tasks/next-agent.md`
- 上一轮：{previous}

## 0. 本轮范围

{scope}

## 1. 用户原始需求（逐字引用）

> 把这件事做完

## 2. 交付物

| 路径 | 说明 | 状态 |
|---|---|---|
| `target.txt` | demo | 完成 |

## 3. 关键决策

### 决策 1：选了甲方案

- 备选：乙方案
- 理由：验证结果更好
- 锚点：`target.txt:1-2`

## 4. 判断依据与证据等级

| 依据 | 性质 | 出处或验证方式 |
|---|---|---|
| 跑过了 | 实际验证过 | 测试命令 |

## 5. 已验证与未验证

**已验证**
- 跑了 demo

**未验证**
- 无

## 6. 最不确定处

1. **也许错了** —— 锚点：`target.txt:2-3`
   如果这里错了：交付不成立

## 7. 明确不在范围内

- 没做乙

## 8. 下一位 agent 接手

> 请使用 `$to-another-agent` 以审查方身份接手。读取 `{name}`，先验证请求和锚点，再只读核对实际产物。
"""


def v2_result(name, request_name, verdict="通过", findings="未发现阻断、重要或可选问题。"):
    return f"""# 审查结果：demo r1

- 协议：to-another-agent/v2
- 交接类型：review-result
- 日期：2026-11-11
- 对应请求：`{request_name}`
- 结论：**{verdict}**
- 一句话：完成审查

## 1. 核对轨迹

- `target.txt:1-2`

## 2. 发现

{findings}

## 3. 对“最不确定处”的逐条回应

| 问题 | 结论 | 依据 |
|---|---|---|
| 也许错了 | 确认没问题 | `target.txt:2-3` |

## 4. 盲区扫描

- 未发现问题

## 5. 上一轮未闭合发现

无。

## 6. 未能核实的

- 无

## 7. 额外提请注意

- 无

## 8. 下一位 agent 接手

> 请使用 `$to-another-agent` 以工作方身份处理 `{name}`。审查已经完成，请更新项目记录。
"""


def run(args):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = CHECKER.main(args)
    return code, buffer.getvalue()


class RelayValidatorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "target.txt").write_text("a\nb\nc\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, relative, body):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def validate(self, path, tasks=None):
        args = [str(path), "--workspace", str(self.root)]
        if tasks:
            args.extend(["--tasks", str(tasks)])
        return run(args)

    def test_valid_handoff_and_task_pass(self):
        handoff = self.write("AGENT_HANDOFF.md", HANDOFF)
        tasks = self.write("tasks/next-agent.md", TASKS)
        code, out = self.validate(handoff, tasks)
        self.assertEqual(code, 0, out)

    def test_handoff_without_tasks_or_remote_work_rejects_stale_prompt_clauses(self):
        body = HANDOFF.replace(
            "- 后续任务：`tasks/next-agent.md`",
            "- 后续任务：无",
        ).replace(
            "，然后继续。",
            "，并接管远程任务。",
        )
        handoff = self.write("AGENT_HANDOFF.md", body)
        code, out = self.validate(handoff)
        self.assertEqual(code, 1)
        self.assertIn("prompt references a task file but follow-up task is none", out)
        self.assertIn("prompt mentions remote takeover but no remote task is active", out)

    def test_handoff_tasks_argument_must_match_handoff_metadata(self):
        handoff = self.write("AGENT_HANDOFF.md", HANDOFF)
        self.write("tasks/next-agent.md", TASKS)
        other_tasks = self.write("tasks/other.md", TASKS)
        code, out = self.validate(handoff, other_tasks)
        self.assertEqual(code, 1)
        self.assertIn("--tasks does not match handoff follow-up task", out)

    def test_handoff_referenced_task_file_must_exist(self):
        handoff = self.write("AGENT_HANDOFF.md", HANDOFF)
        code, out = self.validate(handoff)
        self.assertEqual(code, 1)
        self.assertIn("referenced follow-up task file is missing", out)

    def test_unchecked_task_requires_completion_criterion(self):
        broken = TASKS.replace("  - 完成判据：产物存在且可读\n", "")
        tasks = self.write("tasks/next-agent.md", broken)
        code, out = self.validate(tasks)
        self.assertEqual(code, 1)
        self.assertIn("completion criterion", out)

    def test_acceptance_first_task_requires_validation_action(self):
        broken = TASKS.replace("  - 验收动作：重新运行检查\n", "")
        tasks = self.write("tasks/next-agent.md", broken)
        code, out = self.validate(tasks)
        self.assertEqual(code, 1)
        self.assertIn("validation action", out)

    def test_address_findings_is_a_valid_task_type(self):
        tasks = self.write(
            "tasks/next-agent.md",
            TASKS.replace("交接类型：continue", "交接类型：address-findings"),
        )
        code, out = self.validate(tasks)
        self.assertEqual(code, 0, out)

    def test_recognized_secret_is_rejected(self):
        secret = "gh" + "p_" + ("a" * 30)
        self.write("tasks/next-agent.md", TASKS)
        handoff = self.write(
            "AGENT_HANDOFF.md",
            HANDOFF.replace("可继续。", "令牌 " + secret),
        )
        code, out = self.validate(handoff)
        self.assertEqual(code, 1)
        self.assertIn("credential", out)

    def test_additional_high_confidence_secrets_are_rejected(self):
        secrets = {
            "github fine-grained": "github_" + "pat_" + ("a" * 40),
            "gitlab": "gl" + "pat-" + ("a" * 30),
            "slack": "xox" + "b-" + ("1" * 20) + "-" + ("a" * 20),
            "jwt": "eyJ" + ("a" * 20) + "." + ("b" * 20) + "." + ("c" * 20),
            "signed url": (
                "https://example.com/file?X-Amz-" + "Signature=" + ("a" * 64)
            ),
            "azure signed url": (
                "https://example.blob.core.windows.net/file?sv=2024-01-01&sp=r&sig="
                + ("a" * 44)
            ),
            "cookie": "Cookie: sessionid=" + ("a" * 32),
            "connection uri": (
                "postgresql://user:" + ("a" * 24) + "@db.example/test"
            ),
        }
        self.write("tasks/next-agent.md", TASKS)
        for label, secret in secrets.items():
            with self.subTest(label=label):
                handoff = self.write(
                    "AGENT_HANDOFF.md",
                    HANDOFF.replace("可继续。", "敏感值 " + secret),
                )
                code, out = self.validate(handoff)
                self.assertEqual(code, 1, out)
                self.assertIn("credential", out)

    def test_each_remote_task_requires_takeover_fields(self):
        active = """### 作业 A
- 任务标识：job-1
- 当前状态：运行
- 最近核查：2026-11-11 12:00 +08:00
- 日志或输出：logs/job-1.log
- 监控方式：查询调度器
- 接管动作：检查新日志
- 停止条件：正常完成

### 作业 B
- 任务标识：job-2
- 当前状态：排队
- 最近核查：2026-11-11 12:00 +08:00
- 日志或输出：logs/job-2.log
- 监控方式：查询调度器
- 停止条件：正常完成
"""
        self.write("tasks/next-agent.md", TASKS)
        handoff = self.write(
            "AGENT_HANDOFF.md",
            HANDOFF.replace("无活动远程任务。", active).replace(
                "，然后继续。",
                "，并接管其中记录的远程任务。",
            ),
        )
        code, out = self.validate(handoff)
        self.assertEqual(code, 1)
        self.assertIn("remote task 2", out)

    def test_active_remote_work_must_appear_in_takeover_prompt(self):
        active = """### 作业 A
- 任务标识：job-1
- 当前状态：运行
- 最近核查：2026-11-11 12:00 +08:00
- 日志或输出：logs/job-1.log
- 监控方式：查询调度器
- 接管动作：检查新日志
- 停止条件：正常完成
"""
        self.write("tasks/next-agent.md", TASKS)
        handoff = self.write(
            "AGENT_HANDOFF.md",
            HANDOFF.replace("无活动远程任务。", active),
        )
        code, out = self.validate(handoff)
        self.assertEqual(code, 1)
        self.assertIn("active remote work is missing", out)

    def test_existing_file_anchor_is_checked(self):
        self.write("tasks/next-agent.md", TASKS)
        handoff = self.write(
            "AGENT_HANDOFF.md",
            HANDOFF.replace("建立记录。", "建立记录；证据为 `target.txt:2`。"),
        )
        code, out = self.validate(handoff)
        self.assertEqual(code, 0, out)

    @unittest.skipUnless(os.name == "nt", "Windows absolute-path behavior")
    def test_windows_absolute_path_anchor_is_checked_end_to_end(self):
        self.write("tasks/next-agent.md", TASKS)
        target = self.write("windows-target.txt", "a\nb\nc\n")
        body = HANDOFF.replace(
            "建立记录。",
            "建立记录；证据为 `" + str(target) + ":2-3`。",
        )
        handoff = self.write("AGENT_HANDOFF.md", body)
        code, out = self.validate(handoff)
        self.assertEqual(code, 0, out)
        self.assertIn("1 file anchor(s) resolve", out)

    def test_valid_legacy_request_passes_with_warning(self):
        request = self.write("2026-11-11-demo-r1-请求.md", LEGACY_REQUEST)
        code, out = self.validate(request)
        self.assertEqual(code, 0, out)
        self.assertIn("legacy review request", out)

    def test_legacy_r2_shared_scope_section_remains_compatible(self):
        body = LEGACY_REQUEST.replace(
            "## 1. 用户原始需求（逐字引用）",
            "## 0. 本轮范围\n\n上一轮未闭合的发现：无。\n\n"
            "## 1. 用户原始需求（逐字引用）",
        )
        request = self.write("2026-11-11-demo-r2-请求.md", body)
        code, out = self.validate(request)
        self.assertEqual(code, 0, out)
        self.assertIn("legacy review request", out)

    def test_valid_legacy_result_passes_without_new_verdict_mapping(self):
        result = self.write("2026-11-11-demo-r1-审查.md", LEGACY_RESULT)
        code, out = self.validate(result)
        self.assertEqual(code, 0, out)
        self.assertIn("legacy review result", out)

    def test_bad_review_filename_fails(self):
        request = self.write("请求.md", LEGACY_REQUEST)
        code, out = self.validate(request)
        self.assertEqual(code, 1)
        self.assertIn("filename", out)

    def test_review_round_zero_is_rejected(self):
        name = "2026-11-11-demo-r0-请求.md"
        request = self.write(name, v2_request(name, round_number=0))
        code, out = self.validate(request)
        self.assertEqual(code, 1)
        self.assertIn("round must start at r1", out)

    def test_missing_request_section_fails(self):
        body = LEGACY_REQUEST.replace("## 7. 明确不在范围内", "## 7. 其他")
        request = self.write("2026-11-11-demo-r1-请求.md", body)
        code, out = self.validate(request)
        self.assertEqual(code, 1)
        self.assertIn("out of scope", out)

    def test_anchor_out_of_range_fails(self):
        body = LEGACY_REQUEST.replace("`target.txt:1-2`", "`target.txt:40-50`")
        request = self.write("2026-11-11-demo-r1-请求.md", body)
        code, out = self.validate(request)
        self.assertEqual(code, 1)
        self.assertIn("out of range", out)

    def test_missing_anchor_target_fails(self):
        body = LEGACY_REQUEST.replace("`target.txt:1-2`", "`gone.txt:1-2`")
        request = self.write("2026-11-11-demo-r1-请求.md", body)
        code, out = self.validate(request)
        self.assertEqual(code, 1)
        self.assertIn("anchor target missing", out)

    def test_request_without_uncertainty_fails(self):
        body = LEGACY_REQUEST.replace(
            "1. **也许错了** —— 锚点：`target.txt:2-3`\n"
            "   如果这里错了：交付不成立\n",
            "",
        )
        request = self.write("2026-11-11-demo-r1-请求.md", body)
        code, out = self.validate(request)
        self.assertEqual(code, 1)
        self.assertIn("uncertainty", out)

    def test_invalid_finding_label_fails(self):
        body = LEGACY_RESULT.replace("`阻断·已核实`", "`很严重·大概`")
        result = self.write("2026-11-11-demo-r1-审查.md", body)
        code, out = self.validate(result)
        self.assertEqual(code, 1)
        self.assertIn("invalid severity", out)

    def test_optional_findings_are_capped(self):
        extra = "".join(
            "\n### F%d `可选·已核实` 小建议\n\n- 位置：`target.txt:1-1`\n" % i
            for i in range(2, 9)
        )
        result = self.write("2026-11-11-demo-r1-审查.md", LEGACY_RESULT + extra)
        code, out = self.validate(result)
        self.assertEqual(code, 1)
        self.assertIn("exceed the cap", out)

    def test_unfilled_verdict_fails(self):
        body = LEGACY_RESULT.replace(
            "- 结论：**通过**",
            "- 结论：**通过 / 有条件通过 / 需返工**",
        )
        result = self.write("2026-11-11-demo-r1-审查.md", body)
        code, out = self.validate(result)
        self.assertEqual(code, 1)
        self.assertIn("invalid review verdict", out)

    def test_review_verdict_must_come_from_top_metadata(self):
        request_name = "2026-11-11-demo-r1-请求.md"
        result_name = "2026-11-11-demo-r1-审查.md"
        self.write(request_name, v2_request(request_name))
        body = v2_result(result_name, request_name).replace(
            "- 结论：**通过**\n",
            "",
        ).replace(
            "## 4. 盲区扫描\n\n- 未发现问题",
            "## 4. 盲区扫描\n\n- 结论：通过\n- 未发现问题",
        )
        result = self.write(result_name, body)
        code, out = self.validate(result)
        self.assertEqual(code, 1)
        self.assertIn("invalid review verdict", out)

    def test_valid_v2_request_passes(self):
        name = "2026-11-11-demo-r1-请求.md"
        request = self.write(name, v2_request(name))
        code, out = self.validate(request)
        self.assertEqual(code, 0, out)

    def test_fenced_code_markup_is_not_treated_as_a_placeholder(self):
        name = "2026-11-11-demo-r1-请求.md"
        body = v2_request(name).replace(
            "**已验证**\n- 跑了 demo",
            "**已验证**\n```xml\n<sample>value</sample>\n```\n- 跑了 demo",
        )
        request = self.write(name, body)
        code, out = self.validate(request)
        self.assertEqual(code, 0, out)

    def test_v2_signal_without_protocol_marker_fails(self):
        name = "2026-11-11-demo-r1-请求.md"
        body = v2_request(name).replace(
            "- 协议：to-another-agent/v2\n",
            "",
        ).replace(
            "## 8. 下一位 agent 接手\n\n"
            f"> 请使用 `$to-another-agent` 以审查方身份接手。读取 `{name}`，"
            "先验证请求和锚点，再只读核对实际产物。\n",
            "",
        )
        request = self.write(name, body)
        code, out = self.validate(request)
        self.assertEqual(code, 1)
        self.assertIn("protocol marker", out)

    def test_v2_request_requires_next_agent_prompt(self):
        name = "2026-11-11-demo-r1-请求.md"
        body = v2_request(name).replace("## 8. 下一位 agent 接手", "## 8. 其他")
        request = self.write(name, body)
        code, out = self.validate(request)
        self.assertEqual(code, 1)
        self.assertIn("next-agent prompt", out)

    def test_v2_request_requires_each_decision_to_have_an_anchor(self):
        name = "2026-11-11-demo-r1-请求.md"
        body = v2_request(name).replace(
            "- 锚点：`target.txt:1-2`\n",
            "",
            1,
        )
        request = self.write(name, body)
        code, out = self.validate(request)
        self.assertEqual(code, 1)
        self.assertIn("decision 1 needs an anchor or rerunnable command", out)

    def test_v2_request_requires_each_uncertainty_to_have_an_anchor(self):
        name = "2026-11-11-demo-r1-请求.md"
        body = v2_request(name).replace(
            "1. **也许错了** —— 锚点：`target.txt:2-3`",
            "1. **也许错了**",
        )
        request = self.write(name, body)
        code, out = self.validate(request)
        self.assertEqual(code, 1)
        self.assertIn("uncertainty 1 needs an anchor or rerunnable command", out)

    def test_v2_prompt_must_name_source_document(self):
        name = "2026-11-11-demo-r1-请求.md"
        body = v2_request(name).replace(name, "another-request.md")
        request = self.write(name, body)
        code, out = self.validate(request)
        self.assertEqual(code, 1)
        self.assertIn("source document", out)

    def test_valid_v2_result_passes(self):
        request_name = "2026-11-11-demo-r1-请求.md"
        result_name = "2026-11-11-demo-r1-审查.md"
        self.write(request_name, v2_request(request_name))
        result = self.write(result_name, v2_result(result_name, request_name))
        code, out = self.validate(result)
        self.assertEqual(code, 0, out)

    def test_result_rejects_corresponding_request_for_another_task(self):
        request_name = "2026-11-11-other-r1-请求.md"
        result_name = "2026-11-11-demo-r1-审查.md"
        self.write(request_name, v2_request(request_name))
        result = self.write(result_name, v2_result(result_name, request_name))
        code, out = self.validate(result)
        self.assertEqual(code, 1)
        self.assertIn("task names do not match", out)

    def test_v2_result_requires_next_agent_prompt(self):
        request_name = "2026-11-11-demo-r1-请求.md"
        result_name = "2026-11-11-demo-r1-审查.md"
        self.write(request_name, v2_request(request_name))
        body = v2_result(result_name, request_name).replace(
            "## 8. 下一位 agent 接手",
            "## 8. 其他",
        )
        result = self.write(result_name, body)
        code, out = self.validate(result)
        self.assertEqual(code, 1)
        self.assertIn("next-agent prompt", out)

    def test_pass_verdict_rejects_important_finding(self):
        request_name = "2026-11-11-demo-r1-请求.md"
        result_name = "2026-11-11-demo-r1-审查.md"
        self.write(request_name, v2_request(request_name))
        finding = """### F1 `重要·已核实` 有风险

- 位置：`target.txt:1-1`
- 问题：风险
- 证据：实际内容
- 建议动作：修正
"""
        result = self.write(
            result_name,
            v2_result(result_name, request_name, "通过", finding),
        )
        code, out = self.validate(result)
        self.assertEqual(code, 1)
        self.assertIn("verdict conflicts", out)

    def test_v2_finding_requires_its_own_evidence_fields(self):
        request_name = "2026-11-11-demo-r1-请求.md"
        result_name = "2026-11-11-demo-r1-审查.md"
        self.write(request_name, v2_request(request_name))
        finding = "### F1 `重要·已核实` 只有标题\n"
        result = self.write(
            result_name,
            v2_result(result_name, request_name, "有条件通过", finding),
        )
        code, out = self.validate(result)
        self.assertEqual(code, 1)
        self.assertIn("F1 missing required field: position", out)
        self.assertIn("F1 missing required field: evidence", out)

    def test_v2_finding_ids_must_be_unique(self):
        request_name = "2026-11-11-demo-r1-请求.md"
        result_name = "2026-11-11-demo-r1-审查.md"
        self.write(request_name, v2_request(request_name))
        one = """### F1 `重要·已核实` 风险

- 位置：`target.txt:1-1`
- 问题：风险
- 证据：实际内容
- 建议动作：修正
"""
        result = self.write(
            result_name,
            v2_result(result_name, request_name, "有条件通过", one + "\n" + one),
        )
        code, out = self.validate(result)
        self.assertEqual(code, 1)
        self.assertIn("duplicate finding id: F1", out)

    def test_conditional_verdict_rejects_blocker(self):
        request_name = "2026-11-11-demo-r1-请求.md"
        result_name = "2026-11-11-demo-r1-审查.md"
        self.write(request_name, v2_request(request_name))
        finding = """### F1 `阻断·存疑` 可能不成立

- 位置：`target.txt:1-1`
- 问题：风险
- 为何存疑：缺证据
- 建议动作：查证
"""
        result = self.write(
            result_name,
            v2_result(result_name, request_name, "有条件通过", finding),
        )
        code, out = self.validate(result)
        self.assertEqual(code, 1)
        self.assertIn("verdict conflicts", out)

    def test_rework_verdict_requires_blocker(self):
        request_name = "2026-11-11-demo-r1-请求.md"
        result_name = "2026-11-11-demo-r1-审查.md"
        self.write(request_name, v2_request(request_name))
        finding = """### F1 `重要·已核实` 有风险

- 位置：`target.txt:1-1`
- 问题：风险
- 证据：实际内容
- 建议动作：修正
"""
        result = self.write(
            result_name,
            v2_result(result_name, request_name, "需返工", finding),
        )
        code, out = self.validate(result)
        self.assertEqual(code, 1)
        self.assertIn("verdict conflicts", out)

    def test_result_with_tasks_requires_open_findings_in_task_items(self):
        request_name = "2026-11-11-demo-r1-请求.md"
        result_name = "2026-11-11-demo-r1-审查.md"
        self.write(request_name, v2_request(request_name))
        finding = """### F1 `重要·已核实` 需要落实

- 位置：`target.txt:1-1`
- 问题：存在实质风险
- 证据：实际内容
- 建议动作：写入任务文件
"""
        result = self.write(
            result_name,
            v2_result(result_name, request_name, "有条件通过", finding),
        )
        tasks = self.write(
            "tasks/next-agent.md",
            TASKS.replace("交接类型：continue", "交接类型：address-findings"),
        )
        code, out = self.validate(result, tasks)
        self.assertEqual(code, 1)
        self.assertIn("F1 is not represented in the task file", out)

    def test_result_tasks_reject_finding_id_from_another_round(self):
        request_name = "2026-11-11-demo-r1-请求.md"
        result_name = "2026-11-11-demo-r1-审查.md"
        self.write(request_name, v2_request(request_name))
        finding = """### F1 `重要·已核实` 需要落实

- 位置：`target.txt:1-1`
- 问题：存在实质风险
- 证据：实际内容
- 建议动作：写入任务文件
"""
        result = self.write(
            result_name,
            v2_result(result_name, request_name, "有条件通过", finding),
        )
        wrong_round_tasks = TASKS.replace(
            "交接类型：continue",
            "交接类型：address-findings",
        ).replace(
            "- [ ] T2 完成任务",
            "- [ ] r2-F1 错误轮次",
        )
        tasks = self.write("tasks/next-agent.md", wrong_round_tasks)
        code, out = self.validate(result, tasks)
        self.assertEqual(code, 1)
        self.assertIn("expected r1-F1", out)

    def test_completed_finding_tasks_allow_task_type_to_return_to_continue(self):
        request_name = "2026-11-11-demo-r1-请求.md"
        result_name = "2026-11-11-demo-r1-审查.md"
        self.write(request_name, v2_request(request_name))
        finding = """### F1 `重要·已核实` 已处理

- 位置：`target.txt:1-1`
- 问题：存在实质风险
- 证据：实际内容
- 建议动作：修正并验证
"""
        result = self.write(
            result_name,
            v2_result(result_name, request_name, "有条件通过", finding),
        )
        closed_tasks = TASKS.replace(
            "- [ ] T2 完成任务",
            "- [x] r1-F1 已修正并验证",
        )
        tasks = self.write("tasks/next-agent.md", closed_tasks)
        code, out = self.validate(result, tasks)
        self.assertEqual(code, 0, out)

    def test_r2_request_requires_previous_result(self):
        name = "2026-11-11-demo-r2-请求.md"
        request = self.write(name, v2_request(name, round_number=2))
        code, out = self.validate(request)
        self.assertEqual(code, 1)
        self.assertIn("previous result", out)

    def test_valid_r2_request_passes(self):
        previous_name = "2026-11-10-demo-r1-审查.md"
        self.write(previous_name, LEGACY_RESULT)
        name = "2026-11-11-demo-r2-请求.md"
        request = self.write(
            name,
            v2_request(name, round_number=2, previous=f"`{previous_name}`"),
        )
        code, out = self.validate(request)
        self.assertEqual(code, 0, out)

    def test_r2_request_rejects_previous_result_for_another_task(self):
        previous_name = "2026-11-10-other-r1-审查.md"
        self.write(previous_name, LEGACY_RESULT)
        name = "2026-11-11-demo-r2-请求.md"
        request = self.write(
            name,
            v2_request(name, round_number=2, previous=f"`{previous_name}`"),
        )
        code, out = self.validate(request)
        self.assertEqual(code, 1)
        self.assertIn("previous result must be the same task", out)

    def test_r2_request_rejects_result_from_the_wrong_round(self):
        previous_name = "2026-11-10-demo-r2-审查.md"
        self.write(previous_name, LEGACY_RESULT)
        name = "2026-11-11-demo-r2-请求.md"
        request = self.write(
            name,
            v2_request(name, round_number=2, previous=f"`{previous_name}`"),
        )
        code, out = self.validate(request)
        self.assertEqual(code, 1)
        self.assertIn("previous result must be from round rN-1", out)

    def test_review_fix_rereview_loop_passes(self):
        request_name = "2026-11-10-demo-r1-请求.md"
        result_name = "2026-11-10-demo-r1-审查.md"
        request = self.write(request_name, v2_request(request_name))
        code, out = self.validate(request)
        self.assertEqual(code, 0, out)

        finding = """### F1 `重要·已核实` 需要修正

- 位置：`target.txt:1-1`
- 问题：存在实质风险
- 证据：实际内容
- 建议动作：修正并复审
"""
        result = self.write(
            result_name,
            v2_result(result_name, request_name, "有条件通过", finding),
        )
        code, out = self.validate(result)
        self.assertEqual(code, 0, out)

        address_tasks = TASKS.replace(
            "交接类型：continue",
            "交接类型：address-findings",
        ).replace(
            "- [ ] T2 完成任务",
            "- [ ] r1-F1 修正重要发现",
        )
        tasks = self.write("tasks/next-agent.md", address_tasks)
        code, out = self.validate(tasks)
        self.assertEqual(code, 0, out)
        code, out = self.validate(result, tasks)
        self.assertEqual(code, 0, out)

        next_name = "2026-11-11-demo-r2-请求.md"
        next_request = self.write(
            next_name,
            v2_request(next_name, round_number=2, previous=f"`{result_name}`"),
        )
        code, out = self.validate(next_request)
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
