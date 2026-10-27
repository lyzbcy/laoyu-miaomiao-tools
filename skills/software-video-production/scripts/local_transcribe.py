#!/usr/bin/env python3
"""Real local faster-whisper adapter. Requires an existing model directory; never downloads."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import subprocess

from transcription_preflight import file_hash, measure


def transcribe(media, model_path, source_id='source', language='zh'):
    from faster_whisper import WhisperModel
    import numpy as np
    media, model_path = Path(media).resolve(strict=True), Path(model_path).resolve(strict=True)
    if not (model_path / 'model.bin').is_file():
        raise ValueError('existing local faster-whisper model.bin required; no download fallback')
    measured = measure(media)
    model = WhisperModel(str(model_path), device='cpu', compute_type='int8', local_files_only=True, cpu_threads=2)
    # Decode through the installed FFmpeg: also avoids installed PyAV API version mismatches.
    decoded = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(media), '-map', '0:a:0',
                              '-ar', '16000', '-ac', '1', '-f', 'f32le', 'pipe:1'],
                             check=True, capture_output=True).stdout
    samples = np.frombuffer(decoded, dtype=np.float32).copy()
    segments, info = model.transcribe(samples, language=language, word_timestamps=True,
                                      beam_size=3, vad_filter=False, condition_on_previous_text=False)
    words, raw = [], []
    for segment in segments:
        raw.append({'start': segment.start, 'end': segment.end, 'text': segment.text})
        for word in segment.words or []:
            if word.end > word.start:
                words.append({'id': f'w-{len(words):04d}', 'source': source_id, 'start': word.start,
                              'end': word.end, 'text': word.word, 'probability': word.probability})
    return {'backend': 'faster-whisper', 'backend_version': importlib.metadata.version('faster-whisper'),
            'model_path': str(model_path), 'model_sha256': file_hash(model_path / 'model.bin'),
            'source_sha256': measured['sha256'], 'duration_seconds': measured['duration_seconds'],
            'language': info.language, 'words': words, 'segments': raw, 'cloud_calls': 0, 'decode_backend': 'local FFmpeg 16k mono float32',
            'ear_listening': False, 'semantic_accuracy': 'pending human correction',
            'word_boundary_accuracy': 'machine estimates; not forced-alignment ground truth',
            'approved_deletions': []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('media')
    parser.add_argument('--model-path', required=True)
    parser.add_argument('--source-id', default='source')
    parser.add_argument('--language', default='zh')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    target = Path(args.output)
    if target.exists():
        raise FileExistsError('use a new transcript output path')
    result = transcribe(args.media, args.model_path, args.source_id, args.language)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"local faster-whisper called; {len(result['words'])} timestamped words; human correction pending")


if __name__ == '__main__':
    main()
