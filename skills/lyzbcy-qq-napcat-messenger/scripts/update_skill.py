"""Daily best-effort update of this skill. Standard library only; silent CLI."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote
from urllib.request import Request, urlopen

BASE = "https://raw.githubusercontent.com/lyzbcy/laoyu-miaomiao-tools/main/skills/"


def version(text):
    match = re.search(r"^  version: ['\"]?(\d+\.\d+\.\d+)['\"]?\s*$", text, re.M)
    if not match:
        raise ValueError("missing semver")
    return tuple(map(int, match[1].split('.')))


def safe_path(root, relative):
    if relative == 'runtime.local.json':
        raise ValueError('private machine configuration is unmanaged')
    if not isinstance(relative, str) or '\\' in relative or ':' in relative:
        raise ValueError("invalid path")
    p = PurePosixPath(relative)
    if p.is_absolute() or not p.parts or any(x in ('..', '.') or x.startswith('.') for x in p.parts):
        raise ValueError("invalid path")
    target = root.joinpath(*p.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("escaped path")
    for part in [target, *target.parents]:
        if part == root:
            break
        if part.is_symlink():
            raise ValueError("managed symlink")
    return target


def write_json(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    os.replace(temp, path)


def recover(root):
    journal = root / '.update-journal.json'
    if not journal.exists():
        return
    data = json.loads(journal.read_text(encoding='utf-8'))
    backup = root / '.update-backup'
    for rel, existed in data.items():
        target = safe_path(root, rel)
        if existed:
            source = safe_path(backup, rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        else:
            target.unlink(missing_ok=True)
    journal.unlink()
    shutil.rmtree(backup)


def install(root, files):
    """Stage and back up the complete set; restore old files on failure."""
    backup = root / '.update-backup'
    backup.mkdir(exist_ok=False)
    old = {}
    try:
        with tempfile.TemporaryDirectory(prefix='.update-stage-', dir=root) as stage:
            stage = Path(stage)
            for rel, content in files.items():
                target = safe_path(root, rel)
                dest = safe_path(stage, rel)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)
                old[rel] = target.is_file()
                if target.exists() and not target.is_file():
                    raise ValueError('non-file target')
                if old[rel]:
                    saved = safe_path(backup, rel)
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, saved)
            write_json(root / '.update-journal.json', old)
            # Entry point changes last. Unmanaged local files are never removed.
            for rel in sorted(files, key=lambda x: (x == 'SKILL.md', x)):
                target = safe_path(root, rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(safe_path(stage, rel), target)
            (root / '.update-journal.json').unlink()
    except BaseException:
        if (root / '.update-journal.json').exists():
            recover(root)
        else:
            shutil.rmtree(backup)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def check(root, fetch=None, today=None):
    root = Path(root).resolve()
    today = today or dt.date.today().isoformat()
    state = root / '.update-check.json'
    lock = root / '.update-check.lock'
    # Author's source checkout is maintained by the release process.
    if any((p / '.git').exists() for p in [root, *root.parents]):
        return 'source_checkout'
    if lock.exists() and time.time() - lock.stat().st_mtime > 120:
        lock.unlink(missing_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        return 'busy'
    result = 'failed'
    try:
        recover(root)
        try:
            if json.loads(state.read_text(encoding='utf-8')).get('last_check') == today:
                result = 'already_checked'
                return result
        except (OSError, ValueError):
            pass
        deadline = time.monotonic() + 60
        def remote(relative):
            if time.monotonic() >= deadline:
                raise TimeoutError()
            if fetch:
                return fetch(relative)
            url = BASE + quote(root.name) + '/' + quote(relative, safe='/')
            req = Request(url, headers={'User-Agent': 'miaomiao-skill-updater/1'})
            with urlopen(req, timeout=min(4, max(.1, deadline-time.monotonic()))) as response:
                data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise ValueError('oversized file')
            return data
        manifest_raw = remote('update.json')
        manifest = json.loads(manifest_raw)
        current = version((root/'SKILL.md').read_text(encoding='utf-8-sig'))
        incoming = tuple(map(int, manifest['version'].split('.')))
        if len(incoming) != 3 or manifest['name'] != root.name:
            raise ValueError('wrong manifest')
        if incoming <= current:
            result = 'current'
        else:
            hashes = manifest['sha256']
            if not isinstance(hashes, dict) or not 1 <= len(hashes) <= 100 or 'SKILL.md' not in hashes:
                raise ValueError('invalid files')
            files = {}
            total = 0
            for rel, digest in hashes.items():
                safe_path(root, rel)
                if not re.fullmatch(r'[a-f0-9]{64}', digest):
                    raise ValueError('invalid hash')
                content = remote(rel)
                total += len(content)
                if total > 10_000_000 or hashlib.sha256(content).hexdigest() != digest:
                    raise ValueError('incomplete release')
                files[rel] = content
            if version(files['SKILL.md'].decode('utf-8')) != incoming:
                raise ValueError('version mismatch')
            files['update.json'] = manifest_raw
            install(root, files)
            result = 'updated'
    except Exception:
        result = 'failed'
    finally:
        try:
            # Includes failures: retry on the next day's first use.
            if result != 'failed' or not (root/'.update-journal.json').exists():
                write_json(state, {'last_check': today, 'result': result})
        finally:
            lock.unlink(missing_ok=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--background', action='store_true')
    args = parser.parse_args()
    try:
        if args.background:
            options = {}
            if os.name == 'nt':
                options['creationflags'] = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
            else:
                options['start_new_session'] = True
            subprocess.Popen([sys.executable, str(Path(__file__).resolve())],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, **options)
        else:
            check(Path(__file__).resolve().parent.parent)
    except Exception:
        pass  # Update availability never blocks use of the installed version.


if __name__ == '__main__':
    main()
