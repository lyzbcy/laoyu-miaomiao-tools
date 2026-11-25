import sys, json, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from extension_steps import mutation, read_state, source, UIError
from matrix_resume import pending
from publish import Publisher
import struct


class RecoveryTests(unittest.TestCase):
    def test_matching_prepared_cover_passes_without_visual_review(self):
        with tempfile.TemporaryDirectory() as td:
            cover=Path(td)/'cover.png';cover.write_bytes(b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',1200,900))
            p=Publisher.__new__(Publisher);p.item={};p.j={};p.p='youtube'
            result=p.finish_cover_upload({'ratio':'4:3','path':str(cover)})
            self.assertEqual(result['visual_review'],'passed')
            self.assertFalse(p.j['cover_review_evidence']['screenshot_required'])
            self.assertFalse(p.j['cover_review_evidence']['visually_reviewed'])

    def test_ratio_mismatch_and_explicit_crop_review_do_not_auto_pass(self):
        with tempfile.TemporaryDirectory() as td:
            cover=Path(td)/'cover.png';cover.write_bytes(b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',900,1200))
            p=Publisher.__new__(Publisher);p.item={};p.j={};p.p='youtube'
            with self.assertRaises(UIError):p.finish_cover_upload({'ratio':'4:3','path':str(cover)})
            p.item={'cover_visual_required':True}
            self.assertEqual(p.finish_cover_upload()['visual_review'],'pending')

    def test_failed_external_call_keeps_attempt_and_blocks_repeat(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'journal.json';plan={'video_sha256':'fixed'}
            def fail(): raise RuntimeError('connection lost after request')
            with self.assertRaises(RuntimeError):mutation(path,plan,'submission',fail)
            self.assertTrue(json.loads(path.read_text())['submission_attempted'])
            with self.assertRaises(UIError):mutation(path,plan,'submission',lambda:self.fail('must not repeat'))

    def test_changed_plan_cannot_inherit_submission(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'journal.json';mutation(path,{'text':'old'},'upload',lambda:True)
            with self.assertRaises(UIError):read_state(path,{'text':'new'})

    def test_wrong_video_fingerprint_stops_before_upload(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'video.mp4';p.write_bytes(b'changed')
            with self.assertRaises(UIError):source({'video':str(p),'video_sha256':'wrong'})

    def test_published_with_metadata_review_needs_query_not_reupload(self):
        rows=pending({'episodes':[{'episode':1,'platforms':{'x':{'status':'published','native_id':'1'},'xiaohongshu':{'status':'published','native_id':'2','collection_status':'association_update_submitted_under_review'},'wechat_official':{'status':'published_user_confirmed','native_id':'3'}}}]})
        self.assertEqual([r['platform'] for r in rows],['xiaohongshu','wechat_official'])
        self.assertEqual(rows[0]['next'],'metadata_query_only_never_reupload')
        self.assertEqual(rows[1]['next'],'readback_only_never_resubmit')


if __name__=='__main__':unittest.main()
