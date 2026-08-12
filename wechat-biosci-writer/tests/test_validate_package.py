from __future__ import annotations

import base64
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_package import validate_package  # noqa: E402


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class ValidatePackageTests(unittest.TestCase):
    def make_package(
        self,
        parent: Path,
        name: str,
        image_count: int,
        include_source_url: bool = True,
    ) -> Path:
        package = parent / name
        imgs = package / "imgs"
        imgs.mkdir(parents=True)
        (package / "资料参考图").mkdir()
        (imgs / "cover.png").write_bytes(PNG_1X1)
        for index in range(1, image_count + 1):
            (imgs / f"figure-{index:02d}.png").write_bytes(PNG_1X1)

        source_line = 'sourceUrl: "https://example.org/source"\n' if include_source_url else ""
        markdown_images = "\n".join(
            f"![图 {index}｜测试图](imgs/figure-{index:02d}.png)"
            for index in range(1, image_count + 1)
        )
        (package / "公众号文章.md").write_text(
            "---\n"
            'title: "测试文章"\n'
            'description: "只用于验证发布包合同。"\n'
            'author: "共进化的十字路口"\n'
            'coverImage: "imgs/cover.png"\n'
            f"{source_line}"
            "---\n\n"
            "## 测试正文\n\n"
            f"{markdown_images}\n",
            encoding="utf-8",
        )

        html_images = "".join(
            f'<img src="imgs/figure-{index:02d}.png" alt="测试图 {index}">'
            for index in range(1, image_count + 1)
        )
        (package / "公众号文章.html").write_text(
            '<!doctype html><html lang="zh-CN"><head>'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta name="author" content="共进化的十字路口">'
            '<meta name="description" content="只用于验证发布包合同。">'
            '<title>测试文章</title></head><body>'
            f"{html_images}</body></html>",
            encoding="utf-8",
        )
        for filename in ("图片方案.md", "资料与证据.md", "发布前检查.md"):
            (package / filename).write_text("# 测试\n", encoding="utf-8")
        return package

    def test_quick_package_with_one_image_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package = self.make_package(Path(temp_dir), "快评包", image_count=1)
            result = validate_package(package)
        self.assertEqual("passed", result["status"], result["errors"])
        self.assertEqual(1, result["markdown_image_count"])
        self.assertEqual(1, result["html_image_count"])

    def test_deep_package_without_source_url_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package = self.make_package(
                Path(temp_dir), "深解包", image_count=2, include_source_url=False
            )
            result = validate_package(package)
        self.assertEqual("passed", result["status"], result["errors"])
        self.assertNotIn("sourceUrl", result["metadata"])
        self.assertEqual(2, result["markdown_image_count"])

    def test_remote_body_image_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            package = self.make_package(Path(temp_dir), "错误包", image_count=1)
            markdown_path = package / "公众号文章.md"
            markdown = markdown_path.read_text(encoding="utf-8")
            markdown_path.write_text(
                markdown.replace("imgs/figure-01.png", "https://example.org/figure.png"),
                encoding="utf-8",
            )
            result = validate_package(package)
        self.assertEqual("failed", result["status"])
        self.assertTrue(any("本地相对路径" in error for error in result["errors"]))

    def test_missing_package_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_package(Path(temp_dir) / "不存在")
        self.assertEqual("failed", result["status"])


if __name__ == "__main__":
    unittest.main()
