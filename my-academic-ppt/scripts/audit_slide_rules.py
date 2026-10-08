#!/usr/bin/env python3
"""Read-only native slide text audit; visual and semantic review remain required."""

import importlib.util
import json
from pathlib import Path
import re
import string
import sys
import unicodedata


_SPEC = importlib.util.spec_from_file_location(
    "_slide_rules_package", Path(__file__).with_name("audit_pptx.py"))
PACKAGE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(PACKAGE)
P_NS, A_NS = PACKAGE.P_NS, PACKAGE.A_NS
DEFAULT_CJK_FONT = "Microsoft YaHei"
DEFAULT_LATIN_FONT = "Times New Roman"
DEFENSIVE_PATTERNS = (
    r"仅供参考", r"仅作(?:展示|示意|演示|参考)", r"仅用于(?:展示|示意|演示)",
    r"不构成(?:任何)?(?:建议|承诺|保证|结论|证据)", r"以实际(?:情况|结果)?为准",
    r"实际(?:结果|效果)可能(?:有所)?(?:不同|差异)",
)
LIMITATIONS = [
    "Only native DrawingML text is inspected; there is no OCR of pictures, "
    "rendering, or interpretation of equations, embedded objects, or chart caches.",
    "High-confidence phrases are review candidates, not a semantic classifier. "
    "Unmatched defensive text can remain; manual review of every slide is required.",
    "Scientific conditions, prediction identity, sample sizes, and required "
    "attribution are not automatically classified as defensive copy.",
    "Font checks resolve run, paragraph, and local text-body defaults only. "
    "Unresolved theme/master/layout inheritance is needs_review, never assumed compliant.",
    "Font declarations do not verify installed fonts, glyph coverage, or renderer substitution.",
    "ASCII punctuation follows the Latin font policy. CJK punctuation, curly quotes "
    "U+2018-U+201F, and middle dot U+00B7 follow the CJK policy used by this reference "
    "library. Quote language is not inferred. Other symbols/scripts need manual review; "
    "scientific symbol and equation font exceptions are not automatically rejected.",
    "Native slide text includes footer and other placeholders. Layout/master static "
    "text is scanned unless disabled; inherited placeholders and conditional visibility "
    "are needs_review. Notes are excluded.",
    "Group transforms, clipping, alternate content, animation, and overlaps are not "
    "rendered. Position is the local XML transform, not a guaranteed visible bounding box.",
]


def children(element, namespaces, name):
    return [child for child in element if PACKAGE.is_tag(child, namespaces, name)]


def first(element, namespaces, name):
    return next((item for item in element.iter()
                 if PACKAGE.is_tag(item, namespaces, name)), None)


def font_key(value):
    value = " ".join((value or "").casefold().split())
    return "microsoft yahei" if value == "微软雅黑" else value


def character_script(char):
    number = ord(char)
    if char.isdecimal() or char in string.punctuation:
        return "latin"
    if (0x2E80 <= number <= 0x9FFF or 0xAC00 <= number <= 0xD7AF or
            0xF900 <= number <= 0xFAFF or 0x20000 <= number <= 0x323AF or
            0xFF01 <= number <= 0xFF60 or 0x2018 <= number <= 0x201F or number == 0xB7):
        return "cjk"
    if "LATIN" in unicodedata.name(char, ""):
        return "latin"
    return None


def script_classes(text):
    return sorted({value for char in text if (value := character_script(char)) is not None})


def properties_font(properties, script):
    if properties is None:
        return None
    name = "ea" if script == "cjk" else "latin"
    nodes = children(properties, A_NS, name)
    return nodes[0].get("typeface") if nodes else None


def run_records(shape):
    records = []
    # Tables have one text body per cell. Each keeps its own local defaults.
    bodies = [node for node in shape.iter()
              if PACKAGE.tag_parts(node.tag)[1] == "txBody" and
              PACKAGE.tag_parts(node.tag)[0] in A_NS | P_NS]
    for body_index, body in enumerate(bodies):
        lists = children(body, A_NS, "lstStyle")
        for para_index, para in enumerate(children(body, A_NS, "p")):
            pprs = children(para, A_NS, "pPr")
            ppr = pprs[0] if pprs else None
            level = ppr.get("lvl", "0") if ppr is not None else "0"
            defaults = []
            if ppr is not None:
                defaults += [(node, "paragraph") for node in children(ppr, A_NS, "defRPr")]
            if lists:
                level_name = "lvl" + str(int(level) + 1) + "pPr" if level.isdigit() else ""
                for kind in (level_name, "defPPr"):
                    for item in children(lists[0], A_NS, kind):
                        defaults += [(node, "text_body") for node in children(item, A_NS, "defRPr")]
            for item in para:
                if not (PACKAGE.is_tag(item, A_NS, "r") or PACKAGE.is_tag(item, A_NS, "fld")):
                    continue
                text = "".join(node.text or "" for node in children(item, A_NS, "t"))
                if not text:
                    continue
                rprs = children(item, A_NS, "rPr")
                chain = [(node, "run") for node in rprs] + defaults
                fonts = {}
                for script in script_classes(text):
                    value, source = None, "unresolved_inheritance"
                    for props, origin in chain:
                        candidate = properties_font(props, script)
                        if candidate:
                            value, source = candidate, origin
                            break
                    fonts[script] = {"typeface": value, "source": source,
                                     "resolved": bool(value and not value.startswith("+"))}
                size = next((props.get("sz") for props, _ in chain if props.get("sz")), None)
                records.append({"body": body_index, "paragraph": para_index,
                                "text": text, "fonts": fonts, "size_hundredths_pt": size,
                                "unclassified_characters": sorted({char for char in text
                                    if not char.isspace() and character_script(char) is None})})
    return records


def shape_text(records):
    paragraphs = []
    previous = None
    for record in records:
        key = (record["body"], record["paragraph"])
        if key != previous:
            paragraphs.append("")
        paragraphs[-1] += record["text"]
        previous = key
    return "\n".join(paragraphs)


def position(shape, grouped):
    node = first(shape, A_NS | P_NS, "xfrm")
    if node is None:
        return {"coordinate_space": "unresolved_inheritance", "grouped": grouped}
    output = {"coordinate_space": "local_emu", "grouped": grouped,
              "rotation": node.get("rot", "0")}
    for name in ("off", "ext"):
        items = children(node, A_NS, name)
        if items:
            output.update(items[0].attrib)
    return output


def native_shapes(root):
    def visit(node, grouped=False, alternate=False):
        local = PACKAGE.tag_parts(node.tag)[1]
        alternate = alternate or local == "AlternateContent"
        if PACKAGE.is_tag(node, P_NS, "sp") or PACKAGE.is_tag(node, P_NS, "graphicFrame"):
            yield node, grouped, alternate
            return
        for child in node:
            yield from visit(child, grouped or PACKAGE.is_tag(node, P_NS, "grpSp"), alternate)
    yield from visit(root)


def is_false(value):
    return str(value).lower() in {"0", "false", "off"}


def audit_slide_rules(path, cjk_font=DEFAULT_CJK_FONT, latin_font=DEFAULT_LATIN_FONT):
    package = PACKAGE.Auditor(path)
    structure = package.run()
    report = {"schema_version": 1, "file": Path(path).name, "status": "pass",
              "font_policy": {"cjk": cjk_font, "latin": latin_font},
              "slide_count": structure["slide_count"], "slides": [], "issues": [],
              "semantic_review_required": True, "visual_review_required": True,
              "limitations": LIMITATIONS.copy()}

    def issue(code, message, severity="needs_review", **context):
        report["issues"].append(dict(code=code, message=message, severity=severity, **context))

    for item in structure["issues"]:
        if item["severity"] == "error":
            issue("package_" + item["code"], item["message"], "error",
                  **{k: v for k, v in item.items() if k in {"part", "slide"}})

    def related(source, kind, slide_number):
        values = [r for r in package.relationships.get(source, {}).values() if r["kind"] == kind]
        if len(values) > 1:
            issue("ambiguous_inherited_part", "Multiple " + kind + " relationships", slide=slide_number, part=source)
        valid = [r["resolved"] for r in values if not r["external"] and r["resolved"] in package.xml]
        return valid[:1]

    for slide in structure["slides"]:
        number, part = slide["number"], slide["part"]
        root = package.xml[part]
        layers = [(part, "slide", "visible")]
        for layout in related(part, "slideLayout", number):
            layers.append((layout, "layout", "visible"))
            layout_root = package.xml[layout]
            if not is_false(root.get("showMasterSp", "1")) and not is_false(layout_root.get("showMasterSp", "1")):
                layers += [(master, "master", "visible")
                           for master in related(layout, "slideMaster", number)]
        slide_report = {"number": number, "part": part, "shapes": [], "scanned_layers": []}
        for layer_part, layer, default_visibility in layers:
            layer_root = package.xml[layer_part]
            slide_report["scanned_layers"].append({"part": layer_part, "layer": layer})
            if first(layer_root, A_NS, "blip") is not None:
                issue("picture_text_unchecked", "Pictures require visual/OCR review; native text checks cannot inspect them.",
                      slide=number, part=layer_part)
            if any(PACKAGE.tag_parts(node.tag)[1] in {"chart", "oleObj", "graphicData"}
                   for node in layer_root.iter()
                   if PACKAGE.tag_parts(node.tag)[1] != "graphicData" or "table" not in node.get("uri", "")):
                issue("non_native_text_unchecked", "Chart, diagram, or embedded-object text requires separate review.",
                      slide=number, part=layer_part)
            for shape, grouped, alternate in native_shapes(layer_root):
                identity = first(shape, P_NS, "cNvPr")
                if identity is not None and not is_false(identity.get("hidden", "0")):
                    continue
                runs = run_records(shape)
                text = shape_text(runs)
                if not text.strip():
                    continue
                ph = first(shape, P_NS, "ph")
                visibility = default_visibility
                if alternate or (layer != "slide" and ph is not None):
                    visibility = "needs_review"
                record = {"id": identity.get("id") if identity is not None else None,
                          "name": identity.get("name") if identity is not None else None,
                          "part": layer_part, "layer": layer, "visibility": visibility,
                          "placeholder": dict(ph.attrib) if ph is not None else None,
                          "position": position(shape, grouped), "text": text, "runs": runs}
                slide_report["shapes"].append(record)
                context = {"slide": number, "part": layer_part, "shape_id": record["id"],
                           "layer": layer, "text": text, "position": record["position"]}
                if visibility == "needs_review":
                    issue("conditional_text_visibility", "Inherited placeholder or alternate content needs rendered confirmation.", **context)
                normalized = re.sub(r"\s+", "", text)
                matches = [match.group() for pattern in DEFENSIVE_PATTERNS
                           for match in re.finditer(pattern, normalized)]
                if matches:
                    issue("defensive_copy_candidate", "Review and remove unnecessary defensive/production copy; never delete scientific conditions automatically.",
                          "error" if visibility == "visible" else "needs_review", matches=matches,
                          fonts=[run["fonts"] for run in runs], **context)
                for index, run in enumerate(runs):
                    if run["unclassified_characters"]:
                        issue("font_script_needs_review", "Symbols or scripts outside the automatic CJK/Latin mapping require manual font review; preserve scientific notation.",
                              run=index, run_text=run["text"], characters=run["unclassified_characters"], **context)
                    for script, font in run["fonts"].items():
                        expected = report["font_policy"][script]
                        if not font["resolved"]:
                            issue("font_inheritance_unresolved", "Font cannot be established from local declarations.",
                                  run=index, run_text=run["text"], script=script, font=font, expected=expected, **context)
                        elif font_key(font["typeface"]) != font_key(expected):
                            issue("font_mismatch", "Explicit font differs from the selected policy.",
                                  "error" if visibility == "visible" else "needs_review",
                                  run=index, run_text=run["text"], script=script, font=font, expected=expected, **context)
        report["slides"].append(slide_report)
    if any(item["severity"] == "error" for item in report["issues"]):
        report["status"] = "fail"
    elif report["issues"]:
        report["status"] = "needs_review"
    return report


def main(argv=None):
    parser = PACKAGE.AsciiArgumentParser(description=__doc__)
    parser.add_argument("pptx", type=Path)
    parser.add_argument("--output", type=Path, help="Optional UTF-8 JSON report; input PPTX is never modified")
    parser.add_argument("--cjk-font", default=DEFAULT_CJK_FONT, help="Override only when the user explicitly requests another font")
    parser.add_argument("--latin-font", default=DEFAULT_LATIN_FONT, help="Override only when the user explicitly requests another font")
    args = parser.parse_args(argv)
    if not args.cjk_font.strip() or not args.latin_font.strip():
        parser.error("Font names must not be empty")
    if args.output is not None:
        same = args.output.resolve() == args.pptx.resolve()
        if args.output.exists() and args.pptx.exists():
            same = same or args.output.samefile(args.pptx)
        if same:
            parser.error("--output must not overwrite the input PPTX")
    report = audit_slide_rules(args.pptx, args.cjk_font, args.latin_font)
    if args.output is not None:
        try:
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            report["status"] = "fail"
            report["issues"].append({"code": "report_write_failed", "severity": "error", "message": str(exc)})
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return {"pass": 0, "fail": 1, "needs_review": 2}[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
