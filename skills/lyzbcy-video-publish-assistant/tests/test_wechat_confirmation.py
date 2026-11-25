import sys,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from extension_steps import wechat_confirm,UIError
from matrix_resume import pending

class WechatConfirmation(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.j=Path(self.tmp.name)/'j.json';self.j.write_text(json.dumps({'submission_attempted':True}))
  self.plan={'title':'Example lesson','account':'Example account','article_tab_id':2,'native_video_nonce':'12345','draft_id':'100'}
  self.row={'title':'Example lesson','url':'https://mp.weixin.qq.com/s/example','record':'今天 09:03\n已发表\nExample lesson'}
  self.view={'account_visible':True,'rows':[self.row]}
  self.article={'url':self.row['url'],'title':self.plan['title'],'account':self.plan['account'],'videos':[{'id':'export/example','nonce':'12345'}]}
 def browser(self):
  b=Mock();b.js.side_effect=[self.view,self.article];return b
 def test_public_row_and_current_video_confirm(self):
  b=self.browser();self.assertEqual(wechat_confirm(b,self.plan,self.j)['status'],'published');self.assertTrue(json.loads(self.j.read_text())['published']);b.send.assert_called_once_with('attach_tab',{'tabId':2})
 def test_reviewing_never_marks_published_or_opens_article(self):
  self.row['record']='今天 09:03\n审核中';b=self.browser();r=wechat_confirm(b,self.plan,self.j);self.assertEqual(r['status'],'under_review');b.send.assert_not_called();self.assertNotIn('published',json.loads(self.j.read_text()))
 def test_no_attempt_never_queries_old_posts(self):
  self.j.write_text('{}');b=self.browser()
  with self.assertRaises(UIError):wechat_confirm(b,self.plan,self.j)
  b.js.assert_not_called()
 def test_duplicate_or_wrong_account_does_not_confirm(self):
  for view in [{'account_visible':True,'rows':[self.row,self.row]},{'account_visible':False,'rows':[self.row]}]:
   self.view=view
   with self.assertRaises(UIError):wechat_confirm(self.browser(),self.plan,self.j)
 def test_temporary_or_spoof_links_do_not_confirm(self):
  for url in ['https://mp.weixin.qq.com/s?tempkey=x','https://mp.weixin.qq.com.evil.test/s/example','http://mp.weixin.qq.com/s/example','https://mp.weixin.qq.com/s/example?tempkey=x']:
   self.row['url']=url
   with self.assertRaises(UIError):wechat_confirm(self.browser(),self.plan,self.j)
 def test_unrelated_native_video_rejected(self):
  self.article['videos'][0]['nonce']='67890'
  with self.assertRaises(UIError):wechat_confirm(self.browser(),self.plan,self.j)
 def test_wrong_public_author_title_or_url_rejected(self):
  for key in ['account','title','url']:
   original=self.article[key];self.article[key]='wrong'
   with self.assertRaises(UIError):wechat_confirm(self.browser(),self.plan,self.j)
   self.article[key]=original
 def test_missing_or_duplicate_video_rejected(self):
  for videos in [[],self.article['videos']*2]:
   self.article['videos']=videos
   with self.assertRaises(UIError):wechat_confirm(self.browser(),self.plan,self.j)
 def test_verified_terminal_rows_are_skipped(self):
  for status in ['published_management_verified','published_profile_verified','published_article_with_external_video_links']:
   self.assertEqual(pending({'episodes':[{'episode':1,'platforms':{'any':{'status':status,'native_id':'100'}}}]}),[])
 def test_new_admin_state_requires_human_or_readback(self):
  rows=pending({'episodes':[{'episode':1,'platforms':{'wechat_official':{'status':'awaiting_admin_verification','submission_attempted':True}}}]})
  self.assertEqual(rows[0]['next'],'human_verification_or_current_publication_readback')

if __name__=='__main__':unittest.main()
