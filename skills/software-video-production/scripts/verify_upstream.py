"""Verify the approved, installed source bytes before running original upstream code."""
import hashlib
import json
from pathlib import Path

PINS=Path(__file__).resolve().parents[1]/'assets/upstream-pins.json'

def verify(name,root,pins=None):
    entries=(pins or json.loads(PINS.read_text(encoding='utf-8')))[name]
    root=Path(root).resolve(strict=True)
    for relative,expected in entries['installed_files'].items():
        path=root/relative
        if not path.resolve().is_relative_to(root) or path.is_symlink():
            raise ValueError('upstream source escapes approved install root')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError(f'upstream source changed: {relative}; review before execution')
    return {'name':name,'root':str(root),'commit':entries['commit'],'verified_files':len(entries['installed_files'])}
