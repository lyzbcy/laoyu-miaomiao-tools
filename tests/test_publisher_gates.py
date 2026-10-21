from pathlib import Path
import ast,json,sys,unittest,tempfile,subprocess,shutil
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/lyzbcy-video-publish-assistant/scripts'))
from gates import activity_plan,authorize,light,normalized,publication_signal,review_fingerprint
from browser import Browser,UIError
from bilibili import BilibiliTopics
import test_publisher as fixtures

class GatesTests(unittest.TestCase):
    def test_three_lights(self):
        self.assertEqual([light('x',True)['light'],light('x',pending=True)['light'],light('x')['light']],['green','yellow','red'])
    def test_old_success_is_not_new_publication(self):
        self.assertEqual(publication_signal('douyin',{'url':'/content/manage','text':'发布成功'},'new')['light'],'yellow')
    def test_after_owned_douyin_click_is_submitted_not_audit_pass(self):
        r=publication_signal('douyin',{'url':'/content/manage','text':'发布成功'},'new',True)
        self.assertEqual(r['proof']['status'],'submitted')
    def test_youtube_hidden_other_video_success_is_not_enough(self):
        r=publication_signal('youtube',{'text':'older 发布于 today','published_dialog_text':'other title 发布于 today oldid'},'new',True,'newid')
        self.assertEqual(r['light'],'yellow')
    def test_youtube_success_requires_bound_id(self):
        state={'published_dialog_text':'new 发布于 today newid'}
        self.assertEqual(publication_signal('youtube',state,'new',True,'newid')['light'],'green')
        self.assertEqual(publication_signal('youtube',state,'new',True,'otherid')['light'],'yellow')
    def test_same_title_old_public_row_does_not_confirm_new_video(self):
        state={'matching_row_text':'new 公开','matching_row_video_id':'old-id'}
        self.assertEqual(publication_signal('youtube',state,'new',True,'new-id')['light'],'yellow')
    def test_rejection_is_red(self):
        self.assertEqual(publication_signal('xiaohongshu',{'text':'发布失败'},'new',True)['light'],'red')
    def test_bili_multiple_explicit_activities_rejected(self):
        with self.assertRaisesRegex(ValueError,'at most one'):activity_plan([],['a','b'])
    def test_bili_blocked_tags_use_one_activity_and_report_others(self):
        self.assertEqual(activity_plan(['a','b','normal'],blocked=['a','b']),{'ordinary':['normal'],'activity':'a','omitted':['b']})
    def test_explicit_activity_is_not_an_ordinary_tag(self):
        self.assertEqual(activity_plan(['a','normal'],['a'])['ordinary'],['normal'])
    def test_serialized_douyin_paragraphs_normalize_only_prefixes(self):
        self.assertEqual(normalized('a\n*b','douyin'),'a b')
        self.assertEqual(normalized('a*b','douyin'),'a*b')
        self.assertEqual(normalized('a\n*b','bilibili'),'a *b')
    def test_fingerprint_changes_for_copy_video_and_cover(self):
        m={'video_sha256':'a','platforms':{'x':{'title':'one'}}};base=review_fingerprint(m,'x',{'16:9':'cover-a'})
        for other,covers in [(dict(m,video_sha256='b'),{'16:9':'cover-a'}),(dict(m,platforms={'x':{'title':'two'}}),{'16:9':'cover-a'}),(m,{'16:9':'cover-b'})]:
            self.assertNotEqual(base,review_fingerprint(other,'x',covers))
    def test_authorization_cannot_expand_to_other_platform(self):
        r={'approved':True,'platforms':{'douyin':{'review_fingerprint':'abc','visibility':'public'}}}
        self.assertEqual(authorize(r,'douyin','abc')['light'],'green')
        with self.assertRaises(ValueError):authorize(r,'youtube','abc')
    def test_channels_generic_multiplatform_approval_is_not_enough(self):
        r={'approved':True,'platforms':{'wechat_channels':{'review_fingerprint':'abc','visibility':'public'}}}
        with self.assertRaisesRegex(ValueError,'separate confirmation'):authorize(r,'wechat_channels','abc')
        r['platforms']['wechat_channels']['confirmed_this_video']=True
        self.assertEqual(authorize(r,'wechat_channels','abc')['light'],'green')
        with self.assertRaises(ValueError):authorize(r,'wechat_channels','different-video')
    def test_wechat_mass_send_is_not_implied_by_publish(self):
        r={'approved':True,'platforms':{'wechat_official':{'review_fingerprint':'a','visibility':'public','mass_send':True}}}
        with self.assertRaisesRegex(ValueError,'mass send'):authorize(r,'wechat_official','a')
    @unittest.skipUnless(shutil.which('node'),'Node is needed only for embedded JavaScript syntax validation')
    def test_embedded_browser_expressions_parse(self):
        expressions=[]
        root=Path(__file__).resolve().parents[1]/'skills/lyzbcy-video-publish-assistant/scripts'
        for p in root.glob('*.py'):
            for n in ast.walk(ast.parse(p.read_text('utf-8'))):
                if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value.startswith('(()=>{') and n.value.endswith('})()'):
                    expressions.append({'source':f'{p.name}:{n.lineno}','code':n.value})
        script="let s='';process.stdin.on('data',c=>s+=c);process.stdin.on('end',()=>{for(const x of JSON.parse(s)){try{new Function(x.code)}catch(e){console.error(x.source,e.message);process.exitCode=1}}});"
        result=subprocess.run(['node','-e',script],input=json.dumps(expressions),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

class ExecutionTests(unittest.TestCase):
    setUp=fixtures.PublisherTests.setUp
    save=fixtures.PublisherTests.save
    pub=fixtures.PublisherTests.pub
    def test_green_text_does_not_take_screenshot_or_full_screen_read(self):
        p=self.pub();p.evidence('text')
        p.b.state.assert_not_called();p.b.screenshot.assert_not_called();p.b.signals.assert_called_once()
    def test_verification_reads_fields_but_does_not_screenshot(self):
        p=self.pub();p.evidence('verified');p.b.state.assert_called_once();p.b.screenshot.assert_not_called()
    def test_error_takes_one_diagnostic_screenshot(self):
        p=self.pub();p.evidence('error-covers');p.b.screenshot.assert_called_once()
    def test_input_edit_does_not_use_unreliable_coordinates(self):
        b=Browser('fixture');b.js=Mock(return_value='new');b.tap=Mock();b.key=Mock();b.insert=Mock()
        self.assertEqual(b.edit('input','new'),'new');b.tap.assert_not_called();b.key.assert_not_called();b.insert.assert_not_called()
    def test_fill_cover_refuses_video_before_upload(self):
        b=Browser('fixture');b.js=Mock(side_effect=UIError('Not a unique image input'));b.upload=Mock()
        with self.assertRaises(UIError):b.fill_cover('input','file.mp4')
        b.upload.assert_not_called()
    def test_human_takeover_blocks_writes(self):
        p=self.pub();p.j['human_takeover']=True;p.text=Mock();p.evidence=Mock()
        with self.assertRaisesRegex(UIError,'User owns'):p.run('text')
        p.text.assert_not_called()
    def test_submit_requires_concrete_review_receipt(self):
        p=self.pub();p.authorization=None
        with self.assertRaises(ValueError):p.submit()
        p.b.semantic.assert_not_called()
    def test_uncertain_final_click_is_never_repeated(self):
        p=self.pub();p.p='bilibili';plan=p.review_plan=Mock(return_value={'review_fingerprint':'bound'})
        p.authorization={'approved':True,'platforms':{'bilibili':{'review_fingerprint':'bound','visibility':'public'}}}
        p.j['steps']['verify']={'status':'done'};p.j['cover_visual_review']='passed';p.b.js.return_value={'title':p.item['title'],'description':p.item['description']}
        p.b.semantic.side_effect=UIError('connection lost after click')
        with self.assertRaises(UIError):p.submit()
        self.assertTrue(json.loads(p.file.read_text('utf-8'))['submission_attempted'])
        p.confirm=Mock(return_value=light('submit',pending=True));self.assertEqual(p.submit()['light'],'yellow')
        self.assertEqual(p.b.semantic.call_count,1)
    def test_only_one_blocked_tag_is_routed_to_activity(self):
        p=self.pub();p.item.update(topics=['registered-a','registered-b','ordinary'])
        topic=BilibiliTopics(p);topic.chips=Mock(return_value=[]);topic.ordinary=Mock(side_effect=['activity_only','activity_only','added']);topic.activity=Mock()
        result=topic.apply();topic.activity.assert_called_once_with('registered-a')
        self.assertEqual(result['omitted_activity_limit'],['registered-b']);self.assertEqual(result['ordinary'],['ordinary'])
    def test_activity_disappearing_after_reopen_is_red(self):
        p=self.pub();p.j['bilibili_activity_topic']='registered';p.b.js.return_value=False
        with self.assertRaisesRegex(UIError,'Saved activity topic missing'):BilibiliTopics(p).verify_activity()

if __name__=='__main__':unittest.main()
