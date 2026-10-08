"""Native-text behavior tests; fixtures contain no private report material."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from xml.sax.saxutils import escape
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_slide_rules.py"
SPEC = importlib.util.spec_from_file_location("audit_slide_rules", SCRIPT)
RULES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RULES)
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"


def rels(*rows):
    return '<Relationships xmlns="{}">{}</Relationships>'.format(PKG, "".join(
        '<Relationship Id="{}" Type="{}/{}" Target="{}"/>'.format(*(
            row[0], R, row[1], escape(row[2]))) for row in rows))


def fonts(cjk="Microsoft YaHei", latin="Times New Roman"):
    return ''.join('<a:{} typeface="{}"/>'.format(kind, escape(value))
                   for kind, value in (("ea", cjk), ("latin", latin)) if value is not None)


def run(text, cjk="Microsoft YaHei", latin="Times New Roman"):
    return '<a:r><a:rPr sz="1800">{}</a:rPr><a:t>{}</a:t></a:r>'.format(fonts(cjk, latin), escape(text))


def shape(runs=None, text="测量结果 Model 123", placeholder=None, ident=2,
          y="100000", hidden=False, paragraph_defaults=""):
    ph = '<p:ph type="{}"/>'.format(placeholder) if placeholder else ""
    return ('<p:sp><p:nvSpPr><p:cNvPr id="{}" name="Text" hidden="{}"/>'
            '<p:cNvSpPr/><p:nvPr>{}</p:nvPr></p:nvSpPr><p:spPr>'
            '<a:xfrm><a:off x="500000" y="{}"/><a:ext cx="4000000" cy="500000"/>'
            '</a:xfrm></p:spPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p>{}{}</a:p>'
            '</p:txBody></p:sp>').format(ident, int(hidden), ph, y,
                                      paragraph_defaults, run(text) if runs is None else runs)


def page(contents, kind="sld", attrs=""):
    return '<p:{} xmlns:p="{}" xmlns:a="{}" xmlns:r="{}" {}><p:cSld><p:spTree>{}</p:spTree></p:cSld></p:{}>'.format(
        kind, P, A, R, attrs, contents, kind)


def fixture(slide_contents=None):
    return {
        "[Content_Types].xml": '<Types xmlns="{}"/>'.format(CT),
        "_rels/.rels": rels(("root", "officeDocument", "ppt/presentation.xml")),
        "ppt/presentation.xml": '<p:presentation xmlns:p="{}" xmlns:r="{}"><p:sldIdLst><p:sldId id="256" r:id="one"/></p:sldIdLst><p:sldSz cx="12192000" cy="6858000"/></p:presentation>'.format(P, R),
        "ppt/_rels/presentation.xml.rels": rels(("one", "slide", "slides/slide7.xml")),
        "ppt/slides/slide7.xml": page(shape() if slide_contents is None else slide_contents),
        "ppt/slides/_rels/slide7.xml.rels": rels(("layout", "slideLayout", "../slideLayouts/layout.xml"),
                                                   ("notes", "notesSlide", "../notesSlides/notes.xml")),
        "ppt/slideLayouts/layout.xml": page("", "sldLayout"),
        "ppt/slideLayouts/_rels/layout.xml.rels": rels(("master", "slideMaster", "../slideMasters/master.xml")),
        "ppt/slideMasters/master.xml": page("", "sldMaster"),
        "ppt/notesSlides/notes.xml": page(shape(text="仅供参考", placeholder="body"), "notes"),
        "ppt/notesSlides/_rels/notes.xml.rels": rels(("slide", "slide", "../slides/slide7.xml")),
    }


class SlideRulesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def package(self, parts=None):
        path = self.directory / "deck.pptx"
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in (fixture() if parts is None else parts).items():
                archive.writestr(name, content)
        return path

    def audit(self, parts=None, **kwargs):
        return RULES.audit_slide_rules(self.package(parts), **kwargs)

    def codes(self, report):
        return [issue["code"] for issue in report["issues"]]

    def cli(self, path, *args):
        return subprocess.run([sys.executable, str(SCRIPT), str(path), *map(str, args)], capture_output=True, check=False)

    def test_correct_mixed_fonts_notes_excluded_and_read_only(self):
        path = self.package()
        before = path.read_bytes()
        report = RULES.audit_slide_rules(path)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["issues"], [])
        self.assertEqual(report["slides"][0]["shapes"][0]["text"], "测量结果 Model 123")
        self.assertTrue(report["semantic_review_required"])
        self.assertTrue(report["visual_review_required"])
        self.assertEqual(path.read_bytes(), before)

    def test_cross_run_defensive_copy_in_module_body(self):
        report = self.audit(fixture(shape(runs=run("测量；仅供") + run("参考"), y="1200000")))
        issue = next(item for item in report["issues"] if item["code"] == "defensive_copy_candidate")
        self.assertEqual(report["status"], "fail")
        self.assertEqual(issue["matches"], ["仅供参考"])
        self.assertEqual((issue["slide"], issue["shape_id"], issue["position"]["y"]), (1, "2", "1200000"))
        self.assertIn("fonts", issue)

    def test_native_footer_placeholder_is_not_excluded(self):
        report = self.audit(fixture(shape(text="以实际结果为准", placeholder="ftr", y="6500000")))
        self.assertEqual(report["status"], "fail")
        self.assertIn("defensive_copy_candidate", self.codes(report))
        self.assertEqual(report["slides"][0]["shapes"][0]["placeholder"]["type"], "ftr")

    def test_master_and_layout_static_text_are_scanned(self):
        for target, kind in (("ppt/slideMasters/master.xml", "sldMaster"), ("ppt/slideLayouts/layout.xml", "sldLayout")):
            with self.subTest(target=target):
                parts = fixture()
                parts[target] = page(shape(text="仅作展示"), kind)
                report = self.audit(parts)
                self.assertEqual(report["status"], "fail")
                issues = [i for i in report["issues"] if i["code"] == "defensive_copy_candidate"]
                self.assertEqual(issues[0]["part"], target)

    def test_inherited_placeholder_visibility_is_review_not_assumed(self):
        parts = fixture()
        parts["ppt/slideMasters/master.xml"] = page(shape(text="仅供参考", placeholder="ftr"), "sldMaster")
        report = self.audit(parts)
        self.assertEqual(report["status"], "needs_review")
        self.assertIn("conditional_text_visibility", self.codes(report))
        self.assertIn("defensive_copy_candidate", self.codes(report))

    def test_disabled_master_and_hidden_shape_are_excluded(self):
        parts = fixture(shape() + shape(text="仅供参考", hidden=True, ident=3))
        parts["ppt/slides/slide7.xml"] = page(shape(), attrs='showMasterSp="0"')
        parts["ppt/slideMasters/master.xml"] = page(shape(text="仅供参考"), "sldMaster")
        self.assertEqual(self.audit(parts)["status"], "pass")
        self.assertEqual(self.audit(fixture(shape() + shape(text="仅供参考", hidden=True, ident=3)))["status"], "pass")

    def test_scientific_conditions_are_preserved(self):
        text = "模型预测；n=3；95% CI；仅在低盐条件下有效；温度 25 C；结构置信度较低"
        report = self.audit(fixture(shape(text=text)))
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["slides"][0]["shapes"][0]["text"], text)

    def test_wrong_explicit_font_and_user_override(self):
        parts = fixture(shape(runs=run("测量 A12", cjk="SimSun", latin="Arial")))
        report = self.audit(parts)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(len([i for i in report["issues"] if i["code"] == "font_mismatch"]), 2)
        self.assertEqual(self.audit(parts, cjk_font="SimSun", latin_font="Arial")["status"], "pass")
        self.assertEqual(self.audit(fixture(shape(runs=run("测量 A12", cjk="微软雅黑"))))["status"], "pass")
        # Full-width decimal digits also follow the numeric/Latin policy.
        self.assertEqual(RULES.script_classes("１２３"), ["latin"])

    def test_missing_and_theme_fonts_need_review(self):
        for ea, latin in ((None, None), ("+mn-ea", "+mn-lt")):
            with self.subTest(font=ea):
                report = self.audit(fixture(shape(runs=run("测量 A12", cjk=ea, latin=latin))))
                self.assertEqual(report["status"], "needs_review")
                self.assertIn("font_inheritance_unresolved", self.codes(report))
                self.assertNotIn("font_mismatch", self.codes(report))

    def test_ascii_punctuation_only_run_checks_latin_font(self):
        punctuation = "()-/:,.%"
        self.assertEqual(RULES.script_classes(punctuation), ["latin"])
        report = self.audit(fixture(shape(runs=run(punctuation, latin="Arial"))))
        self.assertEqual(report["status"], "fail")
        mismatch = [item for item in report["issues"] if item["code"] == "font_mismatch"]
        self.assertEqual([item["script"] for item in mismatch], ["latin"])
        self.assertEqual(self.audit(fixture(shape(text=punctuation)))["status"], "pass")

    def test_chinese_punctuation_only_run_checks_cjk_font(self):
        punctuation = "“”‘’·，。；：？！《》【】"
        self.assertEqual(RULES.script_classes(punctuation), ["cjk"])
        report = self.audit(fixture(shape(runs=run(punctuation, cjk="SimSun"))))
        self.assertEqual(report["status"], "fail")
        self.assertEqual([item["script"] for item in report["issues"]
                          if item["code"] == "font_mismatch"], ["cjk"])
        self.assertEqual(self.audit(fixture(shape(text=punctuation)))["status"], "pass")

    def test_scientific_symbol_run_needs_review_without_rewriting(self):
        symbols = "α±×→"
        parts = fixture(shape(runs=run(symbols, cjk="Symbol", latin="Symbol")))
        path = self.package(parts)
        before = path.read_bytes()
        report = RULES.audit_slide_rules(path)
        self.assertEqual(report["status"], "needs_review")
        self.assertIn("font_script_needs_review", self.codes(report))
        self.assertNotIn("font_mismatch", self.codes(report))
        self.assertEqual(report["slides"][0]["shapes"][0]["text"], symbols)
        self.assertEqual(path.read_bytes(), before)

    def test_paragraph_and_text_body_defaults_resolve(self):
        default = '<a:pPr><a:defRPr>{}</a:defRPr></a:pPr>'.format(fonts())
        report = self.audit(fixture(shape(runs=run("测量 A12", None, None), paragraph_defaults=default)))
        self.assertEqual(report["status"], "pass")
        body = shape(runs=run("测量 A12", None, None)).replace('<a:lstStyle/>',
            '<a:lstStyle><a:lvl1pPr><a:defRPr>{}</a:defRPr></a:lvl1pPr></a:lstStyle>'.format(fonts()))
        self.assertEqual(self.audit(fixture(body))["status"], "pass")

    def test_image_text_is_unchecked_and_not_silent_pass(self):
        parts = fixture(shape() + '<p:pic><p:blipFill><a:blip/></p:blipFill></p:pic>')
        report = self.audit(parts)
        self.assertEqual(report["status"], "needs_review")
        self.assertIn("picture_text_unchecked", self.codes(report))

    def test_native_table_text_is_inspected(self):
        table = ('<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="5" name="Table"/>'
                 '</p:nvGraphicFramePr><a:graphic><a:graphicData '
                 'uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
                 '<a:tbl><a:tr><a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p>{}'
                 '</a:p></a:txBody></a:tc></a:tr></a:tbl></a:graphicData>'
                 '</a:graphic></p:graphicFrame>').format(run("仅作示意"))
        report = self.audit(fixture(table))
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["slides"][0]["shapes"][0]["id"], "5")
        self.assertIn("defensive_copy_candidate", self.codes(report))
        self.assertNotIn("non_native_text_unchecked", self.codes(report))

    def test_strict_ooxml_namespace_is_supported(self):
        parts = fixture()
        for name in parts:
            for old, new in ((P, "http://purl.oclc.org/ooxml/presentationml/main"),
                             (A, "http://purl.oclc.org/ooxml/drawingml/main"),
                             (R, "http://purl.oclc.org/ooxml/officeDocument/relationships")):
                parts[name] = parts[name].replace(old, new)
        self.assertEqual(self.audit(parts)["status"], "pass")

    def test_grouped_shape_preserves_local_coordinate_warning(self):
        report = self.audit(fixture('<p:grpSp>' + shape(text="仅供参考") + '</p:grpSp>'))
        self.assertEqual(report["status"], "fail")
        position = report["slides"][0]["shapes"][0]["position"]
        self.assertTrue(position["grouped"])
        self.assertEqual(position["coordinate_space"], "local_emu")

    def test_cli_ascii_utf8_output_exit_codes_and_input_protection(self):
        path = self.package()
        output = self.directory / "报告.json"
        before = path.read_bytes()
        proc = self.cli(path, "--output", output)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc.stdout.decode("ascii")
        self.assertIn("测量结果", output.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(proc.stdout), json.loads(output.read_text(encoding="utf-8")))
        self.assertNotEqual(self.cli(path, "--output", path).returncode, 0)
        hardlink = self.directory / "hardlink.pptx"
        os.link(path, hardlink)
        self.assertNotEqual(self.cli(path, "--output", hardlink).returncode, 0)
        self.assertEqual(path.read_bytes(), before)
        self.package(fixture(shape(runs=run("A", latin=None))))
        self.assertEqual(self.cli(path).returncode, 2)
        self.package(fixture(shape(text="仅供参考")))
        self.assertEqual(self.cli(path).returncode, 1)

    def test_invalid_package_returns_failure(self):
        path = self.directory / "broken.pptx"
        path.write_text("not a zip", encoding="ascii")
        self.assertEqual(RULES.audit_slide_rules(path)["status"], "fail")


if __name__ == "__main__":
    unittest.main()
