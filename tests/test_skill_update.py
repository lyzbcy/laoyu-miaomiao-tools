import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/software-video-production/scripts/update_skill.py'
spec = importlib.util.spec_from_file_location('skill_update', SCRIPT)
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'software-video-production'
        self.root.mkdir()
        self.old = b'---\nmetadata:\n  version: 0.1.0\n---\nold'
        (self.root/'SKILL.md').write_bytes(self.old)
        (self.root/'notes.txt').write_text('user notes')
        self.files = {'SKILL.md': self.old.replace(b'0.1.0', b'0.2.0'), 'docs/rule.md': b'new rule'}
        self.hashes = {k: hashlib.sha256(v).hexdigest() for k, v in self.files.items()}

    def fetch(self, rel):
        if rel == 'update.json':
            return json.dumps({'name':self.root.name,'version':'0.2.0','sha256':self.hashes}).encode()
        return self.files[rel]

    def run_check(self, fetch=None, day='2026-10-19'):
        return update.check(self.root, fetch or self.fetch, day)

    def test_success_preserves_unmanaged_files_and_checks_once_daily(self):
        self.assertEqual(self.run_check(), 'updated')
        self.assertEqual((self.root/'docs/rule.md').read_bytes(), b'new rule')
        self.assertEqual((self.root/'notes.txt').read_text(), 'user notes')
        self.assertEqual(self.run_check(lambda _: self.fail('second daily network call')), 'already_checked')

    def test_offline_failure_keeps_old_version_and_retries_next_day(self):
        def offline(_): raise TimeoutError()
        self.assertEqual(self.run_check(offline), 'failed')
        self.assertEqual((self.root/'SKILL.md').read_bytes(), self.old)
        self.assertEqual(self.run_check(), 'already_checked')
        self.assertEqual(self.run_check(day='2026-10-20'), 'updated')

    def test_missing_file_and_hash_mismatch_never_partially_install(self):
        self.files['docs/rule.md'] = b'corrupt download'
        self.assertEqual(self.run_check(), 'failed')
        self.assertEqual((self.root/'SKILL.md').read_bytes(), self.old)
        self.assertFalse((self.root/'docs/rule.md').exists())

    def test_replacement_failure_rolls_back(self):
        real_replace = update.os.replace
        def replace(src, dst):
            if '.update-stage-' in str(src) and Path(dst).name == 'SKILL.md':
                raise PermissionError('simulated locked entry')
            return real_replace(src, dst)
        with patch.object(update.os, 'replace', side_effect=replace):
            self.assertEqual(self.run_check(), 'failed')
        self.assertEqual((self.root/'SKILL.md').read_bytes(), self.old)
        self.assertFalse((self.root/'docs/rule.md').exists())
        self.assertFalse((self.root/'.update-journal.json').exists())

    def test_crash_journal_is_restored_before_check(self):
        backup=self.root/'.update-backup';backup.mkdir()
        (backup/'SKILL.md').write_bytes(self.old)
        (self.root/'SKILL.md').write_bytes(b'incomplete')
        update.write_json(self.root/'.update-journal.json', {'SKILL.md':True})
        self.assertEqual(self.run_check(), 'updated')
        self.assertFalse(backup.exists())

    def test_path_escape_is_rejected(self):
        self.hashes['../outside.txt']=hashlib.sha256(b'x').hexdigest()
        self.assertEqual(self.run_check(), 'failed')
        self.assertFalse((self.root.parent/'outside.txt').exists())
        self.assertEqual((self.root/'SKILL.md').read_bytes(),self.old)

    def test_newer_local_version_is_not_downgraded(self):
        (self.root/'SKILL.md').write_bytes(self.old.replace(b'0.1.0',b'0.3.0'))
        self.assertEqual(self.run_check(), 'current')

    def test_concurrent_check_does_not_start_second_updater(self):
        (self.root/'.update-check.lock').touch()
        self.assertEqual(self.run_check(lambda _:self.fail('busy must not fetch')), 'busy')


if __name__ == '__main__':
    unittest.main()
