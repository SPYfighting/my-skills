"""Tests for scripts/check_review_doc.py."""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_review_doc as checker  # noqa: E402


REQUEST_BODY = """# 审查请求：demo r1

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
   如果这里错了：完蛋

## 7. 明确不在范围内

- 没做乙
"""

RESULT_BODY = """# 审查结果：demo r1

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


def run(doc_path, workspace):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = checker.main([str(doc_path), "--workspace", str(workspace)])
    return code, buffer.getvalue()


class CheckReviewDocTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "target.txt").write_text("a\nb\nc\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, body):
        path = self.root / name
        path.write_text(body, encoding="utf-8")
        return path

    def test_valid_request_passes(self):
        doc = self.write("2026-08-19-demo-r1-请求.md", REQUEST_BODY)
        code, out = run(doc, self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("PASSED", out)

    def test_valid_result_passes(self):
        doc = self.write("2026-08-19-demo-r1-审查.md", RESULT_BODY)
        code, out = run(doc, self.root)
        self.assertEqual(code, 0, out)

    def test_bad_filename_fails(self):
        doc = self.write("请求.md", REQUEST_BODY)
        code, out = run(doc, self.root)
        self.assertEqual(code, 1)
        self.assertIn("filename does not follow", out)

    def test_missing_section_fails(self):
        body = REQUEST_BODY.replace("## 7. 明确不在范围内", "## 7. 别的东西")
        doc = self.write("2026-08-19-demo-r1-请求.md", body)
        code, out = run(doc, self.root)
        self.assertEqual(code, 1)
        self.assertIn("out of scope", out)

    def test_anchor_out_of_range_fails(self):
        body = REQUEST_BODY.replace("`target.txt:1-2`", "`target.txt:40-50`")
        doc = self.write("2026-08-19-demo-r1-请求.md", body)
        code, out = run(doc, self.root)
        self.assertEqual(code, 1)
        self.assertIn("out of range", out)

    def test_missing_anchor_target_fails(self):
        body = REQUEST_BODY.replace("`target.txt:1-2`", "`gone.txt:1-2`")
        doc = self.write("2026-08-19-demo-r1-请求.md", body)
        code, out = run(doc, self.root)
        self.assertEqual(code, 1)
        self.assertIn("anchor target missing", out)

    def test_request_without_uncertainty_fails(self):
        body = REQUEST_BODY.replace(
            "1. **也许错了** —— 锚点：`target.txt:2-3`\n   如果这里错了：完蛋\n", ""
        )
        doc = self.write("2026-08-19-demo-r1-请求.md", body)
        code, out = run(doc, self.root)
        self.assertEqual(code, 1)
        self.assertIn("at least one is required", out)

    def test_invalid_finding_label_fails(self):
        body = RESULT_BODY.replace("`阻断·已核实`", "`很严重·大概`")
        doc = self.write("2026-08-19-demo-r1-审查.md", body)
        code, out = run(doc, self.root)
        self.assertEqual(code, 1)
        self.assertIn("invalid label", out)

    def test_optional_findings_capped(self):
        extra = "".join(
            "\n### F%d `可选·已核实` 小建议\n\n- 位置：`target.txt:1-1`\n" % i
            for i in range(2, 9)
        )
        doc = self.write("2026-08-19-demo-r1-审查.md", RESULT_BODY + extra)
        code, out = run(doc, self.root)
        self.assertEqual(code, 1)
        self.assertIn("exceed the cap", out)

    def test_unfilled_verdict_fails(self):
        body = RESULT_BODY.replace(
            "- 结论：**通过**", "- 结论：**通过 / 有条件通过 / 需返工**"
        )
        doc = self.write("2026-08-19-demo-r1-审查.md", body)
        code, out = run(doc, self.root)
        self.assertEqual(code, 1)
        self.assertIn("pick one", out)


if __name__ == "__main__":
    unittest.main()
