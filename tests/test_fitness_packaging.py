import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fitness_package_check', ROOT/'scripts/package_skill.py')
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)


class PackagingTest(unittest.TestCase):
    def test_binary_files_are_not_line_normalized(self):
        data = b'\x89PNG\r\n\x1a\nfont\r\nbytes\x00'
        for filename in ['image.png','font.ttf','font.woff','clip.mp4','audio.wav']:
            self.assertEqual(pack.archive_bytes(filename, data), data)

    def test_text_normalization_and_asset_registration(self):
        self.assertEqual(pack.archive_bytes('demo.py', b'first\r\nsecond\r\n'), b'first\nsecond\n')
        self.assertEqual(pack.ASSET_NAMES['lyzbcy-fitness-tracker'], 'lyzbcy-fitness-tracker.zip')


if __name__ == '__main__':
    unittest.main()
