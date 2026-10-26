import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1] / 'skills' / 'lyzbcy-shared-regression'


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


qa = module('shared_qa', ROOT / 'scripts/qa.py')
updater = module('shared_update', ROOT / 'scripts/update_skill.py')


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copy(ROOT / 'assets/cases.json', self.root / 'cases.json')
        self.store = qa.Store(self.root)
        self.run = self.store.create('synthetic-test')['id']

    def tearDown(self):
        self.temp.cleanup()

    def record(self, point='cancel', actor='ai', name='agent', status='passed'):
        return self.store.record(self.run, 'DEMO-001', point, actor, name, status, '合成观察')

    def test_partial_conflict_and_retry_preserve_history(self):
        self.record()
        self.assertEqual(self.store.summary(self.run)['cases'][0]['status'], 'partial')
        self.record(actor='human', name='reviewer', status='failed')
        self.assertEqual(self.store.summary(self.run)['cases'][0]['status'], 'conflict')
        self.record(actor='human', name='reviewer')
        self.record(point='visual')
        view = self.store.summary(self.run, 'DEMO-001')['cases'][0]
        self.assertEqual(view['status'], 'passed')
        self.assertEqual(len(view['checkpoints'][0]['history']), 3)
        self.assertEqual(view['checkpoints'][0]['history'][1]['status'], 'failed')

    def test_frozen_definition_and_invalid_automatic_record(self):
        cases = self.store.cases()
        cases[0]['title'] = 'changed'
        (self.root / 'cases.json').write_text(json.dumps(cases), encoding='utf-8')
        view = self.store.summary(self.run, 'DEMO-001')['cases'][0]
        self.assertEqual(view['status'], 'stale')
        self.assertNotEqual(view['title'], 'changed')
        with self.assertRaises(ValueError):
            self.record(actor='automation')

    def test_http_assertions_no_redirect_and_pending_human(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                self.send_response(302 if self.path == '/redirect' else 200)
                if self.path == '/redirect':
                    self.send_header('Location', '/ok')
                self.end_headers()
                self.wfile.write(b'ok')
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = 'http://127.0.0.1:' + str(server.server_port)
            cases = self.store.cases()
            cases[0]['checkpoints'].extend([
                {'id': 'http', 'title': 'GET', 'mode': 'auto', 'http': {'url': base+'/ok', 'contains': 'ok'}},
                {'id': 'redirect', 'title': 'redirect', 'mode': 'auto', 'http': {'url': base+'/redirect'}}
            ])
            (self.root / 'cases.json').write_text(json.dumps(cases), encoding='utf-8')
            run = self.store.create('http-test')['id']
            self.assertEqual(self.store.run(run, ['DEMO-001'])['checked'], 2)
            points = self.store.summary(run, 'DEMO-001')['cases'][0]['checkpoints']
            self.assertEqual([p['status'] for p in points], ['pending', 'pending', 'passed', 'failed'])
        finally:
            server.shutdown()
            server.server_close()

    def test_update_hash_failure_keeps_old_and_valid_update_preserves_data(self):
        installed = self.root / 'lyzbcy-shared-regression'
        shutil.copytree(ROOT, installed)
        (installed/'local-project.json').write_text('private', encoding='utf-8')
        original = (installed/'SKILL.md').read_bytes()
        new = original.replace(b'version: 0.1.0', b'version: 0.1.1')
        manifest = {'name': installed.name, 'version': '0.1.1', 'sha256': {'SKILL.md': qa.hashlib.sha256(new).hexdigest()}}
        files = {'update.json': json.dumps(manifest).encode(), 'SKILL.md': b'bad'}
        self.assertEqual(updater.check(installed, fetch=files.__getitem__, today='2099-01-01'), 'failed')
        self.assertEqual((installed/'SKILL.md').read_bytes(), original)
        files['SKILL.md'] = new
        self.assertEqual(updater.check(installed, fetch=files.__getitem__, today='2099-01-02'), 'updated')
        self.assertEqual((installed/'SKILL.md').read_bytes(), new)
        self.assertEqual((installed/'local-project.json').read_text(), 'private')
        self.assertEqual(updater.check(installed, fetch=lambda _: self.fail('daily throttle'), today='2099-01-02'), 'already_checked')


if __name__ == '__main__':
    unittest.main()
