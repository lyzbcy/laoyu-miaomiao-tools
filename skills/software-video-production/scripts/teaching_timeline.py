"""Check a planned teaching timeline; this is coverage evidence, not audiovisual QA."""
import argparse
import json
import math
from pathlib import Path

KINDS = {'camera', 'subtitle', 'effect', 'voice', 'background', 'sfx'}


def check(plan, interval=None):
    errors = []
    duration = plan.get('duration')
    valid_time = lambda t: isinstance(t, (int, float)) and not isinstance(t, bool) and math.isfinite(t)
    if not valid_time(duration) or duration <= 0:
        return {'valid': False, 'errors': ['duration must be finite and positive'], 'checkpoints': []}
    segments = plan.get('segments', [])
    events = plan.get('events', [])
    ids = {}
    if not segments:
        errors.append('no speech segments')
    for segment in segments:
        sid = segment.get('id')
        if not isinstance(sid, str) or not sid.strip() or sid in ids:
            errors.append('missing or duplicate segment id: ' + repr(sid))
            continue
        ids[sid] = segment
        start, end = segment.get('start'), segment.get('end')
        if not all(valid_time(x) for x in (start, end)) or not 0 <= start < end <= duration:
            errors.append(sid + ': speech outside final timeline')
        if not all(isinstance(segment.get(k), str) and segment[k].strip() for k in ('zh', 'en')):
            errors.append(sid + ': missing bilingual text')
    covered = set()
    for i, event in enumerate(events):
        sid = event.get('segment_id')
        segment = ids.get(sid)
        at = event.get('at')
        if not segment:
            errors.append(f'event {i}: unknown segment')
            continue
        if event.get('kind') not in KINDS:
            errors.append(f'event {i}: unknown change kind')
            continue
        if not valid_time(at) or not all(valid_time(segment.get(k)) for k in ('start', 'end')) or not segment['start'] <= at < segment['end']:
            errors.append(f'event {i}: change not inside its speech segment')
            continue
        if not all(isinstance(event.get(k), str) and event[k].strip() for k in ('before', 'after', 'reason')) or event.get('before') == event.get('after'):
            errors.append(f'event {i}: describe a meaningful before/after and purpose')
            continue
        covered.add(sid)
    for sid in ids.keys() - covered:
        errors.append(sid + ': no mapped change event')
    points = []
    if interval is not None:
        if not valid_time(interval) or interval <= 0:
            errors.append('attention interval must be finite and positive')
        else:
            if math.ceil(duration / interval) > 100000:
                errors.append('attention interval produces too many checkpoints')
            else:
                for i in range(math.ceil(duration / interval)):
                    at = round(i * interval, 6)
                    active = [sid for sid, s in ids.items() if all(valid_time(s.get(k)) for k in ('start', 'end')) and s['start'] <= at < s['end']]
                    points.append({'at': at, 'segment_ids': active, 'viewer_expectation': '', 'payoff_or_progress': '', 'human_review': None})
    return {'valid': not errors, 'errors': sorted(errors), 'segments': len(ids), 'mapped_segments': len(covered), 'checkpoints': points,
            'scope': 'Planned coverage and bounds only; does not verify translation accuracy, audibility, motion strength, user adoption or retention.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan', type=Path)
    p.add_argument('--attention-interval', type=float)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    result = check(json.loads(args.plan.read_text(encoding='utf-8-sig')), args.attention_interval)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + '\n', encoding='utf-8')
    print(text)
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
