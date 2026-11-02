import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import daily_poster as poster
import fitness
import publish_dashboard as publisher

ROOT = Path(__file__).resolve().parents[1]


class RuntimeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fitness public ')
        self.folder = Path(self.temp.name)/'用户数据'
        fitness.init(self.folder)
        shutil.copy2(ROOT/'examples/demo-records.jsonl', self.folder/'records.jsonl')

    def tearDown(self):
        self.temp.cleanup()

    def config(self, **changes):
        p = self.folder/'config.json'
        value = json.loads(p.read_text(encoding='utf-8'))
        value.update(changes)
        poster.write_json(p, value)

    def test_init_preserves_user_data_and_defaults_to_no_git(self):
        self.config(brand={'title': '自定义训练报'})
        before = (self.folder/'records.jsonl').read_bytes()
        fitness.init(self.folder)
        self.assertEqual((self.folder/'records.jsonl').read_bytes(), before)
        self.assertEqual(json.loads((self.folder/'config.json').read_text(encoding='utf-8'))['brand']['title'], '自定义训练报')
        with patch.object(publisher, 'git', side_effect=AssertionError('disabled blog called git')):
            self.assertEqual(publisher.publish(self.folder)['status'], 'disabled')

    def test_finish_keeps_image_when_blog_fails_without_appending_records(self):
        self.config(blog={'enabled': True, 'repo': str(self.folder/'missing')})
        before = (self.folder/'records.jsonl').read_bytes()
        result = fitness.finish(self.folder, '2026-01-05')
        self.assertEqual(result['blog']['status'], 'failed')
        self.assertTrue(Path(result['image']).is_file())
        self.assertTrue(result['image_check']['ok'])
        self.assertEqual((self.folder/'records.jsonl').read_bytes(), before)

    def test_custom_brand_and_finish_preserve_model_copy(self):
        self.config(brand={'title': '小王的训练小报', 'watermark': '小王', 'account': '小王记录', 'keyword': '训练'})
        data = poster.make_input(self.folder/'records.jsonl', '2026-01-05', json.loads((self.folder/'config.json').read_text(encoding='utf-8'))['brand'])
        data['copy']['cheer'] = '认真练，也认真恢复'
        poster.write_json(self.folder/'posters/2026-01-05.json', data)
        result = fitness.finish(self.folder, '2026-01-05')
        audit = json.loads(Path(result['image']).with_suffix('.audit.json').read_text(encoding='utf-8'))
        self.assertEqual(audit['watermark']['text'], '小王')
        self.assertIn('回复“训练”', audit['cta'])
        self.assertEqual(audit['copy']['cheer'], '认真练，也认真恢复')

    def test_unfinished_date_never_adds_fake_end(self):
        path = self.folder/'records.jsonl'
        path.write_text('\n'.join(path.read_text(encoding='utf-8').splitlines()[:-1])+'\n', encoding='utf-8')
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, '尚无有效收工'):
            fitness.finish(self.folder, '2026-01-05')
        self.assertEqual(path.read_bytes(), before)

    def test_recorder_uses_explicit_folder_and_accepts_half_reps(self):
        cmd = [sys.executable, str(ROOT/'scripts/add_record.py'), '--data-dir', str(self.folder),
               'set', '--exercise', '引体向上', '--weight', '0', '--reps', '4.5', '--session', 'pull']
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        rows, _ = poster.read_records(self.folder/'records.jsonl')
        self.assertEqual(rows[-1]['reps'], 4.5)
        self.assertEqual(rows[-1]['muscleGroup'], 'lats')
        result = subprocess.run(cmd[:cmd.index('--reps')+1]+['-2','--session','pull'], capture_output=True)
        self.assertNotEqual(result.returncode, 0)


@unittest.skipUnless(shutil.which('git'), 'git unavailable')
class PublisherTest(unittest.TestCase):
    config = RuntimeTest.config
    tearDown = RuntimeTest.tearDown

    def setUp(self):
        RuntimeTest.setUp(self)
        self.repo = Path(self.temp.name)/'blog'
        self.bare = Path(self.temp.name)/'remote.git'
        self.repo.mkdir()
        self.run_git('init', '-b', 'main')
        self.run_git('config', 'user.email', 'demo@example.invalid')
        self.run_git('config', 'user.name', 'Fixture')
        (self.repo/'README.md').write_text('fixture\n')
        self.run_git('add', 'README.md')
        self.run_git('commit', '-m', 'fixture')
        subprocess.run(['git', 'init', '--bare', str(self.bare)], check=True, capture_output=True)
        self.run_git('remote', 'add', 'origin', str(self.bare))
        self.run_git('push', '-u', 'origin', 'main')
        self.config(blog={'enabled': True, 'repo': str(self.repo), 'branch': 'main', 'remote': 'origin', 'data_path': 'fitness/fitness.json'})

    def run_git(self, *args):
        return subprocess.run(['git','-C',str(self.repo),*args],check=True,capture_output=True,text=True).stdout.strip()

    # Parent runtime checks run once in RuntimeTest; these cases focus on actual fixture Git repos.
    def test_push_exact_data_path_preserves_other_unstaged_work(self):
        (self.repo/'README.md').write_text('unrelated work\n')
        remote_before = self.run_git('remote', 'get-url', 'origin')
        result = publisher.publish(self.folder)
        self.assertEqual(result['status'], 'pushed')
        self.assertEqual(self.run_git('show', '--format=', '--name-only', 'HEAD'), 'fitness/fitness.json')
        self.assertEqual((self.repo/'README.md').read_text(), 'unrelated work\n')
        self.assertEqual(self.run_git('remote', 'get-url', 'origin'), remote_before)
        self.assertEqual(publisher.publish(self.folder)['status'], 'unchanged')

    def test_existing_staged_work_is_not_committed(self):
        (self.repo/'other.txt').write_text('keep staged')
        self.run_git('add', 'other.txt')
        head = self.run_git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(ValueError, '已有暂存'):
            publisher.publish(self.folder)
        self.assertEqual(head, self.run_git('rev-parse', 'HEAD'))
        self.assertEqual(self.run_git('diff', '--cached', '--name-only'), 'other.txt')

    def test_unpushed_other_commit_is_not_published(self):
        (self.repo/'other.txt').write_text('unpublished user work')
        self.run_git('add', 'other.txt'); self.run_git('commit', '-m', 'user work')
        with self.assertRaisesRegex(ValueError, '未对齐'):
            publisher.publish(self.folder)

    def test_failed_push_retries_same_commit_only(self):
        real = publisher.git
        def fail_push(repo, *args, **kw):
            if args[0] == 'push':
                raise ValueError('fixture push failed')
            return real(repo, *args, **kw)
        with patch.object(publisher, 'git', side_effect=fail_push):
            with self.assertRaisesRegex(ValueError, 'fixture push failed'):
                publisher.publish(self.folder)
        pending = self.run_git('rev-parse', 'HEAD')
        result = publisher.publish(self.folder)
        self.assertTrue(result['retry'])
        self.assertEqual(result['commit'], pending)
        self.assertEqual(self.run_git('rev-parse', 'HEAD'), pending)

    def test_output_paths_cannot_escape_repo(self):
        for value in ['../leak.json', '/absolute.json', '.git/config', '..\\escape.json']:
            with self.assertRaises(ValueError):
                publisher.output_path(self.repo, value)

    def test_jekyll_dry_run_and_publish_use_overlay_without_mutating_originals(self):
        source = (self.folder/'config.json').read_bytes()
        records = (self.folder/'records.jsonl').read_bytes()
        poster.write_json(self.folder/'runtime.local.json', {'blog': {'schema':'jekyll-v1', 'data_path':'_data/fitness.json'}})
        head = self.run_git('rev-parse', 'HEAD')
        result = publisher.publish(self.folder, dry_run=True)
        self.assertEqual(result['status'], 'ready')
        self.assertFalse((self.repo/'_data/fitness.json').exists())
        self.assertEqual(head, self.run_git('rev-parse', 'HEAD'))
        self.assertFalse((self.folder/'publish-state.json').exists())
        self.assertEqual(publisher.publish(self.folder)['status'], 'pushed')
        self.assertEqual(self.run_git('show', '--format=', '--name-only', 'HEAD'), '_data/fitness.json')
        self.assertIn('cardio', json.loads((self.repo/'_data/fitness.json').read_text(encoding='utf-8')))
        self.assertEqual(publisher.publish(self.folder)['status'], 'unchanged')
        self.assertEqual((self.folder/'config.json').read_bytes(), source)
        self.assertEqual((self.folder/'records.jsonl').read_bytes(), records)

    def test_failed_push_dry_run_never_retries_mutation(self):
        real = publisher.git
        def fail(repo, *args, **kw):
            if args[0] == 'push':
                raise ValueError('offline')
            return real(repo, *args, **kw)
        with patch.object(publisher, 'git', side_effect=fail):
            with self.assertRaises(ValueError):
                publisher.publish(self.folder)
        head = self.run_git('rev-parse', 'HEAD')
        with patch.object(publisher, 'git', side_effect=fail):
            self.assertEqual(publisher.publish(self.folder, dry_run=True)['status'], 'ready_to_retry')
        self.assertEqual(head, self.run_git('rev-parse', 'HEAD'))


if __name__ == '__main__':
    unittest.main()
