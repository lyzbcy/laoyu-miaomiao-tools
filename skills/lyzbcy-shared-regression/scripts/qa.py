"""Local comparison and append-only regression records. Python 3.10+, stdlib."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import sqlite3
import sys
from urllib.parse import urlparse, parse_qs
from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler, Request
from urllib.error import HTTPError, URLError
import uuid

ASSETS = Path(__file__).resolve().parent.parent / 'assets'


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def valid_url(value):
    u = urlparse(value)
    if u.scheme not in {'http', 'https'} or not u.hostname or u.username or u.password:
        raise ValueError('仅支持不含凭据的 http/https URL')
    return value


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()

    @contextmanager
    def db(self):
        if not self.root.is_dir():
            raise ValueError('项目目录不存在，请先 init')
        db = sqlite3.connect(self.root / 'regression.sqlite3', timeout=15)
        db.row_factory = sqlite3.Row
        db.executescript('''
        CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, build TEXT NOT NULL, created TEXT NOT NULL, cases TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY, run TEXT NOT NULL, case_id TEXT NOT NULL, point TEXT NOT NULL, actor TEXT NOT NULL, name TEXT NOT NULL, status TEXT NOT NULL, note TEXT NOT NULL, created TEXT NOT NULL);
        ''')
        try:
            with db:
                yield db
        finally:
            db.close()

    def cases(self):
        cases = json.loads((self.root / 'cases.json').read_text(encoding='utf-8-sig'))
        if not isinstance(cases, list) or not cases or len(cases) > 500:
            raise ValueError('cases.json 需要1至500条用例')
        ids = set()
        for c in cases:
            if not isinstance(c.get('id'), str) or c['id'] in ids or not c.get('title'):
                raise ValueError('用例 ID 必须唯一且有标题')
            ids.add(c['id'])
            points = c.get('checkpoints', [])
            if not points or len({p['id'] for p in points}) != len(points):
                raise ValueError('检查点必须非空且 ID 唯一')
            if c.get('url'):
                valid_url(c['url'])
            for ref in c.get('references', []):
                valid_url(ref['url'])
            for p in points:
                if p.get('mode') not in {'human', 'auto'} or not p.get('title'):
                    raise ValueError('检查点需要标题及 human/auto 模式')
                if p['mode'] == 'auto':
                    valid_url(p['http']['url'])
        return cases

    def create(self, build):
        if not isinstance(build, str) or not build.strip() or len(build) > 300:
            raise ValueError('填写实际被测版本，未知需明确注明')
        cases = self.cases()
        key = 'run-' + uuid.uuid4().hex[:12]
        with self.db() as db:
            db.execute('INSERT INTO runs VALUES(?,?,?,?)', (key, build, stamp(), json.dumps(cases, ensure_ascii=False)))
        return {'id': key}

    def frozen(self, run):
        with self.db() as db:
            row = db.execute('SELECT * FROM runs WHERE id=?', (run,)).fetchone()
        if not row:
            raise ValueError('批次不存在')
        return dict(row)

    def record(self, run, case, point, actor, name, status, note):
        if actor not in {'human', 'ai', 'automation'} or status not in {'passed', 'failed', 'blocked'}:
            raise ValueError('身份或状态无效')
        if not isinstance(name, str) or not name.strip() or len(name) > 100 or not isinstance(note, str) or not note.strip() or len(note) > 6000:
            raise ValueError('填写执行者及实际观察，名称≤100字、说明≤6000字')
        c = next((c for c in json.loads(self.frozen(run)['cases']) if c['id'] == case), None)
        p = next((p for p in c['checkpoints'] if p['id'] == point), None) if c else None
        if not p or (actor == 'automation' and p['mode'] != 'auto'):
            raise ValueError('检查点不属于批次或需要人工复核')
        key = uuid.uuid4().hex
        with self.db() as db:
            db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?,?)', (key, run, case, point, actor, name.strip(), status, note.strip(), stamp()))
        return {'id': key}

    def summary(self, run, case=None):
        frozen = self.frozen(run)
        current = {c['id']: digest(c) for c in self.cases()}
        with self.db() as db:
            history = [dict(a) for a in db.execute('SELECT * FROM attempts WHERE run=? ORDER BY rowid', (run,))]
        results = []
        for c in json.loads(frozen['cases']):
            if case and c['id'] != case:
                continue
            points = []
            for p in c['checkpoints']:
                attempts = [a for a in history if a['case_id'] == c['id'] and a['point'] == p['id']]
                latest = {(a['actor'], a['name']): a for a in attempts}
                states = {a['status'] for a in latest.values()}
                state = 'conflict' if 'passed' in states and 'failed' in states else next((s for s in ['failed', 'blocked', 'passed'] if s in states), 'pending')
                points.append({**p, 'status': state, 'history': attempts})
            states = {p['status'] for p in points}
            state = next((s for s in ['conflict', 'failed', 'blocked'] if s in states), 'passed' if states == {'passed'} else 'partial' if 'passed' in states else 'pending')
            if current.get(c['id']) != digest(c):
                state = 'stale'
            results.append({**c, 'status': state, 'checkpoints': points})
        frozen.pop('cases')
        counts = {s: sum(c['status'] == s for c in results) for s in ['pending', 'partial', 'passed', 'failed', 'blocked', 'conflict', 'stale']}
        return {**frozen, 'counts': counts, 'cases': results if case else [{'id': c['id'], 'title': c['title'], 'status': c['status']} for c in results]}

    def run(self, run, ids):
        selected = [c for c in json.loads(self.frozen(run)['cases']) if c['id'] in ids]
        if set(ids) != {c['id'] for c in selected}:
            raise ValueError('包含本批次以外用例')
        if any(c['status'] == 'stale' for c in self.summary(run)['cases'] if c['id'] in ids):
            raise ValueError('用例已变化，请创建新批次')
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        opener = build_opener(ProxyHandler({}), NoRedirect())
        checked = 0
        for c in selected:
            for p in c['checkpoints']:
                if p['mode'] != 'auto':
                    continue
                h = p['http']
                status, note = 'blocked', '网络或执行条件不足'
                try:
                    request = Request(valid_url(h['url']), headers={'User-Agent': 'shared-regression/0.1'})
                    try:
                        response = opener.open(request, timeout=8)
                    except HTTPError as exc:
                        response = exc
                    with response:
                        code = response.code
                        raw = response.read(1_048_577)
                    if len(raw) > 1_048_576:
                        note = '响应超过1MiB，未完成断言'
                    else:
                        ok = code == h.get('status', 200) and h.get('contains', '') in raw.decode('utf-8', errors='replace')
                        status, note = ('passed' if ok else 'failed'), f'HTTP {code}；状态及配置正文断言' + ('符合' if ok else '不符')
                except (URLError, OSError, ValueError) as exc:
                    note = '执行阻塞：' + type(exc).__name__
                self.record(run, c['id'], p['id'], 'automation', 'HTTP GET执行器', status, note)
                checked += 1
        return {'checked': checked, 'summary': self.summary(run)}


def serve(store, port):
    origin = f'http://127.0.0.1:{port}'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, value, status=200):
            raw = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.headers.get('Host') != f'127.0.0.1:{port}':
                return self.reply({'error': '仅允许本机地址'}, 403)
            try:
                u = urlparse(self.path)
                if u.path == '/':
                    raw = (store.root / 'index.html').read_bytes()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(raw)))
                    self.end_headers()
                    return self.wfile.write(raw)
                if u.path == '/api/runs':
                    with store.db() as db:
                        return self.reply([dict(r) for r in db.execute('SELECT id,build,created FROM runs ORDER BY rowid DESC LIMIT 30')])
                if u.path == '/api/run':
                    q = parse_qs(u.query)
                    return self.reply(store.summary(q['id'][0], q.get('case', [None])[0]))
                self.reply({'error': '不存在'}, 404)
            except (ValueError, KeyError, OSError) as exc:
                self.reply({'error': str(exc)}, 400)

        def do_POST(self):
            if self.headers.get('Host') != f'127.0.0.1:{port}' or self.headers.get('Origin') != origin or self.headers.get('X-QA-Client') != '1':
                return self.reply({'error': '仅允许本机对照页请求'}, 403)
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 20000:
                    raise ValueError('请求大小无效')
                body = json.loads(self.rfile.read(length))
                if self.path == '/api/create':
                    return self.reply(store.create(body['build']))
                if self.path == '/api/record' and body.get('actor') in {'human', 'ai'}:
                    return self.reply(store.record(**body))
                self.reply({'error': '不支持的操作'}, 400)
            except (ValueError, KeyError, TypeError, sqlite3.Error) as exc:
                self.reply({'error': str(exc)}, 400)
    print(origin, flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init'); sub.add_parser('list')
    p = sub.add_parser('serve'); p.add_argument('--port', type=int, default=5182)
    p = sub.add_parser('create'); p.add_argument('--build', required=True)
    p = sub.add_parser('summary'); p.add_argument('run'); p.add_argument('--case')
    p = sub.add_parser('run'); p.add_argument('run'); p.add_argument('--ids', required=True)
    p = sub.add_parser('record'); p.add_argument('run')
    for flag in ['case', 'point', 'actor', 'name', 'status', 'note']:
        p.add_argument('--' + flag, required=True)
    args = parser.parse_args()
    store = Store(args.project)
    if args.command == 'init':
        store.root.mkdir(parents=True, exist_ok=True)
        created = []
        for name in ['index.html', 'cases.json']:
            target = store.root / name
            if not target.exists():
                with target.open('xb') as dest:
                    dest.write((ASSETS / name).read_bytes())
                created.append(name)
        result = {'created': created, 'project': str(store.root)}
    elif args.command == 'serve':
        return serve(store, args.port)
    elif args.command == 'list':
        result = [{'id': c['id'], 'title': c['title'], 'checkpoints': len(c['checkpoints'])} for c in store.cases()]
    elif args.command == 'create':
        result = store.create(args.build)
    elif args.command == 'summary':
        result = store.summary(args.run, args.case)
    elif args.command == 'record':
        result = store.record(args.run, args.case, args.point, args.actor, args.name, args.status, args.note)
    else:
        result = store.run(args.run, args.ids.split(','))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False))
        sys.exit(1)
