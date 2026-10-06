"""Behavior tests using neutral temporary OOXML packages, never private decks."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import warnings
from xml.sax.saxutils import escape
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_pptx.py"
SPEC = importlib.util.spec_from_file_location("audit_pptx", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"


def rels(*entries):
    rows = []
    for entry in entries:
        rid, kind, target, *mode = entry
        external = ' TargetMode="External"' if mode and mode[0] else ""
        rows.append('<Relationship Id="{}" Type="{}/{}" Target="{}"{}/>'.format(
            rid, R, kind, escape(target, {'"': '&quot;'}), external))
    return '<Relationships xmlns="{}">{}</Relationships>'.format(PKG, "".join(rows))


def shape(text, placeholder=None, font="Arial", size="2400"):
    ph = '<p:ph type="{}"/>'.format(placeholder) if placeholder else ""
    return ('<p:sp><p:nvSpPr><p:cNvPr id="2" name="Text"/><p:cNvSpPr/>'
            '<p:nvPr>{}</p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/>'
            '<a:lstStyle/><a:p><a:r><a:rPr sz="{}"><a:latin typeface="{}"/>'
            '</a:rPr><a:t>{}</a:t></a:r></a:p></p:txBody></p:sp>').format(
                ph, size, escape(font), escape(text))


def slide_xml(text, extra="", font="Arial", size="2400"):
    return ('<p:sld xmlns:p="{}" xmlns:a="{}" xmlns:r="{}" xmlns:c="{}">'
            '<p:cSld><p:spTree>{}{}</p:spTree></p:cSld></p:sld>').format(
                P, A, R, C, shape(text, font=font, size=size), extra)


def notes_xml(text="Speaker notes", placeholder="body", extra=""):
    return ('<p:notes xmlns:p="{}" xmlns:a="{}"><p:cSld><p:spTree>'
            '{}{}</p:spTree></p:cSld></p:notes>').format(
                P, A, shape(text, placeholder), extra)


def fixture():
    return {
        "[Content_Types].xml": '<Types xmlns="{}"><Default Extension="xml" '
                               'ContentType="application/xml"/><Default Extension="rels" '
                               'ContentType="application/vnd.openxmlformats-package.relationships+xml"/></Types>'.format(CT),
        "_rels/.rels": rels(("root", "officeDocument", "ppt/presentation.xml")),
        "ppt/presentation.xml": (
            '<p:presentation xmlns:p="{}" xmlns:r="{}"><p:sldIdLst>'
            '<p:sldId id="256" r:id="secondFile"/><p:sldId id="257" r:id="firstFile"/>'
            '</p:sldIdLst><p:sldSz cx="12192000" cy="6858000"/></p:presentation>').format(P, R),
        "ppt/_rels/presentation.xml.rels": rels(
            ("firstFile", "slide", "slides/slide9.xml"),
            ("secondFile", "slide", "slides/slide2.xml")),
        "ppt/slides/slide9.xml": slide_xml("Alpha"),
        "ppt/slides/slide2.xml": slide_xml("Beta"),
        "ppt/slides/_rels/slide9.xml.rels": rels(("notes", "notesSlide", "../notesSlides/notes9.xml")),
        "ppt/slides/_rels/slide2.xml.rels": rels(("notes", "notesSlide", "../notesSlides/notes2.xml")),
        "ppt/notesSlides/notes9.xml": notes_xml(),
        "ppt/notesSlides/notes2.xml": notes_xml(),
        "ppt/notesSlides/_rels/notes9.xml.rels": rels(("slide", "slide", "../slides/slide9.xml")),
        "ppt/notesSlides/_rels/notes2.xml.rels": rels(("slide", "slide", "../slides/slide2.xml")),
    }


def strict_namespaces(parts):
    replacements = {P: "http://purl.oclc.org/ooxml/presentationml/main",
                    A: "http://purl.oclc.org/ooxml/drawingml/main",
                    R: "http://purl.oclc.org/ooxml/officeDocument/relationships",
                    C: "http://purl.oclc.org/ooxml/drawingml/chart"}
    for part, value in parts.items():
        if isinstance(value, str):
            for old, new in replacements.items():
                value = value.replace(old, new)
            parts[part] = value
    return parts


class AuditPptxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def package(self, parts=None, name="deck.pptx"):
        path = self.directory / name
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
            for part, data in (fixture() if parts is None else parts).items():
                archive.writestr(part, data)
        return path

    def audit(self, parts=None, **kwargs):
        return AUDIT.audit_pptx(self.package(parts), **kwargs)

    def assert_issue(self, result, code):
        self.assertIn(code, [item["code"] for item in result["issues"]])

    def cli(self, path, *args):
        return subprocess.run([sys.executable, str(SCRIPT), str(path), *map(str, args)],
                              capture_output=True, check=False)

    def test_valid_reordered_slides_canvas_fonts_and_read_only(self):
        path = self.package()
        original = path.read_bytes()
        report = AUDIT.audit_pptx(path, require_notes=True, expected_slides=2)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["issues"], [])
        self.assertEqual([s["part"] for s in report["slides"]],
                         ["ppt/slides/slide2.xml", "ppt/slides/slide9.xml"])
        self.assertEqual([s["text_characters"] for s in report["slides"]], [4, 5])
        self.assertEqual(report["canvas"]["aspect_ratio"], "16:9")
        self.assertEqual(report["slides"][0]["explicit_font_families"], ["Arial"])
        self.assertEqual(report["slides"][0]["explicit_font_sizes_pt"], [24.0])
        self.assertEqual(path.read_bytes(), original)

    def test_slide_order_changes_with_id_list(self):
        parts = fixture()
        parts["ppt/presentation.xml"] = parts["ppt/presentation.xml"].replace(
            'r:id="secondFile"', 'r:id="temporary"').replace(
            'r:id="firstFile"', 'r:id="secondFile"').replace('r:id="temporary"', 'r:id="firstFile"')
        report = self.audit(parts)
        self.assertEqual([s["text_characters"] for s in report["slides"]], [5, 4])

    def test_missing_notes_optional_warning_and_required_failure(self):
        parts = fixture()
        del parts["ppt/slides/_rels/slide2.xml.rels"]
        optional = self.audit(parts)
        self.assertEqual(optional["status"], "pass")
        self.assert_issue(optional, "missing_notes")
        required = self.audit(parts, require_notes=True)
        self.assertEqual(required["status"], "fail")
        self.assertEqual(required["slides"][0]["notes"]["status"], "missing")

    def test_placeholder_only_notes_and_blank_body_are_empty(self):
        for kind in ("sldNum", "hdr", "ftr", "dt", "sldImg", "blank"):
            with self.subTest(kind=kind):
                parts = fixture()
                parts["ppt/notesSlides/notes2.xml"] = notes_xml(
                    " \n\t " if kind == "blank" else "Placeholder text",
                    "body" if kind == "blank" else kind)
                report = self.audit(parts, require_notes=True)
                self.assertEqual(report["status"], "fail")
                self.assert_issue(report, "empty_notes")
                self.assertEqual(report["slides"][0]["notes"]["text_characters"], 0)

    def test_slide_number_field_does_not_count_as_notes(self):
        parts = fixture()
        field = '<p:sp><p:txBody><a:p><a:fld id="field" type="slidenum"><a:t>2</a:t></a:fld></a:p></p:txBody></p:sp>'
        parts["ppt/notesSlides/notes2.xml"] = notes_xml("", extra=field)
        report = self.audit(parts, require_notes=True)
        self.assert_issue(report, "empty_notes")

    def test_notes_body_retained_but_placeholders_excluded(self):
        parts = fixture()
        parts["ppt/notesSlides/notes2.xml"] = notes_xml("Body", extra=shape("99", "sldNum") + shape("Footer", "ftr"))
        report = self.audit(parts, require_notes=True)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["slides"][0]["notes"]["text_characters"], 4)

    def test_wrong_missing_and_duplicate_notes_backlink(self):
        for replacement in (rels(("slide", "slide", "../slides/slide9.xml")),
                            rels(), rels(("one", "slide", "../slides/slide2.xml"),
                                         ("two", "slide", "../slides/slide2.xml"))):
            with self.subTest(replacement=replacement):
                parts = fixture()
                parts["ppt/notesSlides/_rels/notes2.xml.rels"] = replacement
                report = self.audit(parts)
                self.assertEqual(report["status"], "fail")
                self.assert_issue(report, "notes_mapping_mismatch")

    def test_damaged_zip_and_missing_file(self):
        path = self.directory / "broken.pptx"
        path.write_bytes(b"This is not a ZIP package")
        self.assert_issue(AUDIT.audit_pptx(path), "unreadable_zip")
        self.assert_issue(AUDIT.audit_pptx(self.directory / "missing.pptx"), "unreadable_zip")

    def test_corrupt_member_crc(self):
        path = self.package()
        data = path.read_bytes()
        self.assertIn(b"Speaker notes", data)
        path.write_bytes(data.replace(b"Speaker notes", b"Changed notes", 1))
        report = AUDIT.audit_pptx(path)
        self.assertEqual(report["status"], "fail")
        self.assert_issue(report, "unreadable_part")

    def test_malformed_xml_anywhere_fails(self):
        for part in ("ppt/slides/slide2.xml", "ppt/notesSlides/notes2.xml",
                     "ppt/unused.xml", "[Content_Types].xml", "ppt/_rels/presentation.xml.rels"):
            with self.subTest(part=part):
                parts = fixture()
                parts[part] = "<broken>"
                report = self.audit(parts)
                self.assertEqual(report["status"], "fail")
                self.assert_issue(report, "invalid_xml")

    def test_missing_internal_relationship_target_fails(self):
        for target in ("ppt/slides/slide2.xml", "ppt/notesSlides/notes2.xml"):
            with self.subTest(target=target):
                parts = fixture()
                del parts[target]
                report = self.audit(parts)
                self.assertEqual(report["status"], "fail")
                self.assert_issue(report, "missing_relationship_target")

    def test_missing_relationship_id_and_wrong_target_type(self):
        parts = fixture()
        parts["ppt/_rels/presentation.xml.rels"] = rels(("firstFile", "slide", "slides/slide9.xml"))
        self.assert_issue(self.audit(parts), "missing_relationship_id")
        parts = fixture()
        parts["ppt/slides/slide2.xml"] = notes_xml()
        self.assert_issue(self.audit(parts), "invalid_target_xml")

    def test_duplicate_relationship_and_slide_targets(self):
        parts = fixture()
        parts["ppt/_rels/presentation.xml.rels"] = rels(
            ("firstFile", "slide", "slides/slide9.xml"),
            ("secondFile", "slide", "slides/slide9.xml"),
            ("secondFile", "slide", "slides/slide2.xml"))
        report = self.audit(parts)
        self.assert_issue(report, "duplicate_relationship_id")
        self.assert_issue(report, "duplicate_slide_target")

    def test_invalid_internal_target_uris(self):
        for target in ("../../../escape.xml", "https://example.invalid/slide.xml", "../slides\\slide2.xml"):
            with self.subTest(target=target):
                parts = fixture()
                parts["ppt/_rels/presentation.xml.rels"] = rels(("secondFile", "slide", target))
                self.assert_issue(self.audit(parts), "invalid_relationship_target")

    def test_root_relative_and_percent_encoded_targets(self):
        parts = fixture()
        parts["ppt/_rels/presentation.xml.rels"] = rels(
            ("firstFile", "slide", "/ppt/slides/slide9.xml"),
            ("secondFile", "slide", "slides/slide%32.xml"))
        self.assertEqual(self.audit(parts)["status"], "pass")

    def test_native_chart_and_picture_counts_and_missing_media(self):
        parts = fixture()
        extra = ('<p:pic><p:blipFill><a:blip r:embed="picture"/></p:blipFill></p:pic>'
                 '<p:graphicFrame><a:graphic><a:graphicData><c:chart r:id="chart"/>'
                 '</a:graphicData></a:graphic></p:graphicFrame>')
        parts["ppt/slides/slide2.xml"] = slide_xml("Beta", extra)
        parts["ppt/slides/_rels/slide2.xml.rels"] = rels(
            ("notes", "notesSlide", "../notesSlides/notes2.xml"),
            ("picture", "image", "../media/image1.png"),
            ("chart", "chart", "../charts/chart1.xml"))
        parts["ppt/media/image1.png"] = b"neutral bytes; decoding is outside scope"
        parts["ppt/charts/chart1.xml"] = '<c:chartSpace xmlns:c="{}"><c:chart/></c:chartSpace>'.format(C)
        report = self.audit(parts)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["slides"][0]["image_count"], 1)
        self.assertEqual(report["slides"][0]["image_reference_count"], 1)
        self.assertEqual(report["slides"][0]["native_chart_count"], 1)
        del parts["ppt/media/image1.png"]
        self.assert_issue(self.audit(parts), "missing_relationship_target")
        parts["ppt/media/image1.png"] = b"fixture"
        parts["ppt/charts/chart1.xml"] = "<wrong/>"
        self.assert_issue(self.audit(parts), "invalid_target_xml")

    def test_external_hyperlink_counted_without_fetching(self):
        parts = fixture()
        parts["ppt/slides/slide2.xml"] = slide_xml("Beta", '<a:hlinkClick r:id="link"/>')
        parts["ppt/slides/_rels/slide2.xml.rels"] = rels(
            ("notes", "notesSlide", "../notesSlides/notes2.xml"),
            ("link", "hyperlink", "https://example.invalid", True))
        report = self.audit(parts)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["external_relationship_count"], 1)

    def test_standard_chart_reference_rejects_image_relationship(self):
        for strict in (False, True):
            with self.subTest(strict=strict):
                parts = fixture()
                parts["ppt/slides/slide2.xml"] = slide_xml("Beta", '<c:chart r:id="wrongType"/>')
                parts["ppt/slides/_rels/slide2.xml.rels"] = rels(
                    ("notes", "notesSlide", "../notesSlides/notes2.xml"),
                    ("wrongType", "image", "../media/image1.png"))
                parts["ppt/media/image1.png"] = b"neutral image fixture"
                if strict:
                    strict_namespaces(parts)
                path = self.package(parts)
                original = path.read_bytes()
                result = self.cli(path)
                self.assertEqual(result.returncode, 1)
                self.assertTrue(result.stdout.isascii())
                self.assert_issue(json.loads(result.stdout), "relationship_type_mismatch")
                self.assertEqual(path.read_bytes(), original)

    def test_blip_references_reject_non_image_relationships(self):
        for strict in (False, True):
            for attribute in ("embed", "link"):
                with self.subTest(strict=strict, attribute=attribute):
                    parts = fixture()
                    extra = '<a:blip r:{}="wrongType"/>'.format(attribute)
                    parts["ppt/slides/slide2.xml"] = slide_xml("Beta", extra)
                    parts["ppt/slides/_rels/slide2.xml.rels"] = rels(
                        ("notes", "notesSlide", "../notesSlides/notes2.xml"),
                        ("wrongType", "hyperlink", "../media/image1.png"))
                    parts["ppt/media/image1.png"] = b"neutral image fixture"
                    if strict:
                        strict_namespaces(parts)
                    report = self.audit(parts)
                    self.assertEqual(report["status"], "fail")
                    self.assert_issue(report, "relationship_type_mismatch")

    def test_standard_chart_and_image_relationship_types_remain_valid(self):
        for strict in (False, True):
            with self.subTest(strict=strict):
                parts = fixture()
                extra = '<c:chart r:id="chart"/><a:blip r:embed="picture" r:link="linkedPicture"/>'
                parts["ppt/slides/slide2.xml"] = slide_xml("Beta", extra)
                parts["ppt/slides/_rels/slide2.xml.rels"] = rels(
                    ("notes", "notesSlide", "../notesSlides/notes2.xml"),
                    ("chart", "chart", "../charts/chart1.xml"),
                    ("picture", "image", "../media/image1.png"),
                    ("linkedPicture", "image", "https://example.invalid/image.png", True))
                parts["ppt/charts/chart1.xml"] = '<c:chartSpace xmlns:c="{}"><c:chart/></c:chartSpace>'.format(C)
                parts["ppt/media/image1.png"] = b"neutral image fixture"
                if strict:
                    strict_namespaces(parts)
                self.assertEqual(self.audit(parts)["status"], "pass")

    def test_extended_chart_is_not_forced_to_use_standard_chart_relationship(self):
        parts = fixture()
        chart_ns = "http://schemas.microsoft.com/office/drawing/2014/chartex"
        chart_type = "http://schemas.microsoft.com/office/2014/relationships/chartEx"
        extra = '<cx:chart xmlns:cx="{}" r:id="extendedChart"/>'.format(chart_ns)
        parts["ppt/slides/slide2.xml"] = slide_xml("Beta", extra)
        parts["ppt/slides/_rels/slide2.xml.rels"] = rels(
            ("notes", "notesSlide", "../notesSlides/notes2.xml"),
            ("extendedChart", "chartEx", "../charts/chartEx1.xml")).replace(R + "/chartEx", chart_type)
        parts["ppt/charts/chartEx1.xml"] = '<cx:chartSpace xmlns:cx="{}"/>'.format(chart_ns)
        self.assertEqual(self.audit(parts)["status"], "pass")

    def test_external_slide_relationship_fails(self):
        parts = fixture()
        parts["ppt/_rels/presentation.xml.rels"] = rels(("secondFile", "slide", "https://example.invalid/slide.xml", True))
        self.assert_issue(self.audit(parts), "external_structural_target")

    def test_expected_count_mismatch_and_cli_exit_status(self):
        path = self.package()
        result = self.cli(path, "--expected-slides", "3")
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assert_issue(report, "slide_count_mismatch")
        self.assertEqual(self.cli(path, "--expected-slides", "2", "--require-notes").returncode, 0)

    def test_unicode_notes_counts_and_ascii_json_stdout_and_file(self):
        parts = fixture()
        text = "\u4e2d\u6587\u5907\u6ce8\U0001f9ea"
        parts["ppt/notesSlides/notes2.xml"] = notes_xml(text)
        parts["ppt/slides/slide2.xml"] = slide_xml("Beta", font="\u601d\u6e90\u9ed1\u4f53")
        path = self.package(parts, name="\u6f14\u793a.pptx")
        output = self.directory / "report.json"
        result = self.cli(path, "--require-notes", "--output", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.isascii())
        self.assertTrue(output.read_bytes().isascii())
        report = json.loads(result.stdout)
        self.assertEqual(report["slides"][0]["notes"]["text_characters"], len(text))
        self.assertEqual(json.loads(output.read_bytes()), report)

    def test_output_cannot_overwrite_input_or_hardlink(self):
        path = self.package()
        original = path.read_bytes()
        alias = self.directory / "alias.json"
        os.link(path, alias)
        for output in (path, alias):
            with self.subTest(output=output.name):
                self.assertEqual(self.cli(path, "--output", output).returncode, 2)
                self.assertEqual(path.read_bytes(), original)

    def test_report_write_error_returns_nonzero_json(self):
        path = self.package()
        result = self.cli(path, "--output", self.directory / "absent" / "report.json")
        self.assertEqual(result.returncode, 1)
        self.assert_issue(json.loads(result.stdout), "report_write_failed")

    def test_cli_errors_are_ascii(self):
        path = self.package()
        result = self.cli(path, "--expected-slides", "\u4e09")
        self.assertEqual(result.returncode, 2)
        self.assertTrue(result.stderr.isascii())

    def test_missing_content_type_override_target(self):
        parts = fixture()
        parts["[Content_Types].xml"] = parts["[Content_Types].xml"].replace(
            '</Types>', '<Override PartName="/ppt/missing.xml" ContentType="application/xml"/></Types>')
        self.assert_issue(self.audit(parts), "missing_content_type_target")

    def test_missing_required_parts_and_invalid_canvas(self):
        for missing in ("[Content_Types].xml", "_rels/.rels"):
            with self.subTest(missing=missing):
                parts = fixture()
                del parts[missing]
                self.assert_issue(self.audit(parts), "missing_required_part")
        parts = fixture()
        parts["ppt/presentation.xml"] = parts["ppt/presentation.xml"].replace('cy="6858000"', 'cy="0"')
        self.assert_issue(self.audit(parts), "invalid_slide_size")

    def test_strict_ooxml_namespaces(self):
        parts = strict_namespaces(fixture())
        self.assertEqual(self.audit(parts, require_notes=True)["status"], "pass")

    def test_duplicate_zip_member_is_failure(self):
        path = self.package()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(path, "a") as archive:
                archive.writestr("ppt/slides/slide2.xml", slide_xml("Replacement"))
        self.assert_issue(AUDIT.audit_pptx(path), "duplicate_part")


if __name__ == "__main__":
    unittest.main()
