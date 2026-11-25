"""Inspect PPTX structure without changing the document."""
import argparse
import posixpath
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile

P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PKG = '{http://schemas.openxmlformats.org/package/2006/relationships}'


def related(package, part):
    base, filename = posixpath.split(part)
    rels = posixpath.join(base, '_rels', filename + '.rels')
    if rels not in package.namelist():
        return {}
    result = {}
    for item in ET.fromstring(package.read(rels)).iter(PKG + 'Relationship'):
        if item.get('TargetMode') == 'External':
            continue
        target = item.attrib['Target']
        target = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(base, target))
        result[item.attrib['Id']] = (item.attrib.get('Type', ''), target)
    return result


def inspect(path, expected=None, notes=False, clicks=None):
    errors = []
    with ZipFile(path) as package:
        damaged = package.testzip()
        if damaged:
            raise ValueError(f'CRC error: {damaged}')
        part = 'ppt/presentation.xml'
        presentation = ET.fromstring(package.read(part))
        rels = related(package, part)
        slides = [rels[item.attrib[R + 'id']][1] for item in presentation.iter(P + 'sldId')]
        if expected is not None and len(slides) != expected:
            errors.append(f'Expected {expected} slides, got {len(slides)}')
        counts = {}
        for index, slide in enumerate(slides, 1):
            tree = ET.fromstring(package.read(slide))
            counts[index] = sum(1 for node in tree.iter(P + 'cTn') if node.get('nodeType') == 'clickEffect')
            if notes:
                note_parts = [target for kind, target in related(package, slide).values() if kind.endswith('/notesSlide')]
                if not note_parts:
                    errors.append(f'Slide {index}: speaker notes part missing')
                else:
                    note_tree = ET.fromstring(package.read(note_parts[0]))
                    has_body_text = any(node.tag.endswith('}t') and (node.text or '').strip()
                        for shape in note_tree.iter(P + 'sp')
                        if any(n.get('type') == 'body' for n in shape.iter(P + 'ph'))
                        for node in shape.iter())
                    if not has_body_text:
                        errors.append(f'Slide {index}: speaker notes body empty')
        for index, count in (clicks or {}).items():
            if counts.get(index) != count:
                errors.append(f'Slide {index}: expected {count} click effects, got {counts.get(index)}')
        print(f'{len(slides)} slides; native click-effect counts: {counts}')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('deck')
    parser.add_argument('--slides', type=int)
    parser.add_argument('--notes', action='store_true')
    parser.add_argument('--clicks', nargs='+', default=[], metavar='PAGE:COUNT')
    args = parser.parse_args()
    try:
        expected_clicks = {int(a): int(b) for a, b in (item.split(':') for item in args.clicks)}
        errors = inspect(args.deck, args.slides, args.notes, expected_clicks)
    except (OSError, KeyError, ValueError, ET.ParseError) as exc:
        print(f'Invalid or unreadable presentation: {exc}', file=sys.stderr)
        return 1
    for error in errors:
        print(error, file=sys.stderr)
    return int(bool(errors))


if __name__ == '__main__':
    sys.exit(main())
