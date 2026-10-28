from pathlib import Path
import sys,unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/lyzbcy-video-publish-assistant/scripts'))
from browser import Browser,UIError
from gates import validate_context,description_matches,normalized
from prepare_upload import check
import test_publisher as fixtures

class BrowserRegression(unittest.TestCase):
    def test_scalar_dom_attribute_is_not_coerced_to_boolean(self):
        b=Browser('offline');b.send=Mock(return_value={'type':'string','value':'true'})
        self.assertEqual(b.js('attribute'),'true');self.assertIsInstance(b.js('attribute'),str)
    def test_json_array_and_object_still_decoded(self):
        b=Browser('offline');b.send=Mock(side_effect=[{'type':'string','value':'["tag"]'},{'type':'string','value':'{"checked":true}'}])
        self.assertEqual(b.js('array'),['tag']);self.assertEqual(b.js('object'),{'checked':True})
    def test_enter_uses_real_key_on_unique_control(self):
        b=Browser('offline');b.focus=Mock();b.js=Mock();b.key=Mock();b.enter('input.exact')
        b.key.assert_called_once_with('Enter');self.assertIn('Enter target ambiguous',b.js.call_args.args[0])

class ContextRegression(unittest.TestCase):
    def test_matching_account_visibility_and_prefix(self):
        r=validate_context('douyin',{'expected_account_markers':['creator-id'],'visibility':'public'},{'account_text':'creator-id','visibility':'public','description':'exact-prefix\nbody','platform':'douyin'},'exact-prefix')
        self.assertEqual(r['light'],'green')
    def test_wrong_account_fails(self):
        with self.assertRaisesRegex(ValueError,'Account'):validate_context('p',{'expected_account_markers':['wanted']},{'account_text':'other'})
    def test_unverified_visibility_fails(self):
        with self.assertRaisesRegex(ValueError,'visibility'):validate_context('p',{'visibility':'public'},{'visibility':'private'})
    def test_prefix_is_exact_not_a_substring(self):
        with self.assertRaisesRegex(ValueError,'prefix'):validate_context('p',{}, {'description':'extra exact'},'exact')
    def test_other_platform_observation_rejected(self):
        with self.assertRaisesRegex(ValueError,'another platform'):validate_context('p',{}, {'platform':'other'})
    def test_old_and_new_douyin_serializations(self):
        self.assertEqual(normalized('a\n*b','douyin'),'a b')
        self.assertTrue(description_matches('a\nb','a\n*b','douyin'))
        self.assertTrue(description_matches('exact\nred book\n50+10','exactred book50+10','douyin'))
        self.assertFalse(description_matches('red book','redbook','douyin'))
        self.assertFalse(description_matches('50+10','50+9','douyin'))

class PublisherRegression(unittest.TestCase):
    setUp=fixtures.PublisherTests.setUp
    save=fixtures.PublisherTests.save
    pub=fixtures.PublisherTests.pub
    def test_dry_run_never_operates_browser_even_after_submission(self):
        p=self.pub();p.j['submission_attempted']=True;r=p.dry_run()
        self.assertFalse(r['would_submit']);self.assertEqual(r['next'],'confirm_only')
        p.b.select.assert_not_called();p.b.send.assert_not_called();p.b.upload.assert_not_called();p.b.semantic.assert_not_called()
    def test_pinned_tab_cannot_be_stolen_by_another_same_host_tab(self):
        p=self.pub();p.j['tab_id']=42;p.select();p.b.select.assert_not_called();p.b.send.assert_called_once_with('attach_tab',{'tabId':42})
    def test_pinned_tab_on_wrong_host_stops(self):
        p=self.pub();p.j['tab_id']=42;p.b.send.return_value={'url':'https://other.example','tabId':42}
        with self.assertRaisesRegex(UIError,'another host'):p.select()
    def test_open_routes_only_known_home_before_first_upload(self):
        p=self.pub();p.cfg['home_url']='https://studio.youtube.com/channel/known';p.b.select.return_value={'tabId':101,'url':p.cfg['home_url']};p.open()
        p.b.send.assert_called_once_with('navigate',{'url':p.cfg['url']})
    def test_open_does_not_restart_an_existing_upload(self):
        p=self.pub();p.cfg['home_url']='https://studio.youtube.com/channel/known';p.b.select.return_value={'tabId':101,'url':p.cfg['home_url']};p.j['upload_attempted']=True;p.open()
        p.b.send.assert_not_called()
    def test_closed_pinned_draft_is_not_replaced(self):
        p=self.pub();p.j['tab_id']=42;p.b.send.side_effect=UIError('tab was closed')
        with self.assertRaises(UIError):p.open()
        p.b.open.assert_not_called()
    @patch('prepare_upload.shutil.which',return_value=None)
    def test_prefix_preflight_does_not_allow_leading_text(self,_):
        self.data['required_description_prefix']='Required';self.save()
        with self.assertRaisesRegex(ValueError,'prefix'):check(self.manifest)
    @patch('prepare_upload.shutil.which',return_value=None)
    def test_bilibili_empty_tags_fail_before_upload(self,_):
        self.data['platforms']={'bilibili':{'title':'vlog','description':'body','topics':[]}};self.save()
        with self.assertRaisesRegex(ValueError,'at least one'):check(self.manifest)

if __name__=='__main__':unittest.main()
