#!/usr/bin/env python3
"""Build reversible keep-only EDL, remapped words and cut-review windows. No media edits."""
import argparse
import json
import math
from pathlib import Path


def finite(value, name, positive=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or
            not math.isfinite(value) or value < 0 or (positive and value == 0)):
        raise ValueError(f'invalid {name}')
    return float(value)


def interval(item, duration):
    start, end = finite(item['start'], 'start'), finite(item['end'], 'end')
    if end <= start or end > duration + 1e-8:
        raise ValueError('invalid source interval')
    return start, end


def build(project):
    sources = project.get('sources', [])
    if not sources or len({s['id'] for s in sources}) != len(sources):
        raise ValueError('sources required with unique IDs')
    duration = {s['id']: finite(s['duration_seconds'], 'duration_seconds', True) for s in sources}
    for source in sources:
        sha = source.get('sha256', '')
        if not source.get('path') or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError('source path and SHA256 required')
    words = project.get('words', [])
    if len({w['id'] for w in words}) != len(words):
        raise ValueError('duplicate word ID')
    for word in words:
        interval(word, duration[word['source']])
        if not isinstance(word.get('text'), str) or not word['text']:
            raise ValueError('word text required')
    candidates = project.get('candidates', [])
    if len({c['id'] for c in candidates}) != len(candidates):
        raise ValueError('duplicate candidate ID')
    deletes = {s['id']: [] for s in sources}
    for candidate in candidates:
        start, end = interval(candidate, duration[candidate['source']])
        if not candidate.get('reason'):
            raise ValueError('candidate deletion reason required')
        if candidate.get('approved') is not True:
            continue
        for word in words:
            if word['source'] != candidate['source']:
                continue
            if any(word['start'] + 1e-8 < cut < word['end'] - 1e-8 for cut in (start, end)):
                raise ValueError('cut crosses word boundary; realign or change decision')
        deletes[candidate['source']].append((start, end, candidate['id']))
    clips, out_words, timeline = [], [], 0.0
    for source in sources:
        sid, cursor = source['id'], 0.0
        previous_end = -1
        keep = []
        for start, end, _ in sorted(deletes[sid]):
            if start < previous_end - 1e-8:
                raise ValueError('overlapping approved deletions')
            if start > cursor:
                keep.append((cursor, start))
            cursor, previous_end = end, end
        if cursor < duration[sid]:
            keep.append((cursor, duration[sid]))
        for start, end in keep:
            clip = {'source': sid, 'source_in': start, 'source_out': end,
                    'timeline_in': timeline, 'timeline_out': timeline + end - start}
            clips.append(clip)
            for word in words:
                if word['source'] == sid and word['start'] >= start - 1e-8 and word['end'] <= end + 1e-8:
                    out_words.append({'id': word['id'], 'source': sid, 'source_start': word['start'],
                                      'source_end': word['end'], 'text': word['text'],
                                      'start': timeline + word['start'] - start,
                                      'end': timeline + word['end'] - start})
            timeline += end - start
    if not clips:
        raise ValueError('edit deletes all media')
    out_words.sort(key=lambda w: (w['start'], w['end'], w['id']))
    cuts = []
    for index in range(1, len(clips)):
        left, right = clips[index - 1], clips[index]
        t = right['timeline_in']
        cuts.append({'id': f'cut-{index:03d}', 'time': t,
                     'timeline_window': [max(0, t - .5), min(timeline, t + .5)],
                     'left_source': left['source'], 'left_out': left['source_out'],
                     'right_source': right['source'], 'right_in': right['source_in'],
                     'checks': {k: 'pending' for k in
                                ('semantics', 'visual', 'audio_seam', 'subtitle', 'privacy_mask', 'lip_sync')}})
    trim_boundaries = [{'source': c['source'], 'source_in': c['source_in'], 'source_out': c['source_out']}
                       for c in clips]
    return {'schema_version': 1, 'revision': project.get('revision', 1),
            'parent_revision': project.get('parent_revision'),
            'sources': sources, 'original_words': words, 'decisions': candidates,
            'clips': clips, 'duration_seconds': timeline, 'remapped_words': out_words,
            'cut_reviews': cuts, 'trim_boundaries': trim_boundaries,
            'rollback': 'Rebuild from sources/original_words with approved=false; originals unchanged.',
            'verification': {'semantic_preservation': 'pending_human_review', 'ear_listening': False,
                             'lip_sync': 'pending', 'platform_retention': 'unknown', 'rendered': False}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    target = Path(args.output)
    if target.exists():
        raise FileExistsError('use a new revision output path')
    result = build(json.loads(Path(args.project).read_text(encoding='utf-8-sig')))
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(f'EDL written: {target}; originals unchanged; semantic/audio checks pending')


if __name__ == '__main__':
    main()
