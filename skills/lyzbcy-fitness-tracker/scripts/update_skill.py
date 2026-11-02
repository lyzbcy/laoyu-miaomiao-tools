"""Daily, background, best-effort skill updates. Never updates the user's training workspace."""
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

NAME = 'lyzbcy-fitness-tracker'
REPOSITORY = 'lyzbcy/laoyu-miaomiao-tools'
API = 'https://api.github.com/repos/'+REPOSITORY+'/releases/tags/'
RAW = 'https://raw.githubusercontent.com/'+REPOSITORY+'/'
PRIVATE = {'records.jsonl','config.json','exercises.json','publish-state.json','runtime.local.json'}
TEXT = {'.md','.py','.json','.jsonl','.txt','.sh','.html','.css','.js','.yml','.yaml'}


def version(value):
    m = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)', value)
    if not m:
        raise ValueError('invalid semantic version')
    return tuple(map(int, m.groups()))


def local_version(root):
    text = (root/'SKILL.md').read_text(encoding='utf-8-sig')
    m = re.search(r'^  version:\s*["\']?(\d+\.\d+\.\d+)["\']?\s*$', text, re.M)
    if not m:
        raise ValueError('missing version')
    return version(m[1])


def safe_path(root, relative):
    if not isinstance(relative, str) or '\\' in relative or ':' in relative:
        raise ValueError('invalid managed path')
    p = PurePosixPath(relative)
    if p.is_absolute() or not p.parts or any(x in ('.','..') for x in relative.split('/')):
        raise ValueError('unsafe path')
    if any(x.startswith('.') for x in p.parts) and relative != '.gitignore':
        raise ValueError('private path')
    if p.name in PRIVATE or any(x in {'workspace','posters','contributions','.git'} for x in p.parts):
        raise ValueError('private data is unmanaged')
    target = root.joinpath(*p.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError('escaped path')
    for part in [target, *target.parents]:
        if part == root:
            break
        if part.is_symlink():
            raise ValueError('managed symlink')
    return target


def canonical(relative, data):
    return data.replace(b'\r\n', b'\n') if Path(relative).suffix in TEXT or relative in {'LICENSE','.gitignore'} else data


def write_state(path, value):
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    os.replace(tmp, path)


def recover(root):
    journal = root/'.update-journal.json'
    if not journal.exists():
        return
    backup = root/'.update-backup'
    old = json.loads(journal.read_text(encoding='utf-8'))
    for rel, existed in old.items():
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
    backup = root/'.update-backup'
    backup.mkdir(exist_ok=False)
    old = {}
    try:
        with tempfile.TemporaryDirectory(prefix='.update-stage-', dir=root) as folder:
            stage = Path(folder)
            for rel, content in files.items():
                target = safe_path(root, rel)
                if target.exists() and not target.is_file():
                    raise ValueError('non-file target')
                dest = safe_path(stage, rel)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)
                old[rel] = target.exists()
                if old[rel]:
                    saved = safe_path(backup, rel)
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target, saved)
            write_state(root/'.update-journal.json', old)
            for rel in sorted(files, key=lambda x: (x == 'SKILL.md', x)):
                target = safe_path(root, rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(safe_path(stage, rel), target)
            (root/'.update-journal.json').unlink()
    except BaseException:
        if (root/'.update-journal.json').exists():
            recover(root)
        else:
            shutil.rmtree(backup)
        raise
    shutil.rmtree(backup)


def source_checkout(root):
    return any((p/'.git').exists() for p in [root,*root.parents])


def check(root, fetch=None, release=None, today=None, force=False):
    root = Path(root).resolve()
    today = today or dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date().isoformat()
    if source_checkout(root):
        return 'source_checkout'
    state_path, lock = root/'.update-check.json', root/'.update-check.lock'
    if lock.exists() and time.time()-lock.stat().st_mtime > 600:
        lock.unlink(missing_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        return 'busy'
    result, state = 'failed', {}
    try:
        recover(root)
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding='utf-8'))
        if not force and state.get('last_attempt') == today:
            result = 'already_checked'
            return result
        deadline = time.monotonic()+180
        def get(url, limit):
            if time.monotonic() >= deadline:
                raise TimeoutError('deadline')
            req = Request(url, headers={'User-Agent': NAME+'-updater/1','Cache-Control':'no-cache'})
            with urlopen(req, timeout=min(10, max(.1,deadline-time.monotonic()))) as response:
                data = response.read(limit+1)
            if len(data)>limit:
                raise ValueError('oversized response')
            return data
        def remote(rel, revision='main'):
            return fetch(rel, revision) if fetch else get(RAW+revision+'/skills/'+NAME+'/'+quote(rel,safe='/'),24_000_000)
        raw = remote('update.json')
        manifest = json.loads(raw)
        incoming = version(manifest['version'])
        if manifest['name'] != NAME:
            raise ValueError('wrong skill')
        tag = manifest['release_tag']
        if not re.fullmatch(r'v\d+\.\d+\.\d+', tag):
            raise ValueError('invalid release tag')
        published = release(tag) if release else json.loads(get(API+tag, 2_000_000))
        revision = published.get('target_commitish','')
        if published.get('draft') or published.get('prerelease') or published.get('tag_name') != tag or not re.fullmatch('[a-f0-9]{40}', revision):
            raise ValueError('not a pinned stable release')
        if not any(a.get('name') == NAME+'.zip' and a.get('state') == 'uploaded' for a in published.get('assets',[])):
            raise ValueError('release package unavailable')
        if remote('update.json', revision) != raw:
            raise ValueError('release manifest mismatch')
        current = local_version(root)
        if incoming <= current:
            result = 'current'
        else:
            hashes = manifest['sha256']
            if not isinstance(hashes,dict) or not 1<=len(hashes)<=150 or 'SKILL.md' not in hashes or 'update.json' in hashes:
                raise ValueError('invalid file manifest')
            previous = root/'update.json'
            previous = json.loads(previous.read_text(encoding='utf-8')) if previous.is_file() else {}
            for rel, digest in previous.get('sha256',{}).items():
                target = safe_path(root,rel)
                if target.exists() and hashlib.sha256(canonical(rel,target.read_bytes())).hexdigest() != digest:
                    raise ValueError('locally customized managed file; preserve installed version')
            files, total = {}, 0
            for rel, digest in hashes.items():
                target = safe_path(root,rel)
                if not re.fullmatch('[a-f0-9]{64}',digest):
                    raise ValueError('invalid checksum')
                cached = canonical(rel,target.read_bytes()) if target.is_file() else None
                content = cached if cached is not None and hashlib.sha256(cached).hexdigest()==digest else remote(rel,revision)
                total += len(content)
                if total>64_000_000 or hashlib.sha256(content).hexdigest()!=digest:
                    raise ValueError('incomplete or corrupted update')
                if rel.endswith('.py'):
                    compile(content, rel, 'exec')
                files[rel] = content
            with tempfile.TemporaryDirectory() as temp:
                test = Path(temp); (test/'SKILL.md').write_bytes(files['SKILL.md'])
                if local_version(test) != incoming:
                    raise ValueError('version mismatch')
            files['update.json'] = raw
            changed = {rel:content for rel,content in files.items()
                       if not safe_path(root,rel).is_file() or canonical(rel,safe_path(root,rel).read_bytes())!=content}
            install(root,changed)
            result = 'updated'
        state['last_success'] = today
    except Exception:
        result = 'failed'
    finally:
        try:
            if result != 'already_checked':
                state.update(last_attempt=today, result=result)
                write_state(state_path,state)
        finally:
            lock.unlink(missing_ok=True)
    return result


def start_background(root=None):
    """Returns immediately; the worker owns locking, attempts and recovery."""
    root = Path(root or Path(__file__).resolve().parents[1])
    try:
        if source_checkout(root):
            return
        state = root/'.update-check.json'
        today = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date().isoformat()
        if state.exists() and not (root/'.update-journal.json').exists() and json.loads(state.read_text(encoding='utf-8')).get('last_attempt')==today:
            return
        options = {'creationflags': subprocess.CREATE_NO_WINDOW|subprocess.DETACHED_PROCESS} if os.name=='nt' else {'start_new_session':True}
        subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--root',str(root)],stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,**options)
    except Exception:
        pass


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',default=str(Path(__file__).resolve().parents[1]))
    p.add_argument('--background',action='store_true')
    p.add_argument('--force',action='store_true',help='手动查新，绕过当天标记')
    p.add_argument('--json',action='store_true')
    a=p.parse_args()
    try:
        result=start_background(a.root) if a.background else check(a.root,force=a.force)
    except Exception:
        result='failed'
    if a.json:
        print(json.dumps({'status':result},ensure_ascii=False))


if __name__=='__main__':
    main()
