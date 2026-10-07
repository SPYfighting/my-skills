#!/usr/bin/env python3
"""Attach semantic regions and relationships to editable-reference layouts."""
import json
from pathlib import Path
from reference_semantics import get_semantics

ROOT = Path(__file__).resolve().parents[1]


def enrich(layout):
    semantics = get_semantics(layout['reference_id'])
    regions = [dict(region, member_ids=[], text_ids=[]) for region in semantics['regions']]
    unassigned = []
    for element in layout['elements']:
        x, y, w, h = (element[k] for k in ('x', 'y', 'w', 'h'))
        inside = [r for r in regions if x >= r['x'] - .5 and y >= r['y'] - .5
                  and x + w <= r['x'] + r['w'] + .5 and y + h <= r['y'] + r['h'] + .5]
        if not inside:
            # Slight glyph overhang may still belong to a region; large spanning
            # backgrounds/connectors are deliberately left outside region groups.
            inside = [r for r in regions if r['x'] <= x + w / 2 <= r['x'] + r['w']
                      and r['y'] <= y + h / 2 <= r['y'] + r['h'] and w <= r['w'] and h <= r['h']]
        if inside:
            owner = min(inside, key=lambda r: r['w'] * r['h'])
            owner['member_ids'].append(element['id'])
            if element.get('text'):
                owner['text_ids'].append(element['id'])
        else:
            unassigned.append(element['id'])
    layout['schema_version'] = '1.1'
    layout['regions'] = regions
    layout['relationships'] = semantics['relationships']
    layout['unassigned_element_ids'] = unassigned
    layout['region_membership_rule'] = 'Assign each element to the smallest containing semantic region; allow bounded center-based glyph overhang. Spanning backgrounds and connectors remain unassigned and need separate adjustment.'
    for redundant in ('entry', 'read_order', 'adapt'):
        layout.pop(redundant, None)
    return layout


def main():
    catalog = json.loads((ROOT / 'assets/reference-library/catalog.json').read_text(encoding='utf-8'))
    for entry in catalog['entries']:
        file = ROOT / entry['layout']
        layout = enrich(json.loads(file.read_text(encoding='utf-8')))
        file.write_text(json.dumps(layout, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Enriched %d reference layouts.' % len(catalog['entries']))


if __name__ == '__main__':
    main()
