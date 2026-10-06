#!/usr/bin/env python3
"""Read-only, standard-library structural checks for PowerPoint OOXML packages."""

import argparse
import json
import math
from pathlib import Path
import posixpath
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile
import zlib


P_NS = {
    "http://schemas.openxmlformats.org/presentationml/2006/main",
    "http://purl.oclc.org/ooxml/presentationml/main",
}
A_NS = {
    "http://schemas.openxmlformats.org/drawingml/2006/main",
    "http://purl.oclc.org/ooxml/drawingml/main",
}
R_NS = {
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "http://purl.oclc.org/ooxml/officeDocument/relationships",
}
STANDARD_CHART_NS = {
    "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "http://purl.oclc.org/ooxml/drawingml/chart",
}
CHART_NS = STANDARD_CHART_NS | {
    "http://schemas.microsoft.com/office/drawing/2014/chartex",
}
PKG_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
NON_BODY_PLACEHOLDERS = {"sldNum", "hdr", "ftr", "dt", "sldImg"}
LIMITATIONS = [
    "Structural checks do not verify visual overflow, overlap, readability, or layout.",
    "Scientific accuracy, citations, and factual completeness require human review.",
    "This is not a full OOXML schema validator or a rendering compatibility test.",
    "Font lists contain explicit slide XML declarations only; theme, master, layout, "
    "and inherited text styles are not fully resolved. Theme font tokens may appear.",
    "Picture counts count picture shapes; image reference counts also include fills. "
    "Chart counts count native chart references, not charts embedded in pictures.",
    "Relationship type checks cover standard OOXML chart references and DrawingML "
    "image references. Extended chart references are counted, but their relationship "
    "types are not checked.",
    "External targets are recorded but never fetched; media bytes are not decoded.",
    "Text counts exclude page-number, date, header, footer, and slide-image "
    "placeholders and slide-number fields; no OCR is performed.",
]


def tag_parts(tag):
    if isinstance(tag, str) and tag.startswith("{"):
        return tag[1:].split("}", 1)
    return "", tag


def is_tag(element, namespaces, name):
    namespace, local = tag_parts(element.tag)
    return namespace in namespaces and local == name


def elements(root, namespaces, name):
    return (element for element in root.iter() if is_tag(element, namespaces, name))


def relation_id(element):
    for namespace in R_NS:
        value = element.get("{" + namespace + "}id")
        if value:
            return value
    return None


def relation_kind(type_uri):
    for namespace in R_NS:
        if type_uri.startswith(namespace + "/"):
            return type_uri[len(namespace) + 1:]
    return type_uri


def relationship_source(part):
    if part == "_rels/.rels":
        return ""
    directory, name = posixpath.split(part)
    if posixpath.basename(directory) != "_rels" or not name.endswith(".rels"):
        raise ValueError("Relationship part is outside an _rels directory")
    return posixpath.join(posixpath.dirname(directory), name[:-5])


def resolve_target(source, target):
    """Resolve a package URI without opening a filesystem path or fetching a URL."""
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or parsed.query:
        raise ValueError("Internal target is not a package-part URI")
    path = unquote(parsed.path)
    if "\\" in path or "\x00" in path:
        raise ValueError("Internal target contains an invalid path character")
    if not path:
        if parsed.fragment and source:
            return source
        raise ValueError("Internal target has no part name")
    combined = path.lstrip("/") if path.startswith("/") else posixpath.join(
        posixpath.dirname(source), path
    )
    resolved = posixpath.normpath(combined)
    if resolved in {"", ".", ".."} or resolved.startswith("../"):
        raise ValueError("Internal target escapes the package root")
    return resolved


def body_text(root):
    chunks = []

    def visit(element):
        if is_tag(element, P_NS, "sp"):
            if any(ph.get("type") in NON_BODY_PLACEHOLDERS
                   for ph in elements(element, P_NS, "ph")):
                return
        if is_tag(element, A_NS, "fld"):
            field_type = element.get("type", "").lower()
            if field_type == "slidenum" or field_type.startswith("datetime"):
                return
        if is_tag(element, A_NS, "t"):
            chunks.append(element.text or "")
        for child in element:
            visit(child)

    visit(root)
    return "".join(chunks).strip()


class Auditor:
    def __init__(self, path, require_notes=False, expected_slides=None):
        self.path = Path(path)
        self.xml = {}
        self.names = set()
        self.relationships = {}
        self.report = {
            "schema_version": 1,
            "file": self.path.name,
            "status": "fail",
            "require_notes": require_notes,
            "expected_slides": expected_slides,
            "slide_count": 0,
            "canvas": None,
            "slides": [],
            "external_relationship_count": 0,
            "issues": [],
            "limitations": LIMITATIONS.copy(),
        }

    def issue(self, code, message, part=None, slide=None, severity="error"):
        item = {"severity": severity, "code": code, "message": message}
        if part is not None:
            item["part"] = part
        if slide is not None:
            item["slide"] = slide
        self.report["issues"].append(item)

    def read_package(self):
        try:
            with zipfile.ZipFile(self.path) as archive:
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    name = info.filename
                    if name in self.names:
                        self.issue("duplicate_part", "Duplicate ZIP member", name)
                    self.names.add(name)
                    if name.startswith(("/", "../")) or "\\" in name or posixpath.normpath(name) != name:
                        self.issue("invalid_part_name", "ZIP member has an invalid part name", name)
                    try:
                        data = archive.read(info)
                    except (OSError, RuntimeError, ValueError, EOFError, zlib.error,
                            zipfile.BadZipFile, NotImplementedError) as exc:
                        self.issue("unreadable_part", "Cannot read member: " + str(exc), name)
                        continue
                    if name.lower().endswith((".xml", ".rels")):
                        try:
                            self.xml[name] = ET.fromstring(data)
                        except (ET.ParseError, LookupError, ValueError) as exc:
                            self.issue("invalid_xml", "XML parse failed: " + str(exc), name)
        except (OSError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
            self.issue("unreadable_zip", "Cannot read PPTX package: " + str(exc))
            return False
        for required in ("[Content_Types].xml", "_rels/.rels"):
            if required not in self.names:
                self.issue("missing_required_part", "Required package part is absent", required)
        content_types = self.xml.get("[Content_Types].xml")
        if content_types is not None and content_types.tag != "{" + CT_NS + "}Types":
            self.issue("invalid_content_types", "Content types root is not Types", "[Content_Types].xml")
        if content_types is not None:
            for child in content_types:
                if child.tag == "{" + CT_NS + "}Override":
                    target = child.get("PartName", "")
                    if not target.startswith("/") or not child.get("ContentType"):
                        self.issue("invalid_content_type_override", "Override needs an absolute part name and content type", "[Content_Types].xml")
                        continue
                    try:
                        resolved = resolve_target("", target)
                    except ValueError as exc:
                        self.issue("invalid_content_type_override", str(exc), "[Content_Types].xml")
                        continue
                    if resolved not in self.names:
                        self.issue("missing_content_type_target", "Override target is absent: " + resolved, "[Content_Types].xml")
        return True

    def read_relationships(self):
        for part, root in self.xml.items():
            if not part.endswith(".rels"):
                continue
            try:
                source = relationship_source(part)
            except ValueError as exc:
                self.issue("invalid_relationship_part", str(exc), part)
                continue
            if source and source not in self.names:
                self.issue("orphan_relationship_part", "Relationship source part is absent", part)
            if root.tag != "{" + PKG_NS + "}Relationships":
                self.issue("invalid_relationship_root", "Relationship root is not Relationships", part)
                continue
            table = self.relationships.setdefault(source, {})
            for child in root:
                if child.tag != "{" + PKG_NS + "}Relationship":
                    self.issue("invalid_relationship_element", "Unexpected relationship element", part)
                    continue
                rid = child.get("Id")
                type_uri = child.get("Type", "")
                target = child.get("Target", "")
                mode = child.get("TargetMode", "Internal")
                if not rid or not type_uri or not target or mode not in {"Internal", "External"}:
                    self.issue("invalid_relationship", "Relationship needs Id, Type, Target and a valid TargetMode", part)
                    continue
                if rid in table:
                    self.issue("duplicate_relationship_id", "Duplicate relationship ID: " + rid, part)
                    continue
                relation = {"kind": relation_kind(type_uri), "target": target,
                            "external": mode == "External", "resolved": None}
                table[rid] = relation
                if relation["external"]:
                    self.report["external_relationship_count"] += 1
                    continue
                try:
                    resolved = resolve_target(source, target)
                    relation["resolved"] = resolved
                except ValueError as exc:
                    self.issue("invalid_relationship_target", str(exc), part)
                    continue
                if resolved not in self.names:
                    self.issue("missing_relationship_target", "Target is absent: " + resolved, part)
        # Check XML references even when a .rels file itself was lost or broken.
        for part, root in self.xml.items():
            if part.endswith(".rels"):
                continue
            table = self.relationships.get(part, {})
            for element in root.iter():
                for attribute, rid in element.attrib.items():
                    namespace, name = tag_parts(attribute)
                    if namespace not in R_NS or name not in {"id", "embed", "link"}:
                        continue
                    relation = table.get(rid)
                    if relation is None:
                        self.issue("missing_relationship_id", "XML refers to absent relationship ID: " + rid, part)
                        continue
                    required_kind = None
                    if is_tag(element, STANDARD_CHART_NS, "chart") and name == "id":
                        required_kind = "chart"
                    elif is_tag(element, A_NS, "blip") and name in {"embed", "link"}:
                        required_kind = "image"
                    if required_kind is not None and relation["kind"] != required_kind:
                        self.issue("relationship_type_mismatch",
                                   "XML reference " + rid + " requires a " + required_kind +
                                   " relationship; found " + relation["kind"], part)
        expected_roots = {
            "officeDocument": (P_NS, "presentation"),
            "slide": (P_NS, "sld"), "slideLayout": (P_NS, "sldLayout"),
            "slideMaster": (P_NS, "sldMaster"), "notesSlide": (P_NS, "notes"),
            "notesMaster": (P_NS, "notesMaster"), "theme": (A_NS, "theme"),
            "chart": (CHART_NS, "chartSpace"),
        }
        for source, table in self.relationships.items():
            for relation in table.values():
                expected = expected_roots.get(relation["kind"])
                if not expected:
                    continue
                part = relation["resolved"]
                if relation["external"]:
                    self.issue("external_structural_target", "Structural relationship must be internal", source)
                elif part in self.names:
                    root = self.xml.get(part)
                    if root is None or not is_tag(root, *expected):
                        self.issue("invalid_target_xml", "Target is not the expected " + expected[1] + " XML", part)

    def notes_for_slide(self, part, number):
        relations = [r for r in self.relationships.get(part, {}).values()
                     if r["kind"] == "notesSlide"]
        result = {"part": None, "text_characters": 0, "status": "missing"}
        if not relations:
            self.issue("missing_notes", "Slide has no notes relationship", part, number,
                       "error" if self.report["require_notes"] else "warning")
            return result
        if len(relations) != 1:
            self.issue("multiple_notes", "Slide has more than one notes relationship", part, number)
        notes_part = relations[0]["resolved"]
        result["part"] = notes_part
        root = self.xml.get(notes_part)
        if root is None or not is_tag(root, P_NS, "notes"):
            result["status"] = "invalid"
            self.issue("invalid_notes", "Notes XML is absent or invalid", notes_part, number)
            return result
        backlinks = [r for r in self.relationships.get(notes_part, {}).values()
                     if r["kind"] == "slide"]
        if len(backlinks) != 1 or backlinks[0]["resolved"] != part or backlinks[0]["external"]:
            self.issue("notes_mapping_mismatch", "Notes must link back to exactly this slide", notes_part, number)
        result["text_characters"] = len(body_text(root))
        result["status"] = "present" if result["text_characters"] else "empty"
        if not result["text_characters"]:
            self.issue("empty_notes", "Notes contain no body text after placeholder exclusion", notes_part, number,
                       "error" if self.report["require_notes"] else "warning")
        return result

    def read_presentation(self):
        documents = [r for r in self.relationships.get("", {}).values()
                     if r["kind"] == "officeDocument"]
        if len(documents) != 1 or documents[0]["external"]:
            self.issue("invalid_presentation_relationship", "Package must have one internal officeDocument relationship")
            return
        part = documents[0]["resolved"]
        root = self.xml.get(part)
        if root is None or not is_tag(root, P_NS, "presentation"):
            self.issue("invalid_presentation", "Presentation XML is absent or invalid", part)
            return
        sizes = list(elements(root, P_NS, "sldSz"))
        try:
            if len(sizes) != 1:
                raise ValueError("Presentation must have one slide size")
            width, height = int(sizes[0].get("cx", "")), int(sizes[0].get("cy", ""))
            if width <= 0 or height <= 0:
                raise ValueError("Slide dimensions must be positive")
            common = math.gcd(width, height)
            self.report["canvas"] = {"width_emu": width, "height_emu": height,
                                     "aspect_ratio": str(width // common) + ":" + str(height // common),
                                     "width_height_ratio": round(width / height, 6)}
        except ValueError as exc:
            self.issue("invalid_slide_size", "Invalid slide size: " + str(exc), part)
        lists = [child for child in root if is_tag(child, P_NS, "sldIdLst")]
        ids = [] if not lists else [child for child in lists[0] if is_tag(child, P_NS, "sldId")]
        if len(lists) != 1 or not ids:
            self.issue("empty_or_invalid_slide_list", "Presentation must contain one nonempty slide ID list", part)
        self.report["slide_count"] = len(ids)
        expected = self.report["expected_slides"]
        if expected is not None and expected != len(ids):
            self.issue("slide_count_mismatch", "Expected " + str(expected) + " slides; found " + str(len(ids)), part)
        seen_ids, seen_parts = set(), set()
        for number, item in enumerate(ids, 1):
            slide_id = item.get("id")
            if not slide_id or slide_id in seen_ids:
                self.issue("invalid_slide_id", "Slide IDs must be present and unique", part, number)
            seen_ids.add(slide_id)
            rid = relation_id(item)
            relation = self.relationships.get(part, {}).get(rid)
            if not relation or relation["kind"] != "slide" or relation["external"]:
                self.issue("invalid_slide_relationship", "Slide ID must resolve through an internal slide relationship", part, number)
                continue
            slide_part = relation["resolved"]
            if slide_part in seen_parts:
                self.issue("duplicate_slide_target", "Multiple slide IDs point to the same slide", slide_part, number)
            seen_parts.add(slide_part)
            slide_root = self.xml.get(slide_part)
            if slide_root is None or not is_tag(slide_root, P_NS, "sld"):
                self.issue("invalid_slide", "Slide XML is absent or invalid", slide_part, number)
                continue
            fonts, sizes = set(), set()
            for element in slide_root.iter():
                namespace, local = tag_parts(element.tag)
                if namespace in A_NS and local in {"latin", "ea", "cs", "sym"} and element.get("typeface"):
                    fonts.add(element.get("typeface"))
                if namespace in A_NS and local in {"rPr", "defRPr", "endParaRPr"} and "sz" in element.attrib:
                    try:
                        value = int(element.get("sz"))
                        if value <= 0:
                            raise ValueError()
                        sizes.add(value / 100)
                    except ValueError:
                        self.issue("invalid_font_size", "Explicit font size must be a positive integer in hundredths of a point", slide_part, number)
            self.report["slides"].append({
                "number": number, "part": slide_part,
                "text_characters": len(body_text(slide_root)),
                "image_count": sum(1 for _ in elements(slide_root, P_NS, "pic")),
                "image_reference_count": sum(1 for _ in elements(slide_root, A_NS, "blip")),
                "native_chart_count": sum(1 for _ in elements(slide_root, CHART_NS, "chart")),
                "explicit_font_families": sorted(fonts),
                "explicit_font_sizes_pt": sorted(sizes),
                "notes": self.notes_for_slide(slide_part, number),
            })

    def run(self):
        if self.read_package():
            self.read_relationships()
            self.read_presentation()
        self.report["status"] = "fail" if any(
            issue["severity"] == "error" for issue in self.report["issues"]
        ) else "pass"
        return self.report


def audit_pptx(path, require_notes=False, expected_slides=None):
    return Auditor(path, require_notes, expected_slides).run()


def positive_integer(value):
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return result


class AsciiArgumentParser(argparse.ArgumentParser):
    def _print_message(self, message, file=None):
        if message:
            super()._print_message(message.encode("ascii", "backslashreplace").decode("ascii"), file)


def main(argv=None):
    parser = AsciiArgumentParser(description=__doc__)
    parser.add_argument("pptx", type=Path, help="PPTX package to inspect without modification")
    parser.add_argument("--require-notes", action="store_true", help="Fail on missing or empty body notes")
    parser.add_argument("--expected-slides", type=positive_integer)
    parser.add_argument("--output", type=Path, help="Also write the ASCII JSON report to this path")
    args = parser.parse_args(argv)
    if args.output is not None:
        same_file = args.output.resolve() == args.pptx.resolve()
        if args.output.exists() and args.pptx.exists():
            same_file = same_file or args.output.samefile(args.pptx)
        if same_file:
            parser.error("--output must not overwrite the input PPTX")
    report = audit_pptx(args.pptx, args.require_notes, args.expected_slides)
    if args.output is not None:
        try:
            args.output.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="ascii")
        except OSError as exc:
            report["status"] = "fail"
            report["issues"].append({"severity": "error", "code": "report_write_failed",
                                     "message": "Cannot write report: " + str(exc)})
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
