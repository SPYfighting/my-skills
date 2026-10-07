#!/usr/bin/env python3
"""Read one editable-reference layout without requiring vision or a PPT library."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(page=None, full=False):
    catalog = json.loads((ROOT / 'assets/reference-library/catalog.json').read_text(encoding='utf-8'))
    if page is None:
        return [{key: item[key] for key in ('id', 'title', 'family', 'purpose', 'layout')}
                for item in catalog['entries']]
    for item in catalog['entries']:
        if item['id'] == page:
            layout = json.loads((ROOT / item['layout']).read_text(encoding='utf-8'))
            if full:
                return layout
            keys = ('schema_version', 'slide_number', 'reference_id', 'slug', 'title',
                    'family', 'purpose', 'reading_order', 'adaptation_suggestions', 'avoid',
                    'canvas', 'font_design', 'regions', 'relationships', 'unassigned_element_ids', 'counts')
            summary = {key: layout[key] for key in keys if key in layout}
            summary['elements'] = [{key: element[key] for key in
                                    ('id', 'text', 'x', 'y', 'w', 'h', 'font', 'align', 'color', 'zorder', 'role')
                                    if key in element}
                                   for element in layout['elements'] if element.get('text')]
            summary['detail_hint'] = 'Use --full for non-text geometry and complete object attributes.'
            return summary
    raise ValueError('Unknown reference page: ' + str(page))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--page', type=int)
    choice.add_argument('--list', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--full', action='store_true', help='Include all drawing geometry and object attributes')
    args = parser.parse_args()
    try:
        result = read(args.page, full=args.full)
    except (ValueError, OSError) as exc:
        parser.error(str(exc).encode('ascii', 'backslashreplace').decode('ascii'))
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('Wrote reference layout JSON.')
    else:
        print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
