import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import dashboard_data
import daily_poster as poster
import fitness
import publish_dashboard as publisher
import runtime
import update_skill

ROOT = Path(__file__).resolve().parents[1]


class EnvironmentTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)/'private'
        fitness.init(self.folder)
        (self.folder/'records.jsonl').write_bytes((ROOT/'examples/demo-records.jsonl').read_bytes())

    def tearDown(self):
        self.tmp.cleanup()

    def overlay(self, **kwargs):
        poster.write_json(self.folder/'runtime.local.json', kwargs)

    def test_local_overlay_merges_without_changing_config(self):
        original = (self.folder/'config.json').read_bytes()
        self.overlay(brand={'watermark': '本地'}, blog={'schema': 'jekyll-v1'})
        cfg = runtime.config(self.folder)
        self.assertEqual(cfg['brand']['watermark'], '本地')
        self.assertIn('keyword', cfg['brand'])
        self.assertFalse(cfg['blog']['enabled'])
        self.assertEqual((self.folder/'config.json').read_bytes(), original)

    def test_location_priority_and_environment_discovery(self):
        root = Path(self.tmp.name)/'skill';root.mkdir()
        poster.write_json(root/'runtime.local.json', {'workspace': str(self.folder)})
        with patch.object(runtime, 'ROOT', root), patch.dict(os.environ, {}, clear=True):
            self.assertEqual(runtime.workspace(), self.folder)
            with patch.dict(os.environ, {'FITNESS_HOME': str(root)}):
                self.assertEqual(runtime.workspace(), root)
                self.assertEqual(runtime.workspace(str(self.folder)), self.folder)
        (self.folder/'LOCAL.md').write_text('local preferences')
        e = runtime.environment(self.folder)
        self.assertEqual(e['local_guidance'], str(self.folder/'LOCAL.md'))
        self.assertNotIn('config', e)

    def test_local_files_cannot_be_managed_by_updater(self):
        for rel in ['runtime.local.json', 'LOCAL.md', 'nested/runtime.local.json']:
            with self.assertRaises(ValueError):
                update_skill.safe_path(self.folder, rel)

    def test_recorder_uses_locator_without_exported_environment(self):
        # Run the real CLI with an isolated install locator, not the machine's private one.
        import shutil
        install = Path(self.tmp.name)/'install'
        (install/'scripts').mkdir(parents=True)
        for name in ['add_record.py', 'runtime.py']:
            shutil.copy2(ROOT/'scripts'/name, install/'scripts'/name)
        poster.write_json(install/'runtime.local.json', {'workspace': str(self.folder)})
        env = dict(os.environ);env.pop('FITNESS_HOME', None)
        result = subprocess.run([sys.executable, str(install/'scripts/add_record.py'), 'set',
            '--exercise', '引体向上', '--weight', '0', '--reps', '4.5', '--session', 'pull'],
            env=env, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        row = json.loads((self.folder/'records.jsonl').read_text(encoding='utf-8').splitlines()[-1])
        self.assertEqual(row['endTime'], row['ts'])
        self.assertEqual(row['reps'], 4.5)

    def test_jekyll_schema_preserves_totals_and_all_sections(self):
        self.overlay(blog={'schema': 'jekyll-v1'})
        result = publisher.export_data(self.folder)
        rows, _ = poster.read_records(self.folder/'records.jsonl')
        expected = sum(r['weight']*r['reps'] for r in rows if r['action']=='set')
        self.assertEqual(result['overview']['total_volume'], expected)
        self.assertEqual(result['overview']['total_sets'], 6)
        self.assertEqual(len(result['sessions']), 1)
        self.assertEqual(result['sessions'][0]['duration_min'], 50)
        for key in ['personal_records', 'muscle_balance', 'volume_trend', 'exercises', 'cardio', 'nutrition_link']:
            self.assertIn(key, result)
        self.assertEqual(result, publisher.export_data(self.folder))

    def test_legacy_notes_and_preferences_require_explicit_enable(self):
        cfg = runtime.config(self.folder)
        cfg.update(preferences={'private_marker':'PRIVATE'}, personalRecords={'back':{'划船':{'weight':10,'reps':5,'note':'SECRET'}}})
        cfg['blog'] = {'schema': 'jekyll-v1'}
        result = dashboard_data.export_jekyll(self.folder, cfg)
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertNotIn('PRIVATE', json.dumps(result))
        cfg['blog'].update(include_notes=True, include_preferences=True)
        result = dashboard_data.export_jekyll(self.folder, cfg)
        self.assertEqual(result['personal_records'][0]['note'], 'SECRET')
        self.assertEqual(result['overview']['preferences']['private_marker'], 'PRIVATE')

    def test_cardio_only_and_empty_legacy_data(self):
        row = {'date':'2026-01-05','ts':'2026-01-05T12:00:00+08:00','action':'cardio','exercise':'跑步','durationMin':25,'activeKcal':200}
        (self.folder/'records.jsonl').write_text(json.dumps(row)+'\n')
        result = dashboard_data.export_jekyll(self.folder)
        self.assertEqual(result['overview']['total_sessions'], 0)
        self.assertEqual(result['cardio']['total_minutes'], 25)
        (self.folder/'records.jsonl').write_text('')
        self.assertEqual(dashboard_data.export_jekyll(self.folder)['overview']['total_sets'], 0)

    def test_image_failure_does_not_hide_blog_or_stale_image(self):
        with patch.object(fitness.subprocess, 'run', return_value=subprocess.CompletedProcess([],1,'','image failure')), \
             patch.object(publisher, 'publish', return_value={'status':'pushed'}) as pub:
            result = fitness.finish(self.folder, '2026-01-05')
        pub.assert_called_once()
        self.assertIsNone(result['image'])
        self.assertIn('image failure', result['image_error'])
        self.assertEqual(result['blog']['status'], 'pushed')

    def test_no_publish_mode_never_calls_git(self):
        with patch.object(publisher, 'publish', side_effect=AssertionError('published')):
            result = fitness.finish(self.folder, '2026-01-05', no_publish=True)
        self.assertEqual(result['blog']['status'], 'skipped')
        self.assertTrue(result['image_check']['ok'])

    def test_image_process_failure_without_stderr_never_returns_stale_png(self):
        with patch.object(fitness.subprocess, 'run', return_value=subprocess.CompletedProcess([],1,'','')):
            result = fitness.finish(self.folder, '2026-01-05', no_publish=True)
        self.assertIsNone(result['image'])
        self.assertIn('退出码1', result['image_error'])

    def test_process_scoped_ssh_options_never_leak(self):
        self.overlay(blog={'github_ssh': True})
        with patch.object(publisher, '_publish') as inner:
            inner.side_effect = lambda *a, **kw: tuple(publisher.GIT_OPTIONS.get())
            self.assertIn('url.ssh://git@github.com/.insteadOf=git@github.com:', publisher.publish(self.folder))
        self.assertFalse(publisher.GIT_OPTIONS.get())


if __name__ == '__main__':
    unittest.main()
