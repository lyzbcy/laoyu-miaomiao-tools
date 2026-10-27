#!/usr/bin/env python3
"""Export every EDL cut's before/after frames and audiovisual window for human review."""
import argparse
import json
from pathlib import Path
import subprocess


def run(args, capture=False):
    return subprocess.run(args, check=True, capture_output=capture, text=True,
                          encoding='utf-8', errors='replace')


def inspect_cuts(edl, media, output):
    media, output = Path(media).resolve(strict=True), Path(output).resolve()
    if output.exists():
        raise FileExistsError('review output must be a new directory')
    probe = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                            '-of', 'json', str(media)], True).stdout)
    if not any(s.get('codec_type') == 'video' for s in probe['streams']):
        raise ValueError('review media needs a video stream')
    duration = float(probe['format']['duration'])
    if abs(duration - edl['duration_seconds']) > .15:
        raise ValueError('render duration does not match EDL (tolerance 150 ms)')
    # Verify cut timestamps before creating output or decoding.
    for cut in edl['cut_reviews']:
        if not 0 < cut['time'] < duration:
            raise ValueError('cut outside render')
    output.mkdir(parents=True)
    run(['ffmpeg', '-v', 'error', '-i', str(media), '-f', 'null', '-'], True)
    reviews = []
    for index, cut in enumerate(edl['cut_reviews'], 1):
        t, prefix = cut['time'], f'cut-{index:03d}'
        frames = []
        for side, sample in [('before', max(0, t - .08)), ('after', min(duration - .02, t + .08))]:
            path = output / f'{prefix}-{side}.png'
            run(['ffmpeg', '-v', 'error', '-ss', str(sample), '-i', str(media),
                 '-frames:v', '1', str(path)], True)
            if not path.is_file() or not path.stat().st_size:
                raise ValueError('cut frame missing')
            frames.append({'side': side, 'time': sample, 'path': path.name})
        begin, end = max(0, t - .5), min(duration, t + .5)
        window = output / f'{prefix}-window.mp4'
        run(['ffmpeg', '-v', 'error', '-ss', str(begin), '-i', str(media), '-t', str(end - begin),
             '-map', '0:v:0', '-map', '0:a?', '-c:v', 'libx264', '-preset', 'ultrafast',
             '-crf', '20', '-c:a', 'aac', str(window)], True)
        reviews.append({'id': prefix, 'time': t, 'frames': frames, 'window': window.name,
                        'checks': cut['checks']})
    report = {'media': str(media), 'duration_seconds': duration, 'full_decode_pass': True,
              'audio_stream_present': any(s.get('codec_type') == 'audio' for s in probe['streams']),
              'cut_count': len(reviews), 'cuts': reviews, 'ear_listening': False,
              'semantic_preservation': 'pending', 'privacy_mask': 'pending',
              'subtitle_readability': 'pending', 'lip_sync': 'pending',
              'note': 'Frames/windows exported, not automatically judged. Review first/last and trim boundaries too.'}
    (output / 'review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('edl')
    parser.add_argument('media')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = inspect_cuts(json.loads(Path(args.edl).read_text(encoding='utf-8-sig')), args.media, args.output)
    print(f"decoded; exported {result['cut_count']} cut windows; human review pending")


if __name__ == '__main__':
    main()
