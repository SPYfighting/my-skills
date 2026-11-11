import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "check_handoff.py"
SPEC = importlib.util.spec_from_file_location("check_handoff", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


HANDOFF = """# 项目交接

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
"""

TASKS = """# 下一位 agent 任务

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


class HandoffValidatorTests(unittest.TestCase):
    def write_fixture(self, root, tasks=TASKS):
        root = Path(root)
        handoff = root / "AGENT_HANDOFF.md"
        task_path = root / "tasks" / "next-agent.md"
        task_path.parent.mkdir()
        handoff.write_text(HANDOFF, encoding="utf-8")
        task_path.write_text(tasks, encoding="utf-8")
        return handoff, task_path

    def run_validator(self, directory, handoff, tasks):
        return MODULE.main([
            "--handoff", str(handoff),
            "--tasks", str(tasks),
            "--workspace", directory,
        ])

    def test_valid_fallback_documents_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            handoff, tasks = self.write_fixture(directory)
            self.assertEqual(self.run_validator(directory, handoff, tasks), 0)

    def test_unchecked_task_requires_completion_criterion(self):
        broken = TASKS.replace("  - 完成判据：产物存在且可读\n", "")
        with tempfile.TemporaryDirectory() as directory:
            handoff, tasks = self.write_fixture(directory, broken)
            self.assertEqual(self.run_validator(directory, handoff, tasks), 1)

    def test_acceptance_first_task_requires_validation_action(self):
        broken = TASKS.replace("  - 验收动作：重新运行检查\n", "")
        with tempfile.TemporaryDirectory() as directory:
            handoff, tasks = self.write_fixture(directory, broken)
            self.assertEqual(self.run_validator(directory, handoff, tasks), 1)

    def test_recognized_secret_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            handoff, tasks = self.write_fixture(directory)
            handoff.write_text(
                HANDOFF.replace(
                    "可继续。",
                    "令牌 " + "gh" + "p_" + ("a" * 30),
                ),
                encoding="utf-8",
            )
            self.assertEqual(self.run_validator(directory, handoff, tasks), 1)

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
        with tempfile.TemporaryDirectory() as directory:
            handoff, tasks = self.write_fixture(directory)
            handoff.write_text(
                HANDOFF.replace("无活动远程任务。", active),
                encoding="utf-8",
            )
            self.assertEqual(self.run_validator(directory, handoff, tasks), 1)

    def test_existing_file_anchor_is_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            handoff, tasks = self.write_fixture(directory)
            evidence = Path(directory) / "result.txt"
            evidence.write_text("line one\nline two\n", encoding="utf-8")
            handoff.write_text(
                HANDOFF.replace("建立记录。", "建立记录；证据为 `result.txt:2`。"),
                encoding="utf-8",
            )
            self.assertEqual(self.run_validator(directory, handoff, tasks), 0)


if __name__ == "__main__":
    unittest.main()
