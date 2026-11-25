"""Entry without a frontmatter file list: packaging falls back to the update manifest (software-video-production)."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'software-video-production'


class VideoPackagingTest(unittest.TestCase):
    def test_entry_without_files_list_uses_update_manifest(self):
        front = (SKILL / 'SKILL.md').read_text(encoding='utf-8').split('---', 2)[1]
        self.assertNotIn('files:', front)
        manifest = json.loads((SKILL / 'update.json').read_text(encoding='utf-8'))
        self.assertIn('SKILL.md', manifest['sha256'])
        result = subprocess.run(
            [sys.executable, '-X', 'utf8', str(ROOT / 'scripts' / 'package_skill.py'), 'software-video-production', '--check'],
            capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('update.json', result.stdout)
        self.assertIn(f"manifest {len(manifest['sha256']) + 1} 个文件", result.stdout)  # the manifest itself ships too

    def test_every_update_manifest_file_exists_on_disk(self):
        manifest = json.loads((SKILL / 'update.json').read_text(encoding='utf-8'))
        self.assertEqual([rel for rel in manifest['sha256'] if not (SKILL / rel).is_file()], [])


if __name__ == '__main__':
    unittest.main()
