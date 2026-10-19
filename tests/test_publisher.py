from pathlib import Path
import json,struct,sys,tempfile,unittest
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills'/'lyzbcy-video-publish-assistant'/'scripts'))
from browser import Browser,UIError,digest
from publish import Publisher
from prepare_upload import check

class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        (self.root/'video.mp4').write_bytes(b'test-media-fingerprint')
        (self.root/'cover.png').write_bytes(b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',1920,1080))
        self.manifest=self.root/'manifest.json';self.data={'video':'video.mp4','covers':{'16:9':'cover.png'},'mode':'prepare','platforms':{'youtube':{'title':'A music animation','description':'Actual description','topics':['Animation'],'made_for_kids':False,'ai_disclosure':True}}};self.save()
    def save(self):self.manifest.write_text(json.dumps(self.data),encoding='utf-8')
    def pub(self):
        with patch('publish.Browser'):p=Publisher(self.manifest,'youtube',self.root/'run','test-task','http://localhost:10086')
        p.b.state.return_value={'url':'https://studio.youtube.com','text':'','inputs':[]};return p

    @patch('prepare_upload.shutil.which',return_value=None)
    def test_youtube_preflight_and_locked_hash(self,_):
        self.data['video_sha256']=digest(self.root/'video.mp4');self.save();self.assertEqual(check(self.manifest)['local_preflight'],'passed')
        (self.root/'video.mp4').write_bytes(b'changed');self.assertRaisesRegex(ValueError,'SHA256',check,self.manifest)
    @patch('prepare_upload.shutil.which',return_value=None)
    def test_cannot_turn_manifest_into_publication(self,_):
        self.data['mode']='publish';self.save();self.assertRaisesRegex(ValueError,'drafts only',check,self.manifest)
    def test_resume_refuses_changed_video(self):
        p=self.pub();p.persist();(self.root/'video.mp4').write_bytes(b'new-version');self.assertRaisesRegex(UIError,'different session/video',self.pub)
    def test_copy_change_invalidates_verification(self):
        p=self.pub();p.j['steps']={'upload':{'status':'done'},'verify':{'status':'done'}};p.persist();self.data['platforms']['youtube']['title']='Revised title';self.save();q=self.pub();self.assertIn('upload',q.j['steps']);self.assertNotIn('verify',q.j['steps'])
    def test_uncertain_upload_is_not_repeated(self):
        p=self.pub();p.shown=Mock(return_value=False);p.body=Mock(return_value='');p.b.js.return_value=True;p.b.wait.side_effect=UIError('timeout');p.evidence=Mock()
        self.assertRaisesRegex(UIError,'do not re-upload',p.run,'upload');self.assertTrue(json.loads(p.file.read_text())['upload_attempted'])
        self.assertRaisesRegex(UIError,'already attempted',p.run,'upload');self.assertEqual(p.b.upload.call_count,1)
    def test_an_unrelated_draft_is_not_overwritten(self):
        p=self.pub();p.shown=Mock(return_value=True);p.b.js.return_value='Someone else draft';self.assertRaisesRegex(UIError,'another title',p.upload);p.b.upload.assert_not_called()
    def test_publication_ui_target_never_clicked(self):
        b=Browser('fixture');b.focus=Mock();b.target=Mock(return_value={'text':'发布','disabled':False});b.point=Mock();self.assertRaisesRegex(UIError,'outside',b.tap,text='发布');b.point.assert_not_called()
    def test_ambiguous_target_has_no_click_side_effect(self):
        b=Browser('fixture');b.focus=Mock();b.target=Mock(side_effect=UIError('ambiguous'));b.point=Mock();self.assertRaises(UIError,b.tap,text='完成');b.point.assert_not_called()
    def test_cover_visual_review_is_a_checkpoint(self):
        p=self.pub();p.j['cover_visual_review']='pending';self.assertRaisesRegex(UIError,'visual review',p.save);p.b.tap.assert_not_called()
    def test_verify_requires_reopened_draft(self):
        p=self.pub();self.assertRaisesRegex(UIError,'Reopen',p.verify)
    def test_changed_saved_title_cannot_pass(self):
        p=self.pub();p.j['steps']['reopen']={'status':'done'};p.evidence=Mock(return_value={'inputs':[{'value':'wrong title'}]});self.assertRaisesRegex(UIError,'title differs',p.verify)
    def test_manual_bili_submission_stops_any_new_upload(self):
        p=self.pub();p.b.state.return_value={'url':'https://member.bilibili.com/platform/upload/video/frame','text':'稿件投递成功','inputs':[]};p.evidence=Mock();self.assertRaisesRegex(UIError,'manual publication',p.run,'upload');p.b.upload.assert_not_called();p.b.focus.assert_any_call(False)
    def test_youtube_save_uses_only_close_not_publish(self):
        p=self.pub();p.j['cover_visual_review']='passed';p.evidence=Mock(return_value={})
        p.b.wait=Mock(side_effect=[{'saved_private':True,'saving':False,'title':self.data['platforms']['youtube']['title'],'url':'https://studio.youtube.com','text':''}, True])
        r=p.save();self.assertEqual(r['status'],'private_autosaved')
        p.b.semantic.assert_called_once_with('button','关闭');p.b.tap.assert_not_called()

if __name__=='__main__':unittest.main()
