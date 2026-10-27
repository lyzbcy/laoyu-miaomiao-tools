import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from verify_upstream import verify

class UpstreamGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.file=self.root/'code.py';self.file.write_text('safe fixture')
        self.pins={'example':{'commit':'fixed','installed_files':{'code.py':hashlib.sha256(self.file.read_bytes()).hexdigest()}}}

    def test_pinned_bytes_accepted(self):
        self.assertEqual(verify('example',self.root,self.pins)['verified_files'],1)

    def test_tampered_source_rejected(self):
        self.file.write_text('changed')
        with self.assertRaisesRegex(ValueError,'changed'):verify('example',self.root,self.pins)

    def test_missing_source_not_executed(self):
        self.pins['example']['installed_files']={'missing.py':'0'*64}
        with self.assertRaises(FileNotFoundError):verify('example',self.root,self.pins)

    def test_source_escape_rejected(self):
        self.pins['example']['installed_files']={'../escape.py':'0'*64}
        with self.assertRaisesRegex(ValueError,'escapes'):verify('example',self.root,self.pins)

if __name__=='__main__':unittest.main()
