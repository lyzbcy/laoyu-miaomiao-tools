#!/usr/bin/env python3
"""Self-authored EDL -> actual segments -> concat -> duck/mix -> captions-last renderer."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import unicodedata

from edit_plan import build
from cut_review import inspect_cuts


def run(command, cwd=None):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        raise RuntimeError(result.stderr[-5000:])
    return result


def probe(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]).stdout)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def clock(t, ass=False):
    rate = 100 if ass else 1000
    units = max(0, round(t * rate))
    hours, rest = divmod(units, 3600 * rate)
    minutes, rest = divmod(rest, 60 * rate)
    seconds, fraction = divmod(rest, rate)
    return f'{hours}:{minutes:02}:{seconds:02}.{fraction:02}' if ass else f'{hours:02}:{minutes:02}:{seconds:02},{fraction:03}'


def captions(edl, width, height, output):
    cues, current, current_clip = [], [], None
    def flush():
        if current:
            cues.append({'start': current[0]['start'], 'end': current[-1]['end'],
                         'text': ''.join(w['text'] for w in current), 'word_ids': [w['id'] for w in current]})
            current.clear()
    for word in edl['remapped_words']:
        if not 0 <= word['start'] < word['end'] <= edl['duration_seconds'] + 1e-7:
            raise ValueError('subtitle outside EDL')
        clip_id = next((i for i, c in enumerate(edl['clips']) if word['start'] >= c['timeline_in'] - 1e-7 and word['end'] <= c['timeline_out'] + 1e-7), None)
        if clip_id is None:
            raise ValueError('subtitle crosses a cut')
        if current and (clip_id != current_clip or word['start'] - current[-1]['end'] > .32 or
                        len(''.join(w['text'] for w in current)) + len(word['text']) > 12):
            flush()
        current.append(word)
        current_clip = clip_id
    flush()
    font = round(width / 720 * 46)
    margin = round(height / 1280 * 178)
    header = f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Main,Microsoft YaHei,{font},&H00FFFFFF,&H0000FFFF,&H00101A2A,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,54,54,{margin},1
[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
'''
    srt, lines = [], []
    for i, cue in enumerate(cues, 1):
        text = cue['text'].replace('\\', '＼').replace('{', '｛').replace('}', '｝').replace('\r', '').replace('\n', ' ')
        # Conservative Unicode width check; final frame reading remains a human check.
        text_width = sum(1 if unicodedata.east_asian_width(c) in ('W', 'F') else .58 for c in text) * font
        if text_width > width - 108:
            raise ValueError('subtitle too wide; shorten/rephrase cue before render')
        lines.append(f"Dialogue: 0,{clock(cue['start'],True)},{clock(cue['end'],True)},Main,,0,0,0,,{text}")
        srt.append(f"{i}\n{clock(cue['start'])} --> {clock(cue['end'])}\n{text}\n")
    (output / 'captions.ass').write_text(header + '\n'.join(lines) + '\n', encoding='utf-8-sig')
    (output / 'captions.srt').write_text('\n'.join(srt), encoding='utf-8')
    return cues


def mean_volume(path):
    result = run(['ffmpeg', '-v', 'info', '-i', str(path), '-vn', '-af', 'volumedetect', '-f', 'null', '-'])
    match = re.search(r'mean_volume:\s*(-?inf|[-\d.]+) dB', result.stderr)
    return float(match.group(1)) if match else None


def render(project, project_dir, output, width=720, height=1280, fps=30):
    if (not isinstance(width, int) or not isinstance(height, int) or width % 2 or height % 2
            or width < 160 or height < 160 or not isinstance(fps, int) or not 12 <= fps <= 60):
        raise ValueError('invalid dimensions/fps')
    edl = build(project)
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('use a new output revision')
    project_dir = Path(project_dir).resolve()
    sources = {}
    require_audio = project.get('require_audio', True)
    for source in project['sources']:
        path = (project_dir / source['path']).resolve(strict=True)
        if sha(path) != source['sha256']:
            raise ValueError('source hash changed; update manifest and review again')
        privacy = source.get('privacy', {})
        if not (privacy.get('kind') == 'synthetic' or
                (privacy.get('rasterized') is True and privacy.get('approved') is True
                 and privacy.get('redacted_sha256') == source['sha256'])):
            raise ValueError('privacy gate: supply synthetic source or approved raster-redacted derivative hash')
        info = probe(path)
        if not any(s.get('codec_type') == 'video' for s in info['streams']):
            raise ValueError('source has no video')
        if abs(float(info['format']['duration']) - source['duration_seconds']) > .15:
            raise ValueError('source duration changed')
        has_audio = any(s.get('codec_type') == 'audio' for s in info['streams'])
        if require_audio and not has_audio:
            raise ValueError('required source audio missing')
        sources[source['id']] = (path, has_audio)
    # This renderer keeps the EDL time mapping exact: callers must choose frame-grid cuts.
    for clip in edl['clips']:
        if any(abs(t * fps - round(t * fps)) > 1e-4 for t in (clip['source_in'], clip['source_out'])):
            raise ValueError('cut is off frame grid; review/snap source boundaries explicitly')
    output.mkdir(parents=True)
    (output / 'edl.json').write_text(json.dumps(edl, ensure_ascii=False, indent=2), encoding='utf-8')
    pieces = []
    for i, clip in enumerate(edl['clips']):
        source, has_audio = sources[clip['source']]
        begin, end = clip['source_in'], clip['source_out']
        length = end - begin
        piece = output / f'clip-{i:03d}.mkv'
        command = ['ffmpeg', '-v', 'error', '-i', str(source)]
        if not has_audio:
            command += ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo']
        vf = (f'trim=start={begin}:end={end},setpts=PTS-STARTPTS,'
              f'scale={width}:{height}:force_original_aspect_ratio=decrease,'
              f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps},format=yuv420p')
        af = (f'atrim=start={begin if has_audio else 0}:duration={length},asetpts=PTS-STARTPTS,'
              f'aresample=48000,apad,atrim=duration={length},'
              f'afade=t=in:d=0.006,afade=t=out:st={max(0,length-.006)}:d=0.006')
        command += ['-map', '0:v:0', '-map', '0:a:0' if has_audio else '1:a:0', '-vf', vf, '-af', af,
                    '-t', str(length), '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                    '-c:a', 'pcm_s16le', str(piece)]
        run(command)
        pieces.append(piece)
    listing = output / 'concat.txt'
    listing.write_text(''.join("file '" + p.as_posix().replace("'", "'\\''") + "'\n" for p in pieces), encoding='utf-8')
    base = output / 'base.mkv'
    run(['ffmpeg', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(listing), '-c', 'copy', str(base)])
    cues = captions(edl, width, height, output)
    bgm = project.get('bgm')
    duck_path = None
    if bgm:
        music = (project_dir / bgm['path']).resolve(strict=True)
        gain = float(bgm.get('gain', .18))
        if not math.isfinite(gain) or not 0 < gain <= 1:
            raise ValueError('invalid BGM gain')
        if mean_volume(music) is None or mean_volume(music) < -80:
            raise ValueError('required BGM branch is silent')
        duck_path = output / 'ducked-bgm.wav'
        graph = (f'[1:a]apad,atrim=duration={edl["duration_seconds"]},volume={gain}[music];'
                 '[music][0:a]sidechaincompress=threshold=0.025:ratio=6:attack=20:release=180[duck]')
        run(['ffmpeg', '-v', 'error', '-i', str(base), '-i', str(music), '-filter_complex', graph,
             '-map', '[duck]', '-c:a', 'pcm_s16le', str(duck_path)])
        if mean_volume(duck_path) is None or mean_volume(duck_path) < -85:
            raise ValueError('ducked BGM branch is silent')
    final = output / 'final.mp4'
    command = ['ffmpeg', '-v', 'error', '-i', str(base)]
    if duck_path:
        command += ['-i', str(duck_path), '-filter_complex',
                    '[0:a][1:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=false[mix]', '-map', '0:v:0', '-map', '[mix]']
    else:
        command += ['-map', '0:v:0', '-map', '0:a:0']
    command += ['-vf', 'subtitles=filename=captions.ass', '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', str(final)]
    run(command, cwd=output)
    actual = probe(final)
    video = next(s for s in actual['streams'] if s['codec_type'] == 'video')
    assert (video['width'], video['height']) == (width, height)
    assert abs(float(Fraction(video['avg_frame_rate'])) - fps) < .001
    volume = mean_volume(final)
    if require_audio and (volume is None or volume < -80):
        raise ValueError('required final audio is silent')
    cut_check = inspect_cuts(edl, final, output / 'cut-review')
    report = {'implementation': 'self-authored; not video-use renderer', 'final': str(final),
              'dimensions': [width, height], 'fps': fps, 'duration_seconds': float(actual['format']['duration']),
              'expected_duration': edl['duration_seconds'], 'caption_cues': len(cues),
              'caption_bounds_pass': True, 'subtitle_file': str(output / 'captions.srt'),
              'segment_count': len(pieces), 'full_decode_pass': cut_check['full_decode_pass'],
              'audio_present': cut_check['audio_stream_present'], 'mean_volume_db': volume,
              'ducked_bgm_mean_db': mean_volume(duck_path) if duck_path else None,
              'cut_windows': cut_check['cut_count'], 'ear_listening': False,
              'human_semantic_review': 'pending', 'aesthetic_quality': 'not established',
              'source_hashes_verified': True, 'privacy_gate_passed': True}
    (output / 'render-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--output', required=True)
    parser.add_argument('--width', type=int, default=720)
    parser.add_argument('--height', type=int, default=1280)
    parser.add_argument('--fps', type=int, default=30)
    args = parser.parse_args()
    project = Path(args.project).resolve(strict=True)
    result = render(json.loads(project.read_text(encoding='utf-8-sig')), project.parent, args.output, args.width, args.height, args.fps)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
