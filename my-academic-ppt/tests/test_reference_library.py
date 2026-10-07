"""Check reference portability, reproducibility and preview/source pairing."""
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_reference_library as builder
from reference_art import Page
import read_reference
from enrich_reference_layouts import enrich


class ReferenceLibraryTests(unittest.TestCase):
    def test_generator_reproduces_all_published_svg_and_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)
            (dest / 'references').mkdir()
            with patch.object(builder, 'ROOT', dest):
                entries = builder.build()
            self.assertEqual(list(range(1, 38)), [e['id'] for e in entries])
            for relative in ['assets/reference-library/catalog.json', 'references/gallery.md'] + [e['svg'] for e in entries]:
                with self.subTest(path=relative):
                    self.assertEqual((ROOT / relative).read_bytes(), (dest / relative).read_bytes())

    def test_assets_are_self_contained_and_parseable(self):
        catalog = json.loads((ROOT / 'assets/reference-library/catalog.json').read_text())
        for entry in catalog['entries']:
            with self.subTest(page=entry['id']):
                for key in ['family', 'purpose', 'read_order', 'adapt', 'avoid']:
                    self.assertTrue(entry[key])
                self.assertIsInstance(entry['adapt'], list)
                self.assertIsInstance(entry['avoid'], list)
                source = (ROOT / entry['svg']).read_text()
                svg = ET.fromstring(source)
                self.assertEqual('0 0 1280 720', svg.attrib['viewBox'])
                for element in svg.iter():
                    self.assertNotIn(element.tag.split('}')[-1], ['script', 'foreignObject', 'image'])
                    for key, value in element.attrib.items():
                        if key.split('}')[-1] in ('href', 'src'):
                            self.assertTrue(value.startswith('#'))
                data = (ROOT / entry['preview']).read_bytes()
                self.assertEqual(b'\x89PNG\r\n\x1a\n', data[:8])
                self.assertEqual((1280, 720), struct.unpack('>II', data[16:24]))

    def test_preview_pairing_and_contact_sheet(self):
        manifest = json.loads((ROOT / 'assets/reference-library/render-manifest.json').read_text())
        catalog = json.loads((ROOT / 'assets/reference-library/catalog.json').read_text())
        required = {'assets/reference-library/contact-sheet.png'}
        required.add(catalog['pptx'])
        for entry in catalog['entries']:
            required.update((entry['svg'], entry['preview'], entry['layout']))
        self.assertEqual(required, set(manifest['sha256']))
        self.assertTrue(manifest['renderer'])
        for path, digest in manifest['sha256'].items():
            with self.subTest(path=path):
                self.assertEqual(digest, hashlib.sha256((ROOT / path).read_bytes()).hexdigest())

    def test_markdown_local_links_resolve(self):
        files = [ROOT / 'SKILL.md'] + list((ROOT / 'references').glob('*.md'))
        for file in files:
            for target in re.findall(r'\]\(([^)]+)\)', file.read_text()):
                if target.startswith(('https:', 'http:', '#')):
                    continue
                relative = target.split('#')[0]
                with self.subTest(file=file.name, target=target):
                    self.assertTrue((file.parent / relative).is_file())

    def test_user_text_is_escaped_as_text(self):
        page = Page(1, 'A < B & C')
        page.text(20, 20, '<script>not executable</script>')
        svg = ET.fromstring(page.finish())
        self.assertIn('A < B & C', ''.join(svg.itertext()))
        self.assertFalse(any(e.tag.endswith('}script') for e in svg.iter()))

    def test_reference_footers_contain_only_page_numbers(self):
        catalog = json.loads((ROOT / 'assets/reference-library/catalog.json').read_text())
        for entry in catalog['entries']:
            with self.subTest(page=entry['id']):
                svg = ET.fromstring((ROOT / entry['svg']).read_text())
                footer_text = [e for e in svg.iter() if e.tag.endswith('}text')
                               and float(e.attrib['y']) >= 690]
                self.assertEqual([str(entry['id']).zfill(2)],
                                 [''.join(e.itertext()) for e in footer_text])
                self.assertGreater(float(footer_text[0].attrib['x']), 1200)

    def test_native_ppt_matches_machine_readable_layouts(self):
        catalog = json.loads((ROOT / 'assets/reference-library/catalog.json').read_text())
        ns = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
              'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
        with zipfile.ZipFile(ROOT / catalog['pptx']) as archive:
            for entry in catalog['entries']:
                with self.subTest(page=entry['id']):
                    layout = json.loads((ROOT / entry['layout']).read_text())
                    self.assertEqual(entry['id'], layout['slide_number'])
                    self.assertEqual(entry['id'], layout['reference_id'])
                    self.assertEqual(hashlib.sha256((ROOT / entry['svg']).read_bytes()).hexdigest(), layout['source']['sha256'])
                    page = ET.fromstring(archive.read('ppt/slides/slide%d.xml' % entry['id']))
                    shapes = page.findall('.//p:spTree/p:sp', ns)
                    names = {s.find('p:nvSpPr/p:cNvPr', ns).get('name'): s for s in shapes}
                    native = [e for e in layout['elements'] if e['native']]
                    self.assertEqual(len(native), len(shapes))
                    for element in native:
                        shape = names[element['id']]
                        xf = shape.find('p:spPr/a:xfrm', ns)
                        off, ext = xf.find('a:off', ns), xf.find('a:ext', ns)
                        values = [float(off.get('x')), float(off.get('y')), float(ext.get('cx')), float(ext.get('cy'))]
                        for key, actual in zip(['x', 'y', 'w', 'h'], values):
                            self.assertAlmostEqual(element[key], actual / 9525, delta=.002)
                        if element['text'] is not None:
                            actual_text = ''.join(t.text or '' for t in shape.findall('.//a:t', ns))
                            self.assertEqual(element['text'], actual_text)
                            self.assertGreaterEqual(element['x'], -.01)
                            self.assertGreaterEqual(element['y'], -.01)
                            self.assertLessEqual(element['x'] + element['w'], 1280.01)
                            self.assertLessEqual(element['y'] + element['h'], 720.01)
                    self.assertGreater(len([e for e in native if e['text']]), 1)
                    for picture in page.findall('.//p:spTree/p:pic', ns):
                        size = picture.find('p:spPr/a:xfrm/a:ext', ns)
                        self.assertLess(float(size.get('cx')) * float(size.get('cy')), (1280 * 720 * 9525 ** 2) * .8)

    def test_text_only_reader_returns_requested_layout(self):
        entries = read_reference.read()
        self.assertEqual(list(range(1, 38)), [e['id'] for e in entries])
        for number in [3, 26, 37]:
            layout = read_reference.read(number)
            self.assertEqual(number, layout['reference_id'])
            self.assertTrue(layout['reading_order'])
            self.assertTrue(layout['adaptation_suggestions'])
            self.assertTrue(any(e['text'] for e in layout['elements']))
            self.assertTrue(layout['regions'])
            self.assertNotIn('commands', layout['elements'][0])
        with self.assertRaises(ValueError):
            read_reference.read(0)

    def test_semantic_regions_are_reproducible_and_refer_to_real_elements(self):
        for entry in read_reference.read():
            with self.subTest(page=entry['id']):
                layout = read_reference.read(entry['id'], full=True)
                self.assertEqual(layout, enrich(json.loads(json.dumps(layout))))
                element_ids = {e['id'] for e in layout['elements']}
                region_ids = {r['id'] for r in layout['regions']}
                assigned = []
                for region in layout['regions']:
                    self.assertTrue(region['label'])
                    self.assertTrue(region['member_ids'])
                    self.assertTrue(set(region['text_ids']).issubset(region['member_ids']))
                    assigned.extend(region['member_ids'])
                self.assertEqual(len(assigned), len(set(assigned)))
                self.assertEqual(element_ids, set(assigned + layout['unassigned_element_ids']))
                for relation in layout['relationships']:
                    self.assertIn(relation['from'], region_ids)
                    self.assertIn(relation['to'], region_ids)


if __name__ == '__main__':
    unittest.main()
