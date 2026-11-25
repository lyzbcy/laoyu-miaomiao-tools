import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
from gates import publication_signal
from browser import UIError
from xiaohongshu import confirm_published
from publication_registry import record
from youtube_api import upload, trusted


class Confirmation(unittest.TestCase):
    def test_youtube_new_receipt_is_bound(self):
        state={'published_dialog_text':'视频发布时间\nTest\n上传于2026年10月30日\n分享链接\nhttps://youtu.be/abcdefghijk'}
        self.assertEqual(publication_signal('youtube',state,'Test',True,'abcdefghijk')['light'],'green')
        for owned,video in [(False,'abcdefghijk'),(True,'12345678901'),(True,None)]:
            self.assertEqual(publication_signal('youtube',state,'Test',owned,video)['light'],'yellow')
    def test_row_ambiguity_never_confirms(self):
        self.assertEqual(publication_signal('youtube',dict(matching_row_text='Test\n公开',matching_row_video_id='abcdefghijk',row_count=2),'Test',True,'abcdefghijk')['light'],'yellow')
    def test_xhs_waits_for_async_cards(self):
        row=dict(title='Test',note_id='a'*24,channel='published',published_at='2026-10-30 11:16',duration=304)
        b=Mock();b.state.return_value={'url':'https://creator.xiaohongshu.com/new/note-manager'}
        b.js.side_effect=[{'active_tab':'已发布','rows':[]},{'active_tab':'已发布','rows':[row]}]
        def wait(fn,**kwargs):
            self.assertFalse(fn());return fn()
        b.wait.side_effect=wait
        p=SimpleNamespace(b=b,j={'submission_attempted':True,'submission_started_at':'2026-10-30T11:15:00+08:00','video_duration':304},item={'title':'Test'})
        self.assertEqual(confirm_published(p)['gate']['light'],'green')
        b.tap.assert_called_once_with(text='已发布')
    def test_xhs_timeout_stays_pending(self):
        b=Mock();b.state.return_value={'url':'/note-manager'};b.wait.side_effect=UIError('not ready');b.js.return_value={'active_tab':'已发布','rows':[]}
        p=SimpleNamespace(b=b,j={'submission_attempted':True,'submission_started_at':'2026-10-30T11:15:00+08:00','video_duration':304},item={'title':'Test'})
        self.assertEqual(confirm_published(p)['gate']['light'],'yellow')
        b.tap.assert_called_once_with(text='已发布')


class Registry(unittest.TestCase):
    def test_only_confirmed_identity_export_no_downgrade(self):
        with tempfile.TemporaryDirectory() as temp:
            m={'video_sha256':'f'*64,'content_id':'test','platforms':{'youtube':{'title':'Test','account_label':'owner'}}}
            self.assertIsNone(record(temp,m,'youtube',{'light':'yellow'},{}))
            self.assertFalse((Path(temp)/'publication-registry.json').exists())
            record(temp,m,'youtube',{'light':'green','proof':{'status':'published','video_id':'abcdefghijk'}},{})
            record(temp,m,'youtube',{'light':'green','proof':{'status':'submitted'}},{})
            p=json.loads((Path(temp)/'publication-registry.json').read_text())['publications']
            self.assertEqual(len(p),1);self.assertEqual(p[0]['status'],'published');self.assertEqual(p[0]['native_id'],'abcdefghijk')


class API(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.file=Path(self.temp.name)/'video.mp4';self.file.write_bytes(b'x'*400000);self.state=Path(self.temp.name)/'state.json'
        self.calls=[];self.fail_once=False;self.acked=0
    def tearDown(self):self.temp.cleanup()
    def request(self,method,url,headers,data=None):
        self.calls.append((method,url,headers,data))
        if method=='GET':return 200,{},b'{"items":[{"id":"channel"}]}'
        if method=='POST':
            self.assertEqual(json.loads(data)['status']['privacyStatus'],'private')
            return 200,{'Location':'https://www.googleapis.com/upload/session'},b''
        if not data:return 308,({'Range':'bytes=0-'+str(self.acked-1)} if self.acked else {}),b''
        self.acked+=len(data)
        if self.fail_once:
            self.fail_once=False;raise RuntimeError('network interruption after server acknowledgement')
        if self.acked>=400000:return 201,{},b'{"id":"abcdefghijk","status":{"privacyStatus":"private"}}'
        return 308,{'Range':'bytes=0-'+str(self.acked-1)},b''
    def test_upload_private_and_repeated_invocation_does_not_reupload(self):
        result=upload(self.file,'Test','channel',self.state,'token',self.request,262144)
        self.assertEqual(result['status'],'uploaded_private');count=len(self.calls)
        upload(self.file,'Test','channel',self.state,'token',self.request,262144)
        self.assertEqual(len(self.calls),count+1) # channel verification only
        self.assertNotIn('token',self.state.read_text())
    def test_interrupted_upload_probes_and_sends_only_remainder(self):
        self.fail_once=True
        with self.assertRaises(RuntimeError):upload(self.file,'Test','channel',self.state,'token',self.request,262144)
        upload(self.file,'Test','channel',self.state,'token',self.request,262144)
        posts=[c for c in self.calls if c[0]=='POST'];chunks=[c for c in self.calls if c[0]=='PUT' and c[3]]
        self.assertEqual(len(posts),1);self.assertTrue(chunks[-1][2]['Content-Range'].startswith('bytes 262144-'))
    def test_file_change_cannot_reuse_session(self):
        upload(self.file,'Test','channel',self.state,'token',self.request,262144);self.file.write_bytes(b'changed')
        with self.assertRaises(ValueError):upload(self.file,'Test','channel',self.state,'token',self.request,262144)
    def test_unknown_creation_does_not_start_another_session(self):
        def fail(method,*args):
            if method=='GET':return 200,{},b'{"items":[{"id":"channel"}]}'
            raise RuntimeError('lost session creation response')
        with self.assertRaises(RuntimeError):upload(self.file,'Test','channel',self.state,'token',fail)
        with self.assertRaisesRegex(ValueError,'creation result unknown'):upload(self.file,'Test','channel',self.state,'token',self.request)
        self.assertFalse(any(c[0]=='POST' for c in self.calls))
    def test_channel_mismatch_and_bad_session_url(self):
        with self.assertRaises(ValueError):upload(self.file,'Test','other',self.state,'token',self.request)
        for u in ['https://evil.example/session','http://www.googleapis.com/session','https://www.googleapis.com.evil.example/session','https://user@www.googleapis.com/session']:
            with self.assertRaises(ValueError):trusted(u)


if __name__=='__main__':unittest.main()
