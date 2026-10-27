"""Actual FFmpeg synthetic renders and gate regressions. No original vlog or network inputs."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import render_edl
from edit_plan import build


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class RenderIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.media = cls.root / 'own-test.mkv'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=s=160x284:r=30:d=2',
                        '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=2',
                        '-c:v','libx264','-pix_fmt','yuv420p','-c:a','pcm_s16le',str(cls.media)],check=True)
        cls.template = {'sources':[{'id':'x','path':cls.media.name,'sha256':render_edl.sha(cls.media),
                                   'duration_seconds':2,'privacy':{'kind':'synthetic'}}],
                        'words':[{'id':'a','source':'x','start':.1,'end':.4,'text':'甲'},
                                 {'id':'b','source':'x','start':1.6,'end':1.9,'text':'乙'}],
                        'candidates':[{'id':'d','source':'x','start':1,'end':1.5,'reason':'synthetic gap','approved':True}],
                        'require_audio':True}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.project = copy.deepcopy(self.template)
        self.out = self.root / self._testMethodName

    def test_actual_edl_slices_concat_captions_and_audio(self):
        result = render_edl.render(self.project,self.root,self.out,160,284,30)
        self.assertAlmostEqual(result['duration_seconds'],1.5,delta=.05)
        self.assertEqual(result['segment_count'],2)
        self.assertEqual(result['cut_windows'],1)
        self.assertTrue(result['full_decode_pass'])
        self.assertTrue(result['caption_bounds_pass'])
        self.assertTrue(result['audio_present'])
        self.assertGreater(result['mean_volume_db'],-80)
        self.assertIn('00:00:01,100', (self.out/'captions.srt').read_text(encoding='utf-8'))

    def test_rollback_actually_renders_original_duration(self):
        self.project['candidates'][0]['approved']=False
        result=render_edl.render(self.project,self.root,self.out,160,284,30)
        self.assertAlmostEqual(result['duration_seconds'],2,delta=.05)
        self.assertEqual(result['segment_count'],1)
        self.assertEqual(result['cut_windows'],0)
        self.assertTrue(result['full_decode_pass'])

    def test_hash_change_rejected_before_output(self):
        self.project['sources'][0]['sha256']='1'*64
        with self.assertRaisesRegex(ValueError,'hash'):
            render_edl.render(self.project,self.root,self.out,160,284,30)
        self.assertFalse(self.out.exists())

    def test_real_source_needs_privacy_approval(self):
        self.project['sources'][0]['privacy']={}
        with self.assertRaisesRegex(ValueError,'privacy gate'):
            render_edl.render(self.project,self.root,self.out,160,284,30)
        self.assertFalse(self.out.exists())

    def test_off_frame_cut_rejected_before_output(self):
        self.project['candidates'][0]['start']=1.01
        with self.assertRaisesRegex(ValueError,'frame grid'):
            render_edl.render(self.project,self.root,self.out,160,284,30)
        self.assertFalse(self.out.exists())

    def test_subtitle_past_output_rejected(self):
        edl=build(self.project)
        edl['remapped_words'][0]['end']=9
        self.out.mkdir()
        with self.assertRaisesRegex(ValueError,'outside'):
            render_edl.captions(edl,720,1280,self.out)

    def test_ass_control_text_escaped(self):
        self.project['words'][0]['text']='{甲}'
        edl=build(self.project)
        self.out.mkdir()
        render_edl.captions(edl,720,1280,self.out)
        self.assertIn('｛甲｝',(self.out/'captions.ass').read_text(encoding='utf-8-sig'))

    def test_unsupported_geometry_rejected(self):
        with self.assertRaisesRegex(ValueError,'dimensions'):
            render_edl.render(self.project,self.root,self.out,161,284,30)


if __name__=='__main__':
    unittest.main()
