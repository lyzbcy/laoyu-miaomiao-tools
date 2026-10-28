"""v1.3.3 offline regressions: no login, upload, public post, or browser mutation."""
from pathlib import Path
import datetime,json,subprocess,sys,unittest,shutil,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import Mock,patch
from types import SimpleNamespace
S=Path(__file__).resolve().parents[1]/'skills/lyzbcy-video-publish-assistant/scripts'
sys.path.insert(0,str(S))
from browser import Browser,UIError,SCOPED_TARGET
from gates import publication_signal
from xiaohongshu import choose_topic,needs_topic_suffix,published_gate,apply_topics,confirm_published,PUBLISHED_ROWS,TOPIC_ROWS
from youtube import YouTubeDraft

class Transport(unittest.TestCase):
    def result(self):return SimpleNamespace(returncode=0,stdout=b'{"ok":true,"data":{}}',stderr=b'')
    def test_loopback_proxy_bypass(self):
        for host in ['127.0.0.1','localhost','[::1]','127.2.3.4']:
            with self.subTest(host=host),patch('browser.subprocess.run',return_value=self.result()) as run:
                Browser('test','http://'+host+':10086').send('snapshot')
                args=run.call_args.args[0];self.assertEqual(args[args.index('--noproxy')+1],'*')
                self.assertFalse(Path(args[-1][1:]).exists())
    def test_remote_proxy_preserved(self):
        for host in ['bridge.example.com','localhost.example.com','192.168.1.2']:
            with patch('browser.subprocess.run',return_value=self.result()) as run:
                Browser('test','http://'+host).send('snapshot')
                self.assertNotIn('--noproxy',run.call_args.args[0])
    def test_bad_envelope_stops(self):
        with patch.object(Browser,'curl',return_value={'ok':False,'error':'offline'}):
            with self.assertRaises(UIError):Browser('test').send('snapshot')
    def test_preflight_connected_read_only(self):
        b=Browser('test');b.curl=Mock(return_value={'running':True,'extension_connected':True});b.send=Mock(return_value=[])
        self.assertEqual(b.preflight()['bridge'],'ready');b.send.assert_called_once_with('list_browser_tabs')
    def test_preflight_disconnect_no_tab_action(self):
        for status in [{},{'running':True,'extension_connected':False},{'running':False,'extension_connected':True}]:
            b=Browser('test');b.curl=Mock(return_value=status);b.send=Mock()
            with self.assertRaises(UIError):b.preflight()
            b.send.assert_not_called()

class Topics(unittest.TestCase):
    def setUp(self):self.rows=[dict(name='#电脑技巧',id='topic-a',x=1,y=2),dict(name='#电脑技巧\u00a0',id='topic-b',x=3,y=4)]
    def test_ambiguous_fails_immediately_with_ids(self):
        with self.assertRaisesRegex(UIError,'topic-a'):choose_topic(self.rows,'电脑技巧')
    def test_configured_id(self):self.assertEqual(choose_topic(self.rows,'电脑技巧','topic-b')['x'],3)
    def test_wrong_id(self):
        with self.assertRaises(UIError):choose_topic(self.rows,'电脑技巧','missing')
    def test_duplicate_id_still_ambiguous(self):
        with self.assertRaises(UIError):choose_topic(self.rows*2,'电脑技巧','topic-b')
    def test_unique_without_id(self):self.assertEqual(choose_topic(self.rows[:1],'电脑技巧')['id'],'topic-a')
    def test_missing_topic(self):
        with self.assertRaises(UIError):choose_topic(self.rows,'别的')
    def test_partial_resume_does_not_append(self):self.assertFalse(needs_topic_suffix('正文 #电脑技巧 ','电脑技巧'))
    def test_new_suffix_required(self):self.assertTrue(needs_topic_suffix('正文','电脑技巧'))
    def test_linked_resume_zero_click(self):
        b=Mock();b.js.return_value='正文 #电脑技巧[话题]#';p=SimpleNamespace(b=b,item={'topics':['电脑技巧']},cfg={'editor':'#editor'})
        self.assertTrue(apply_topics(p)[0]['existing']);b.insert.assert_not_called();b.point.assert_not_called()
    def test_partial_resume_selects_configured_topic_once(self):
        b=Mock();b.js.side_effect=['正文 #电脑技巧','正文 #电脑技巧',self.rows];b.wait.side_effect=[self.rows,True]
        p=SimpleNamespace(b=b,item={'topics':['电脑技巧'],'topic_ids':{'电脑技巧':'topic-b'}},cfg={'editor':'#editor','topic_candidates':'.item .name'})
        self.assertEqual(apply_topics(p)[0]['topic_id'],'topic-b');b.insert.assert_not_called();b.point.assert_called_once_with(3,4)
    def test_changed_candidates_no_click(self):
        b=Mock();b.js.side_effect=['正文 #电脑技巧','正文 #电脑技巧',[]];b.wait.return_value=self.rows
        p=SimpleNamespace(b=b,item={'topics':['电脑技巧'],'topic_ids':{'电脑技巧':'topic-b'}},cfg={'editor':'#editor','topic_candidates':'.item .name'})
        with self.assertRaises(UIError):apply_topics(p)
        b.point.assert_not_called()

class Publication(unittest.TestCase):
    def state(self):return {'active_tab':'已发布','rows':[{'title':'测试稿件','note_id':'1234567890abcdef12345678','channel':'published','published_at':'2026-10-28 11:08','duration':116}]}
    def gate(self,state):return published_gate(state,'测试稿件','2026-10-28T11:07:59+08:00',116.4,datetime.datetime.fromisoformat('2026-10-28T11:10:00+08:00'))
    def test_fresh_unique_published(self):self.assertEqual(self.gate(self.state())['proof']['status'],'published')
    def test_wrong_or_unselected_tab(self):
        for tab in ['审核中','未通过',None]:
            s=self.state();s['active_tab']=tab;self.assertEqual(self.gate(s)['light'],'yellow')
    def test_old_title_row_is_not_new(self):
        s=self.state();s['rows'][0]['published_at']='2026-10-27 11:08';self.assertEqual(self.gate(s)['light'],'yellow')
    def test_duplicate_rows(self):
        s=self.state();s['rows']*=2;self.assertEqual(self.gate(s)['light'],'yellow')
    def test_missing_identity_wrong_title_duration_channel(self):
        for k,v in [('note_id',None),('note_id','garbage'),('title','旧稿件'),('duration',120),('channel','pending'),('published_at','bad'),('published_at','2026-10-29 11:08')]:
            s=self.state();s['rows'][0][k]=v;self.assertEqual(self.gate(s)['light'],'yellow',(k,v))
    def test_same_minute_old_row_remains_yellow(self):
        result=published_gate(self.state(),'测试稿件','2026-10-28T11:08:12+08:00',116.4)
        self.assertEqual(result['reason'],'minute_precision_requires_bound_note_id')
    def test_same_minute_bound_receipt_id(self):
        result=published_gate(self.state(),'测试稿件','2026-10-28T11:08:12+08:00',116.4,expected_note_id='1234567890abcdef12345678')
        self.assertEqual(result['light'],'green')
    def test_wrong_bound_receipt_id(self):
        result=published_gate(self.state(),'测试稿件','2026-10-28T11:08:12+08:00',116.4,expected_note_id='aaaaaaaaaaaaaaaaaaaaaaaa')
        self.assertEqual(result['light'],'yellow')
    def test_no_duration_or_started(self):
        self.assertEqual(published_gate(self.state(),'测试稿件',None,None)['light'],'yellow')
    def test_owned_redirect_only_submitted(self):
        s={'url':'https://creator.xiaohongshu.com/publish/publish?source=&published=true','text':''}
        self.assertEqual(publication_signal('xiaohongshu',s,'测试',True)['proof']['status'],'submitted')
        self.assertEqual(publication_signal('xiaohongshu',s,'测试',False)['light'],'yellow')
    def test_false_redirects(self):
        for url in ['https://evil.example/publish/publish?published=true','https://creator.xiaohongshu.com/publish/publish?published=false','https://creator.xiaohongshu.com/other?published=true']:
            self.assertEqual(publication_signal('xiaohongshu',{'url':url,'text':''},'测试',True)['light'],'yellow')
    def test_confirm_without_attempt_has_no_browser_action(self):
        p=SimpleNamespace(j={},b=Mock())
        with self.assertRaises(UIError):confirm_published(p)
        self.assertEqual(p.b.mock_calls,[])

class Scoped(unittest.TestCase):
    def test_scoped_close_uses_dom_not_global_ax(self):
        b=Browser('test');b.js=Mock(return_value={'x':1,'y':2,'disabled':False});b.point=Mock();b.send=Mock()
        b.semantic('button','关闭',scope='ytcp-uploads-dialog',video_id='abcdefghijk')
        b.point.assert_called_once_with(1,2);b.send.assert_not_called()
    def test_final_guard_works_inside_scope(self):
        b=Browser('test');b.js=Mock()
        with self.assertRaises(UIError):b.semantic('button','发布',scope='dialog')
        b.js.assert_not_called()
    def test_disabled_no_click(self):
        b=Browser('test');b.js=Mock(return_value={'disabled':True});b.point=Mock()
        with self.assertRaises(UIError):b.semantic('button','关闭',scope='dialog')
        b.point.assert_not_called()
    def test_scope_error_does_not_fallback(self):
        b=Browser('test');b.js=Mock(side_effect=UIError('scope missing'));b.send=Mock()
        with self.assertRaises(UIError):b.semantic('button','关闭',scope='dialog')
        b.send.assert_not_called()

class Reopen(unittest.TestCase):
    def make(self):
        b=Mock();p=SimpleNamespace(b=b,j={'youtube_kind':'video'},item={'title':'Test'},cfg={'title':'#title'},shown=Mock(side_effect=[False,True]),persist=Mock())
        d=YouTubeDraft(p);d.context=Mock(return_value={'draft_dialog':True,'title':'Test','text':''});d.remember=Mock()
        b.wait.side_effect=lambda fn,**kw: fn()
        b.js.return_value=True
        return p,d
    def test_already_target_route_no_tab_click(self):
        p,d=self.make();p.b.state.return_value={'url':'https://studio.youtube.com/channel/x/videos/upload'}
        d.reopen();p.b.semantic.assert_not_called();p.b.send.assert_called_once_with('click',{'selector':'ytcp-video-row[data-publish-draft=active] button[aria-label="编辑草稿"]'})
    def test_route_settles_before_ax_no_click(self):
        p,d=self.make();p.b.state.side_effect=[{'url':'https://studio.youtube.com/channel/x/videos/short'},{'url':'https://studio.youtube.com/channel/x/videos/upload'},{'url':'https://studio.youtube.com/channel/x/videos/upload'}]
        d.reopen();p.b.semantic.assert_not_called()
    def test_spa_ax_race_retries_only_ambiguous(self):
        p,d=self.make();p.b.state.return_value={'url':'https://studio.youtube.com/channel/x/videos/short'}
        def select(*args):
            if p.b.semantic.call_count==1:raise UIError("Ambiguous/missing semantic target ('tab', '视频', 0)")
            p.b.state.return_value={'url':'https://studio.youtube.com/channel/x/videos/upload'}
        p.b.semantic.side_effect=select
        values=[]
        def wait(fn,**kw):
            v=fn();values.append(v)
            if v is False:v=fn()
            self.assertTrue(v,'wait never accepts an unsettled route')
            return v
        p.b.wait.side_effect=wait;d.reopen();self.assertIs(values[0],False);self.assertEqual(p.b.semantic.call_count,2)
    def test_wrong_saved_id_stops(self):
        p,d=self.make();p.j.update(saved_edit_url='https://studio.youtube.com/video/abcdefghijk/edit',youtube_video_id='12345678901')
        with self.assertRaises(UIError):d.reopen()
        p.b.send.assert_not_called()

if __name__=='__main__':unittest.main()


@unittest.skipUnless(shutil.which('node'),'Node required for DOM replay')
class DOMReplay(unittest.TestCase):
    def run_js(self,source,setup):
        harness="const visible=e=>true;const getComputedStyle=e=>({visibility:'visible'});function el(text,role='button'){return {innerText:text,tagName:'BUTTON',disabled:false,getClientRects:()=>[1],getBoundingClientRect:()=>({x:1,y:2,width:10,height:10}),getAttribute:k=>k==='role'?role:null,scrollIntoView:()=>{},contains:()=>false}};"+setup+";try{console.log(JSON.stringify({ok:true,value:eval("+json.dumps(source)+")}))}catch(e){console.log(JSON.stringify({ok:false,error:e.message}))}"
        r=subprocess.run(['node','-e',harness],capture_output=True,text=True,encoding='utf8',check=True)
        return json.loads(r.stdout)
    def scoped(self,setup):return self.run_js(SCOPED_TARGET.replace('CFG',json.dumps({'scope':'ytcp-uploads-dialog','role':'button','name':'关闭','video_id':'abcdefghijk'})),setup)
    def root(self,children="[el('关闭')]",links="[{href:'https://youtu.be/abcdefghijk'}]",roots='[root]'):
        return "const root=el('upload');root.querySelectorAll=s=>s==='a[href]'?"+links+":"+children+";const document={querySelectorAll:s=>"+roots+"}"
    def test_other_dialog_close_is_not_selected(self):
        self.assertTrue(self.scoped(self.root())['ok'])
    def test_duplicate_close_inside_scope_fails(self):self.assertFalse(self.scoped(self.root("[el('关闭'),el('关闭')]"))['ok'])
    def test_missing_scope_fails(self):self.assertFalse(self.scoped(self.root(roots='[]'))['ok'])
    def test_multiple_dialogs_fail(self):self.assertFalse(self.scoped(self.root(roots='[root,root]'))['ok'])
    def test_other_video_link_fails(self):self.assertFalse(self.scoped(self.root(links="[{href:'https://youtu.be/12345678901'}]"))['ok'])
    def test_spoof_video_link_fails(self):self.assertFalse(self.scoped(self.root(links="[{href:'https://evil.example/abcdefghijk'}]"))['ok'])
    def test_published_dom_attribute_and_duration(self):
        setup="const row=el('01:56\\n测试稿件\\n2026-10-28 11:08');row.innerText=row.innerText.replaceAll('\\\\n','\\n');row.querySelector=s=>el('测试稿件');row.getAttribute=k=>JSON.stringify({noteTarget:{value:{noteId:'1234567890abcdef12345678'}},index:{value:{channelTabName:'published'}}});const document={querySelectorAll:()=>[row],querySelector:()=>el('已发布')}"
        r=self.run_js(PUBLISHED_ROWS.replace('TITLE',json.dumps('测试稿件')),setup)
        self.assertTrue(r['ok']);state=json.loads(r['value']);self.assertEqual(state['rows'][0]['duration'],116);self.assertEqual(state['rows'][0]['note_id'],'1234567890abcdef12345678')
    def test_topic_dom_attribute(self):
        setup="const row=el('#电脑技巧');row.closest=s=>s==='[data-impression]'?{getAttribute:()=>JSON.stringify({tagTarget:{value:{tagId:'topic-id'}}})}:null;const document={querySelectorAll:()=>[row]}"
        r=self.run_js(TOPIC_ROWS.replace('SELECTOR',json.dumps('.item .name')),setup)
        self.assertEqual(json.loads(r['value'])[0]['id'],'topic-id')

class LiveLocalTransport(unittest.TestCase):
    def test_dead_proxy_cannot_break_loopback_bridge(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                self.send_response(200);self.end_headers();self.wfile.write(json.dumps({'ok':True,'data':{'session':body['session']}}).encode())
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            with patch.dict('os.environ',{'HTTP_PROXY':'http://127.0.0.1:1','ALL_PROXY':'http://127.0.0.1:1','NO_PROXY':''}):
                self.assertEqual(Browser('regression','http://127.0.0.1:'+str(server.server_port)).send('snapshot'),{'session':'regression'})
        finally:server.shutdown();server.server_close();worker.join()
