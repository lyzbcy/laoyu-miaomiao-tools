"""Portable voice selection, validated cache, and online failure boundaries."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('narrate', ROOT/'skills/software-video-production/scripts/narrate.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class Narration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)/'voice.mp3'

    def mock_audio(self):
        return patch.object(M, 'urlopen', side_effect=[io.BytesIO(json.dumps({'code':200,'url':'https://audio.example/voice.mp3'}).encode()), io.BytesIO(b'ID3sample')])

    def test_cache_reuses_same_text_voice_and_speed_without_network(self):
        with self.mock_audio() as call:
            self.assertFalse(M.synthesize('测试', self.output)['cached'])
            self.assertIn('/mbAIsc?', call.call_args_list[0].args[0])
        with patch.object(M, 'urlopen', side_effect=AssertionError('No network for cache')):
            self.assertTrue(M.synthesize('测试', self.output)['cached'])

    def test_changed_text_speed_or_audio_cannot_silently_reuse_or_overwrite(self):
        with self.mock_audio(): M.synthesize('测试', self.output)
        for text, speed in [('其他',0), ('测试',1)]:
            with self.assertRaises(ValueError): M.synthesize(text,self.output,speed)
        self.output.write_bytes(b'changed')
        with self.assertRaises(ValueError): M.synthesize('测试',self.output)

    def test_service_error_leaves_no_output(self):
        with patch.object(M,'urlopen',return_value=io.BytesIO(b'{"code":503}')):
            with self.assertRaises(ValueError): M.synthesize('测试',self.output)
        self.assertFalse(self.output.exists())

    def test_non_audio_download_leaves_no_output(self):
        with patch.object(M,'urlopen',side_effect=[io.BytesIO(b'{"code":200,"url":"https://audio.example/file"}'),io.BytesIO(b'<html>error</html>')]):
            with self.assertRaises(ValueError): M.synthesize('测试',self.output)
        self.assertFalse(self.output.exists())

    def test_skill_routes_to_shipped_default_without_local_model(self):
        s=(ROOT/'skills/software-video-production/SKILL.md').read_text(encoding='utf8')
        audio=(ROOT/'skills/software-video-production/docs/audio.md').read_text(encoding='utf8')
        self.assertIn('scripts/narrate.py',s)
        self.assertIn('哈基米',s)
        self.assertIn(M.ENDPOINT,audio)
        self.assertNotIn('缺少时用Edge TTS',audio)
