#!/usr/bin/env python3
"""Synthetic-only acceptance pipeline: installed Remotion + local TTS + self-authored EDL render."""
import argparse
from array import array
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import wave

from edit_plan import build
from render_edl import render, run, sha, probe


SCRIPTS = Path(__file__).resolve().parent


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def demo(output, runtime, browser, width=720, fps=30, voice='Microsoft Huihui Desktop'):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('synthetic demo output must be new')
    runtime, browser = Path(runtime).resolve(strict=True), Path(browser).resolve(strict=True)
    output.mkdir(parents=True)
    speech_dir = output / 'speech'
    speech_dir.mkdir()
    phrases = [['先看', '前后', '变化'], ['再看', '关键', '位置'], ['最后', '一步', '一步']]
    word_jobs = [{'text': text, 'output': str(speech_dir / f'word-{scene}-{i}.wav')}
                 for scene, phrase in enumerate(phrases) for i, text in enumerate(phrase)]
    speech_request = output / 'speech-request.json'
    write_json(speech_request, {'voice': voice, 'words': word_jobs,
                                'notice': 'Original synthetic testing words only; local Windows TTS.'})
    windows = Path(os.environ.get('WINDIR', 'C:/Windows'))
    compiler = windows / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    speech_assembly = windows / 'Microsoft.NET/assembly/GAC_MSIL/System.Speech/v4.0_4.0.0.0__31bf3856ad364e35/System.Speech.dll'
    if not compiler.is_file() or not speech_assembly.is_file():
        raise RuntimeError('existing Windows .NET compiler/System.Speech required; no install fallback')
    speech_exe = output / 'synthetic-speech.exe'
    run([str(compiler), '/nologo', '/out:' + str(speech_exe), '/reference:' + str(speech_assembly),
         '/reference:System.Web.Extensions.dll', str(SCRIPTS / 'SyntheticSpeech.cs')])
    run([str(speech_exe), str(speech_request)])
    rate = 48000
    speech, words, shots, candidates = bytearray(), [], [], []
    recipes = ['before_after', 'detail_zoom', 'step_progression']
    titles = ['同一对象，看见变化', '先定位，再看关键处', '一步操作，一次反馈']
    for scene, phrase in enumerate(phrases):
        scene_start = len(speech) / (2 * rate)
        local = bytearray(b'\0\0' * round(.3 * rate))
        for i, text in enumerate(phrase):
            with wave.open(str(speech_dir / f'word-{scene}-{i}.wav'), 'rb') as reader:
                if (reader.getframerate(), reader.getsampwidth(), reader.getnchannels()) != (rate, 2, 1):
                    raise ValueError('local speech format mismatch')
                pcm = reader.readframes(reader.getnframes())
            start = scene_start + len(local) / (2 * rate)
            local.extend(pcm)
            end = scene_start + len(local) / (2 * rate)
            words.append({'id': f'w-{scene}-{i}', 'source': 'synthetic', 'start': start, 'end': end, 'text': text})
            local.extend(b'\0\0' * round(.10 * rate))
        frames = max(fps * 4, math.ceil((len(local) / (2 * rate) + 1) * fps))
        # Choose a frame-aligned duration; 48k audio is exact for the supported 30fps demo.
        scene_samples = round(frames / fps * rate)
        local.extend(b'\0\0' * (scene_samples - len(local) // 2))
        speech.extend(local)
        shots.append({'id': recipes[scene], 'recipe': recipes[scene], 'title': titles[scene], 'frames': frames})
        if scene < 2:
            scene_end = scene_start + frames / fps
            trim_frames = round(.3 * fps)
            candidates.append({'id': f'd-{scene}', 'source': 'synthetic', 'start': scene_end - trim_frames / fps,
                               'end': scene_end, 'reason': 'Generated silent tail only; never an automatic rule for real speech', 'approved': True})
    source_duration = len(speech) / (2 * rate)
    voice_path = output / 'narration.wav'
    with wave.open(str(voice_path), 'wb') as writer:
        writer.setnchannels(1); writer.setsampwidth(2); writer.setframerate(rate); writer.writeframes(speech)
    music = array('h')
    for sample in range(len(speech) // 2):
        t = sample / rate
        notes = (220, 277.18, 329.63) if int(t / 4) % 2 == 0 else (196, 246.94, 293.66)
        fade = min(1, t / .2, (source_duration - t) / .3)
        value = .10 * sum(math.sin(2 * math.pi * frequency * t) for frequency in notes) / 3 * max(0, fade)
        music.append(round(value * 32767))
    music_path = output / 'original-bgm.wav'
    with wave.open(str(music_path), 'wb') as writer:
        writer.setnchannels(1); writer.setsampwidth(2); writer.setframerate(rate); writer.writeframes(music.tobytes())
    config = {'runtime': str(runtime), 'browserExecutable': str(browser), 'width': width, 'height': width * 16 // 9,
              'fps': fps, 'output': str(output / 'shots'), 'shots': shots}
    config_path = output / 'shots-config.json'
    write_json(config_path, config)
    print('Rendering 3 self-authored shots through installed Remotion...', flush=True)
    subprocess.run(['node', str(SCRIPTS / 'render_shots.cjs'), str(config_path)], check=True)
    concat_file = output / 'shot-concat.txt'
    concat_file.write_text(''.join("file '" + (output / 'shots' / (s['id'] + '.mp4')).as_posix().replace("'", "'\\''") + "'\n" for s in shots), encoding='utf-8')
    sequence = output / 'shot-sequence.mp4'
    run(['ffmpeg', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(concat_file), '-c', 'copy', str(sequence)])
    source = output / 'synthetic-source.mkv'
    run(['ffmpeg', '-v', 'error', '-i', str(sequence), '-i', str(voice_path), '-map', '0:v:0', '-map', '1:a:0',
         '-c:v', 'copy', '-c:a', 'pcm_s16le', '-t', str(source_duration), str(source)])
    project = {'revision': 1, 'parent_revision': None, 'require_audio': True,
               'sources': [{'id': 'synthetic', 'path': source.name, 'sha256': sha(source),
                            'duration_seconds': source_duration, 'privacy': {'kind': 'synthetic', 'approved': True}}],
               'words': words, 'candidates': candidates, 'bgm': {'path': music_path.name, 'gain': .5},
               'timing_provenance': 'Exact concatenated per-word Windows TTS file ranges, including tail silence; not ASR or forced alignment.',
               'scope': 'All UI, words and audio generated for this test; no real vlog inputs.'}
    write_json(output / 'project.json', project)
    rollback = dict(project, revision=2, parent_revision=1, candidates=[dict(c, approved=False) for c in candidates])
    write_json(output / 'rollback-project.json', rollback)
    write_json(output / 'rollback-edl.json', build(rollback))
    print('Rendering approved EDL, captions last, ducked original BGM, cut QA...', flush=True)
    result = render(project, output, output / 'edited', width, width * 16 // 9, fps)
    final = Path(result['final'])
    rows = math.ceil(result['duration_seconds'] / 4)
    run(['ffmpeg', '-v', 'error', '-i', str(final), '-vf', f'fps=1,scale=270:480,tile=4x{rows}', '-frames:v', '1', str(output / 'contact-sheet.png')])
    starts = [0, shots[0]['frames']/fps-.3, (shots[0]['frames']+shots[1]['frames'])/fps-.6]
    for index, time in enumerate([starts[i]+shots[i]['frames']/fps*.55 for i in range(3)]):
        run(['ffmpeg', '-v', 'error', '-ss', str(min(time, result['duration_seconds'] - .1)), '-i', str(final),
             '-frames:v', '1', str(output / f'qa-frame-{index}.png')])
    report = {'implementation': 'self-authored shot/EDL adapters; actual installed Remotion/FFmpeg/Windows TTS',
              'upstream_shotcraft_or_video_use_executed': False, 'new_dependencies_installed': False,
              'source_duration': source_duration, 'final': result, 'synthetic_word_count': len(words),
              'rollback_duration': build(rollback)['duration_seconds'], 'actual_tts_voice': voice,
              'cloud_calls': 0, 'real_materials_read': False, 'aesthetic_gain_on_real_material': 'unverified'}
    write_json(output / 'acceptance.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['demo'])
    parser.add_argument('--runtime', required=True)
    parser.add_argument('--browser', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--width', type=int, default=720)
    parser.add_argument('--fps', type=int, default=30)
    parser.add_argument('--voice', default='Microsoft Huihui Desktop')
    args = parser.parse_args()
    if args.fps != 30 or args.width not in (360, 720, 1080):
        raise ValueError('synthetic demo supports width 360/720/1080 and 30fps')
    demo(args.output, args.runtime, args.browser, args.width, args.fps, args.voice)


if __name__ == '__main__':
    main()
