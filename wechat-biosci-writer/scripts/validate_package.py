#!/usr/bin/env python3
"""Validate a wechat-biosci-writer publication package without network access."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


REQUIRED_FILES = (
    "公众号文章.md",
    "公众号文章.html",
    "图片方案.md",
    "资料与证据.md",
    "发布前检查.md",
)
REQUIRED_METADATA = ("title", "description", "author", "coverImage")
FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+['\"].*?['\"])?\s*\)")
HTML_IMAGE_RE = re.compile(r"<img\b[^>]*\bsrc\s*=\s*(['\"])(.*?)\1", re.IGNORECASE | re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str | None]:
    match = FRONTMATTER_RE.search(text)
    if not match:
        return {}, "公众号文章.md 缺少位于文件开头的 YAML Frontmatter"

    metadata: dict[str, str] = {}
    for line_number, raw_line in enumerate(match.group(1).splitlines(), start=2):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            return {}, f"Frontmatter 第 {line_number} 行不是 key: value 格式"
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        metadata[key] = value
    return metadata, None


def remove_fenced_code(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return re.sub(r"~~~.*?~~~", "", text, flags=re.DOTALL)


def resolve_local_reference(root: Path, reference: str) -> tuple[Path | None, str | None]:
    reference = unquote(reference.strip().strip("<>"))
    parsed = urlparse(reference)
    if parsed.scheme or reference.startswith("//"):
        return None, "发布正文图片必须使用 imgs/ 下的本地相对路径"
    clean_reference = reference.split("#", 1)[0].split("?", 1)[0]
    candidate = (root / clean_reference).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None, "图片路径越出文章发布包"
    return candidate, None


def validate_local_images(
    root: Path,
    references: list[str],
    origin: str,
    errors: list[str],
) -> list[str]:
    valid: list[str] = []
    for reference in references:
        candidate, problem = resolve_local_reference(root, reference)
        if problem:
            errors.append(f"{origin}: {reference}：{problem}")
            continue
        assert candidate is not None
        try:
            relative = candidate.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{origin}: {reference}：图片路径越出文章发布包")
            continue
        if not relative.parts or relative.parts[0].lower() != "imgs":
            errors.append(f"{origin}: {reference}：发布图片只能引用 imgs/ 目录")
            continue
        if not candidate.is_file() or candidate.stat().st_size == 0:
            errors.append(f"{origin}: {reference}：图片不存在或为空")
            continue
        valid.append(relative.as_posix())
    return valid


def html_has_meta(html: str, name: str) -> bool:
    patterns = (
        rf"<meta\b[^>]*\bname\s*=\s*(['\"]){re.escape(name)}\1[^>]*\bcontent\s*=\s*(['\"])(?:(?!\2).)+\2[^>]*>",
        rf"<meta\b[^>]*\bcontent\s*=\s*(['\"])(?:(?!\1).)+\1[^>]*\bname\s*=\s*(['\"]){re.escape(name)}\2[^>]*>",
    )
    return any(re.search(pattern, html, re.IGNORECASE | re.DOTALL) for pattern in patterns)


def validate_package(root: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []

    if not root.is_dir():
        errors.append(f"文章发布包不存在或不是目录：{root}")
        return {"status": "failed", "errors": errors, "warnings": warnings}

    for filename in REQUIRED_FILES:
        path = root / filename
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"缺少必需文件或文件为空：{filename}")

    reference_dir = root / "资料参考图"
    if not reference_dir.is_dir():
        errors.append("缺少目录：资料参考图")

    markdown_path = root / "公众号文章.md"
    html_path = root / "公众号文章.html"
    metadata: dict[str, str] = {}
    markdown_images: list[str] = []
    html_images: list[str] = []

    if markdown_path.is_file():
        markdown = markdown_path.read_text(encoding="utf-8-sig")
        metadata, frontmatter_error = parse_frontmatter(markdown)
        if frontmatter_error:
            errors.append(frontmatter_error)
        for field in REQUIRED_METADATA:
            if not metadata.get(field, "").strip():
                errors.append(f"Frontmatter 缺少必填字段或值为空：{field}")

        description = metadata.get("description", "")
        if len(description) > 120:
            errors.append(f"description 超过 120 个字符：当前 {len(description)} 个字符")

        cover_reference = metadata.get("coverImage", "")
        if cover_reference and cover_reference.replace("\\", "/") != "imgs/cover.png":
            errors.append("coverImage 必须为 imgs/cover.png")
        if cover_reference:
            validate_local_images(root, [cover_reference], "Frontmatter coverImage", errors)

        source_url = metadata.get("sourceUrl", "")
        if source_url and urlparse(source_url).scheme not in {"http", "https"}:
            errors.append("sourceUrl 必须是 http 或 https 权威入口")

        image_references = [match.group(1) for match in MARKDOWN_IMAGE_RE.finditer(remove_fenced_code(markdown))]
        markdown_images = validate_local_images(root, image_references, "公众号文章.md", errors)

    if html_path.is_file():
        html = html_path.read_text(encoding="utf-8-sig")
        if not re.search(r"<html\b[^>]*\blang\s*=\s*(['\"])zh-CN\1", html, re.IGNORECASE):
            errors.append('公众号文章.html 缺少 lang="zh-CN"')
        if not re.search(r"<meta\b[^>]*\bname\s*=\s*(['\"])viewport\1", html, re.IGNORECASE):
            errors.append("公众号文章.html 缺少移动端 viewport")
        if not re.search(r"<title\b[^>]*>\s*[^<\s].*?</title>", html, re.IGNORECASE | re.DOTALL):
            errors.append("公众号文章.html 缺少非空 title")
        for name in ("author", "description"):
            if not html_has_meta(html, name):
                errors.append(f"公众号文章.html 缺少非空 meta name=\"{name}\"")
        image_references = [match.group(2) for match in HTML_IMAGE_RE.finditer(html)]
        html_images = validate_local_images(root, image_references, "公众号文章.html", errors)
        if re.search(r"<(?:script|link)\b[^>]*(?:src|href)\s*=\s*(['\"])(?:https?:)?//", html, re.IGNORECASE):
            errors.append("公众号文章.html 不得依赖远程脚本或样式")

    cover_path = root / "imgs" / "cover.png"
    if not cover_path.is_file() or cover_path.stat().st_size == 0:
        errors.append("缺少非空封面：imgs/cover.png")

    if markdown_images and html_images and set(markdown_images) != set(html_images):
        warnings.append("Markdown 与 HTML 引用的正文图片集合不同，请人工确认预览是否完整")

    status = "passed" if not errors else "failed"
    return {
        "status": status,
        "package": str(root.resolve()),
        "metadata": metadata,
        "markdown_image_count": len(markdown_images),
        "html_image_count": len(html_images),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="验证科研微信公众号文章发布包")
    parser.add_argument("package", type=Path, help="文章发布包目录")
    args = parser.parse_args()

    result = validate_package(args.package)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    for issue in result["errors"]:
        print(f"错误：{issue}", file=sys.stderr)
    for issue in result["warnings"]:
        print(f"警告：{issue}", file=sys.stderr)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
