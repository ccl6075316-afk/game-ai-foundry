"""Hash declared viewer evidence and compose a contact sheet; never grant visual approval."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

from view import ROOT, output_path, sha256


def inventory(report_paths):
    reports = []
    captures = []
    seen = set()
    model_hashes = set()
    for value in report_paths:
        path = Path(value).resolve()
        report = json.loads(path.read_text())
        if report.get('kind') != 'fish_asset_viewer_validation':
            raise ValueError(f'Unsupported report kind: {path}')
        model = Path(report['model']).resolve()
        if not model.is_file() or sha256(model) != report.get('model_sha256'):
            raise ValueError(f'Report model missing or changed: {model}')
        model_hashes.add(report['model_sha256'])
        rows = report.get('captures', [])
        if not isinstance(rows, list):
            raise ValueError('Report captures must be an array')
        for row in rows:
            image = Path(row['path'])
            if not image.is_absolute():
                image = path.parent / image
            image = image.resolve()
            if not image.is_file():
                raise ValueError(f'Declared capture missing: {image}')
            if image in seen:
                continue
            seen.add(image)
            digest = sha256(image)
            if row.get('sha256') and row['sha256'] != digest:
                raise ValueError(f'Capture hash mismatch: {image}')
            captures.append({'name': row.get('name', image.stem), 'path': str(image), 'sha256': digest,
                             'bytes': image.stat().st_size, 'source_report': str(path),
                             'model_sha256': report['model_sha256'], 'time_seconds': row.get('time_seconds'),
                             'camera': row.get('camera'), 'visual_review': 'pending'})
        reports.append({'path': str(path), 'sha256': sha256(path), 'technical_ok': report.get('ok') is True,
                        'model': str(model), 'runtime_inventory': report.get('runtime_inventory', {}), 'capture_count': len(rows)})
    if len(model_hashes) > 1:
        raise ValueError('Contact sheet must describe one model hash; split different candidates into separate inventories')
    return {'schema_version': 1, 'kind': 'fish_asset_evidence_validation', 'ok': True, 'status': 'done',
            'next_action': 'human_review', 'visual_review': 'pending', 'reports': reports, 'captures': captures,
            'summary': {'report_count': len(reports), 'capture_count': len(captures),
                        'technical_reports_ok': all(r['technical_ok'] for r in reports),
                        'capture_bytes': sum(r['bytes'] for r in captures), 'model_sha256': next(iter(model_hashes), None)},
            'limitations': ['Inventory and contact sheets do not perform visual review, species acceptance, fish geometry validation or SOP approval']}


def contact_sheet(rows, output, columns=3, thumb_width=400):
    try:
        from PIL import Image, ImageDraw
    except ImportError as error:
        raise ValueError('Contact sheet requires repository Pillow dependency') from error
    if not rows:
        raise ValueError('No declared captures to arrange')
    if not 1 <= columns <= 8 or not 64 <= thumb_width <= 1600:
        raise ValueError('columns must be 1..8 and thumb-width 64..1600')
    height = round(thumb_width * .72)
    cell_height = height + 52
    sheet = Image.new('RGB', (thumb_width * min(columns, len(rows)), cell_height * ((len(rows) + columns - 1) // columns)), '#17212a')
    draw = ImageDraw.Draw(sheet)
    for index, row in enumerate(rows):
        with Image.open(row['path']) as original:
            image = original.convert('RGB')
            image.thumbnail((thumb_width, height), resample=Image.Resampling.NEAREST)
        x = (index % columns) * thumb_width
        y = (index // columns) * cell_height
        sheet.paste(image, (x + (thumb_width-image.width)//2, y + (height-image.height)//2))
        # Labels use an ASCII-safe rendering fallback on minimal Pillow installs.
        label = (str(row['name']) + ' | review pending').encode('ascii', 'replace').decode()
        draw.text((x+8, y+height+5), label, fill='white')
        draw.text((x+8, y+height+23), row['sha256'][:20], fill='#aabbcc')
    sheet.save(output)
    return {'path': str(output), 'sha256': sha256(output), 'width': sheet.width, 'height': sheet.height}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', action='append', required=True, help='Repeat for declared viewer validation reports')
    parser.add_argument('--output', required=True, help='Fresh directory under repository work/, output/, or projects/<project>/experiments/')
    parser.add_argument('--contact-sheet', action='store_true')
    parser.add_argument('--columns', type=int, default=3)
    parser.add_argument('--thumb-width', type=int, default=400)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    result = {'schema_version': 1, 'command': 'portable-evidence', 'stage': 'validate', 'ok': False,
              'status': 'failed', 'next_action': 'fix_input', 'inputs': {'reports': args.report}, 'outputs': [], 'summary': {}, 'failures': []}
    try:
        report = inventory(args.report)
        inputs = [Path(p).resolve() for p in args.report] + [Path(r['path']) for r in report['captures']] + [Path(r['model']) for r in report['reports']]
        output = output_path(args.output, inputs)
        targets = [output / 'evidence.validation.json']
        if args.contact_sheet:
            targets.append(output / 'contact-sheet.png')
        if any(p.exists() for p in targets):
            raise ValueError('Refuse overwriting evidence outputs')
        result['summary'] = report['summary'] | {'planned_outputs': [str(p) for p in targets], 'visual_review': 'pending'}
        if not args.dry_run:
            output.mkdir(parents=True, exist_ok=True)
            if args.contact_sheet:
                report['contact_sheet'] = contact_sheet(report['captures'], targets[1], args.columns, args.thumb_width)
            targets[0].write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
            result['outputs'] = [str(p) for p in targets]
        result.update(ok=True, status='done', next_action='human_review')
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        result['failures'].append({'kind': 'validation', 'code': 'evidence_invalid', 'message': str(error)})
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
