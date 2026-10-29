"""Generate default Mandarin narration online with the adopted Manbo voice (stdlib only)."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen

ENDPOINT = 'https://api.milorapart.top/apis/mbAIsc'
VOICE = '曼波'


def synthesize(text, output, speed=0, timeout=100):
    text = text.strip()
    if not text or not math.isfinite(speed) or timeout <= 0:
        raise ValueError('Nonempty text, finite speed, and positive timeout required')
    output = Path(output)
    if output.suffix.lower() != '.mp3':
        raise ValueError('Output must use .mp3')
    metadata = output.with_suffix('.mp3.json')
    key = hashlib.sha256(json.dumps([ENDPOINT, VOICE, text, float(speed)], ensure_ascii=False).encode()).hexdigest()
    if output.exists() or metadata.exists():
        if output.is_file() and metadata.is_file():
            old = json.loads(metadata.read_text(encoding='utf8'))
            if old.get('cache_key') == key and old.get('sha256') == hashlib.sha256(output.read_bytes()).hexdigest():
                return {'output': str(output.resolve()), 'cached': True, 'voice': VOICE}
        raise ValueError('Existing output does not match this request; choose another output path')
    query = urlencode({'text': text, 'format': 'mp3', 'speed': speed})
    with urlopen(ENDPOINT + '?' + query, timeout=timeout) as response:
        result = json.load(response)
    if result.get('code') != 200 or not result.get('url'):
        raise ValueError('Online voice service did not return an audio URL')
    if urlparse(result['url']).scheme != 'https':
        raise ValueError('Expected HTTPS audio URL')
    with urlopen(result['url'], timeout=timeout) as response:
        audio = response.read()
    if not (audio.startswith(b'ID3') or (len(audio) > 1 and audio[0] == 255 and audio[1] & 224 == 224)):
        raise ValueError('Service response is not recognizable MP3 audio')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents overwriting an existing or concurrently created output.
    with output.open('xb') as stream:
        stream.write(audio)
    proof = {'provider': ENDPOINT, 'voice': VOICE, 'user_label': '哈基米',
             'text': text, 'speed': speed, 'cache_key': key,
             'sha256': hashlib.sha256(audio).hexdigest(), 'bytes': len(audio)}
    with metadata.open('x', encoding='utf8') as stream:
        json.dump(proof, stream, ensure_ascii=False, indent=2)
    return {'output': str(output.resolve()), 'cached': False, 'voice': VOICE}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--text')
    source.add_argument('--text-file', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--speed', type=float, default=0)
    parser.add_argument('--timeout', type=float, default=100)
    args = parser.parse_args()
    try:
        text = args.text if args.text is not None else args.text_file.read_text(encoding='utf-8-sig')
        print(json.dumps(synthesize(text, args.output, args.speed, args.timeout), ensure_ascii=True))
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, str(error) + '\n')
