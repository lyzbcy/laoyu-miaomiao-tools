#!/usr/bin/env python3
"""Offline case selection from confirmed segment intent/assets; never renders or downloads."""
import argparse
import json
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / 'assets/advanced-cases.json'


def select(brief):
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    if brief.get('intent') not in catalog['intents']:
        raise ValueError('intent must be one of: ' + ', '.join(catalog['intents']))
    images = brief.get('images', 0)
    if type(images) is not int or images < 0:
        raise ValueError('images must be a nonnegative integer')
    if type(brief.get('has_short_copy', False)) is not bool:
        raise ValueError('has_short_copy must be boolean')
    motion = brief.get('motion', 'normal')
    if motion not in ('normal', 'reduced'):
        raise ValueError('motion must be normal or reduced')
    candidates, rejected = [], []
    for case in catalog['cases']:
        reasons = []
        if brief['intent'] not in case['intents']:
            continue
        if images < case['min_images']:
            reasons.append(f"需要至少{case['min_images']}张可用截图")
        if case['needs_copy'] and not brief.get('has_short_copy', False):
            reasons.append('需要已确认的短文案')
        if motion == 'reduced' and not case['reduced_motion']:
            reasons.append('不适合低运动模式')
        record = {'case_id': case['id'], 'recipe': case['recipe'], 'reason': case['decision'],
                  'reference': 'docs/advanced-cases.md#' + case['anchor']}
        if reasons:
            rejected.append({**record, 'missing_conditions': reasons})
        else:
            candidates.append({**record, 'rank': case['priority'].get(brief['intent'], 0),
                               'shot_overrides': {'reducedMotion': True} if motion == 'reduced' else {}})
    candidates.sort(key=lambda c: -c['rank'])
    return {'catalog_version': catalog['version'], 'brief': brief,
            'selected': candidates[0] if candidates else None, 'alternatives': candidates[1:],
            'rejected': rejected, 'fallback': None if candidates else '直接切镜或保持清晰画面；缺失条件补齐后再选',
            'next': '将case_id写入分镜motion_case；按案例传素材至render_shots.cjs，制作并检查代表段；未自动渲染或混音'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('brief', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = select(json.loads(args.brief.read_text(encoding='utf-8-sig')))
    # Do not silently replace a previously reviewed plan.
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(result, out, ensure_ascii=False, indent=2)
    print(json.dumps(result['selected'], ensure_ascii=False))


if __name__ == '__main__':
    main()
