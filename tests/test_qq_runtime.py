"""Public offline regression. No real accounts, credentials, or messages."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import types
import unittest
from unittest.mock import patch
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

R=Path(__file__).resolve().parents[1]
S=R/'skills/lyzbcy-qq-napcat-messenger'
QQ_UNDER_TEST=os.environ.get('QQ_SCRIPT_UNDER_TEST',str(S/'scripts/qq.py'))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.cfg=self.root/'cfg';self.cfg.mkdir()
        self.env=patch.dict(os.environ,{},clear=True);self.env.start();self.addCleanup(self.env.stop)
        os.environ.update(NAPCAT_CFG_DIR=str(self.cfg),QQ_SKILL_LOCAL_CONFIG=str(self.root/'local.json'))
        self.account('11111');self.account('22222')
        self.q=load('qq_test',QQ_UNDER_TEST)
        os.environ['NAPCAT_QQ']='22222'
    def account(self,qq,**server):
        value={'host':'127.0.0.1','port':30001,'token':'fixture-token','enable':True};value.update(server)
        (self.cfg/f'onebot11_{qq}.json').write_text(json.dumps({'network':{'httpServers':[value]}}),encoding='utf8')
    def main(self,*args):
        with patch.object(self.q.sys,'argv',['qq.py',*args]),contextlib.redirect_stdout(io.StringIO()) as output:
            self.q.main()
        return output.getvalue()
    def test_exact_account(self):
        self.q.configure();self.assertEqual(self.q.QQ,22222)
    def test_ambiguous_account_rejected(self):
        os.environ.pop('NAPCAT_QQ')
        with self.assertRaisesRegex(RuntimeError,'多个账号'):self.q.configure()
    def test_missing_explicit_account_does_not_fall_back(self):
        os.environ['NAPCAT_QQ']='33333'
        with self.assertRaisesRegex(RuntimeError,'指定账号'):self.q.configure()
    def test_disabled_http_rejected(self):
        self.account('22222',enable=False)
        with self.assertRaisesRegex(RuntimeError,'未启用'):self.q.configure()
    def test_bind_all_translates_to_loopback(self):
        self.account('22222',host='0.0.0.0');self.q.configure()
        self.assertEqual(self.q.API,'http://127.0.0.1:30001')
    def test_ipv6(self):
        self.account('22222',host='::');self.q.configure();self.assertEqual(self.q.API,'http://[::1]:30001')
    def test_version_no_config(self):
        os.environ['NAPCAT_CFG_DIR']=str(self.root/'missing')
        self.assertEqual(self.main('--version').strip(),'1.1.0')
    def test_doctor_no_config_no_token(self):
        self.q.CFG_DIR=str(self.root/'missing')
        value=json.loads(self.main('doctor'))
        self.assertFalse(value['ready']);self.assertNotIn('fixture-token',json.dumps(value))
    def test_doctor_wrong_account_not_ready(self):
        with patch.object(self.q,'call',return_value={'retcode':0,'data':{'user_id':11111}}):
            self.assertFalse(json.loads(self.main('doctor'))['ready'])
    def test_private_machine_config(self):
        local={'qq':'22222','node_dir':str(self.root/'node'),'cfg_dir':str(self.cfg),'desktop_qq':'myQQ.exe'}
        (self.root/'local.json').write_text(json.dumps(local))
        os.environ.pop('NAPCAT_QQ')
        q=load('qq_private',S/'scripts/qq.py');q.configure()
        self.assertEqual(q.QQ,22222);self.assertEqual(q.NODE_DIR,local['node_dir']);self.assertEqual(q.DESKTOP_QQ,'myQQ.exe')
    def test_env_overrides_private_config(self):
        (self.root/'local.json').write_text(json.dumps({'qq':'11111'}))
        q=load('qq_env',S/'scripts/qq.py');q.configure();self.assertEqual(q.QQ,22222)
    def test_explicit_legacy_override(self):
        os.environ['NAPCAT_SHELL']='legacy';os.environ['NAPCAT_NODE_DIR']='node'
        q=load('qq_node_override',S/'scripts/qq.py');self.assertEqual(q.NODE_DIR,'node')
        os.environ.pop('NAPCAT_NODE_DIR')
        (self.root/'local.json').write_text(json.dumps({'node_dir':'private-node'}))
        q=load('qq_legacy',S/'scripts/qq.py');self.assertEqual(q.NODE_DIR,'')
    def test_existing_login_reused_without_kill(self):
        with patch.object(self.q,'call',return_value={'retcode':0,'data':{'user_id':22222}}),patch.object(self.q,'kill_qq') as kill:
            self.assertIn('复用',self.main('grab'));kill.assert_not_called()
    def test_missing_runtime_checked_before_kill(self):
        self.q.NODE_DIR=str(self.root/'missing')
        with patch.object(self.q,'call',side_effect=OSError('offline')),patch.object(self.q,'kill_qq') as kill:
            with self.assertRaises(SystemExit):self.main('grab')
            kill.assert_not_called()
    def test_start_node_arguments(self):
        self.q.NODE_DIR=str(self.root);self.q.configure()
        for name in ('node.exe','index.js'):(self.root/name).write_text('fixture')
        with patch.object(self.q.subprocess,'Popen') as start:
            self.q.start_napcat()
            self.assertEqual(start.call_args.args[0][-2:],['-q','22222'])
            self.assertIn('node.exe',start.call_args.args[0][0])
    def test_failed_borrow_restores_desktop(self):
        with patch.object(self.q,'call',side_effect=OSError('offline')),patch.object(self.q.os.path,'isfile',return_value=True),patch.object(self.q,'kill_qq') as kill,patch.object(self.q.time,'sleep'),patch.object(self.q,'start_napcat'),patch.object(self.q,'login_wait',side_effect=SystemExit(1)),patch.object(self.q,'start_desktop') as desktop:
            with self.assertRaises(SystemExit):self.main('grab')
            self.assertEqual(kill.call_count,2);desktop.assert_called_once()
    def test_stop_only_dedicated_node(self):
        self.q.NODE_DIR=str(self.root/'dedicated')
        result=types.SimpleNamespace(returncode=0,stdout='[11,12]',stderr='')
        with patch.object(self.q.os,'name','nt'),patch.object(self.q.subprocess,'run',return_value=result) as run:
            self.q.stop_node_runtime()
            self.assertIn('ExecutablePath -eq',run.call_args_list[0].args[0][-1])
            self.assertEqual(run.call_args_list[1].args[0],['taskkill','/F','/T','/PID','11'])
            self.assertNotIn('/IM',str(run.call_args_list))
    def test_process_early_exit_no_wait(self):
        process=types.SimpleNamespace(poll=lambda:7,returncode=7)
        with patch.object(self.q.time,'sleep') as sleep,contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit):self.q.login_wait(process=process)
            self.assertIn('exit=7',output.getvalue());sleep.assert_not_called()
    def test_login_deadline_preserves_error(self):
        self.q.configure()
        with patch.object(self.q,'call',side_effect=OSError('connection refused')),contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit):self.q.login_wait(timeout=.01)
            self.assertIn('connection refused',output.getvalue())
    def test_mismatch_send_is_not_sent(self):
        calls=[]
        def call(ep,*a,**kw):calls.append(ep);return {'retcode':0,'data':{'user_id':11111}}
        with patch.object(self.q,'call',side_effect=call):
            with self.assertRaises(SystemExit):self.main('send','33333','fixture message')
        self.assertEqual(calls,['/get_login_info'])
    def test_stub_whoami_fails(self):
        with patch.object(self.q,'call',return_value={'retcode':0,'data':{}}):
            with self.assertRaises(SystemExit):self.main('whoami')
    def test_wrong_whoami_fails(self):
        with patch.object(self.q,'call',return_value={'retcode':0,'data':{'user_id':11111}}):
            with self.assertRaises(SystemExit):self.main('whoami')
    def test_file_name_alias(self):
        self.assertIn('fixture.xlsx',self.q.seg_text({'type':'file','data':{'file':'fixture.xlsx','file_id':'full-id'}}))
    def test_file_without_receipt_fails(self):
        with patch.object(self.q,'require_login'),patch.object(self.q,'call',return_value={'retcode':0,'data':{}}):
            with self.assertRaises(SystemExit):self.main('send-file','33333','fixture.xlsx')
    def test_loopback_really_bypasses_dead_proxy(self):
        requests=[]
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append((self.path,json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                self.send_response(200);self.end_headers();self.wfile.write(b'{"retcode":0,"data":{"user_id":22222}}')
            def log_message(self,*a):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            self.q.configure();self.q.API='http://127.0.0.1:'+str(server.server_port)
            os.environ.update(HTTP_PROXY='http://127.0.0.1:1',HTTPS_PROXY='http://127.0.0.1:1',NO_PROXY='')
            self.assertEqual(self.q.call('/get_login_info')['data']['user_id'],22222)
            self.assertEqual(requests,[('/get_login_info',{})])
        finally:server.shutdown();server.server_close()
    def test_error_redacts_token(self):
        self.q.configure();self.assertNotIn('fixture-token',self.q.clean_error(ValueError('fixture-token')))
    def test_bad_private_config_reported_by_doctor(self):
        (self.root/'local.json').write_text('{bad JSON')
        q=load('qq_bad_private',S/'scripts/qq.py')
        with contextlib.redirect_stdout(io.StringIO()) as output:q.doctor()
        self.assertFalse(json.loads(output.getvalue())['ready'])
    def test_target_path_escape_rejected(self):
        os.environ['NAPCAT_QQ']='../other'
        with self.assertRaises(ValueError):self.q.configure()

class SetupTests(unittest.TestCase):
    def setUp(self):
        self.mod=load('qq_setup_test',S/'scripts/runtime_setup.py')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def release(self,**kw):
        asset={'name':self.mod.ASSET,'digest':'sha256:'+'a'*64,'size':123,'browser_download_url':f'https://github.com/{self.mod.REPOSITORY}/releases/download/v4.18.41/{self.mod.ASSET}'};asset.update(kw)
        return {'tag_name':'v4.18.41','assets':[asset]}
    def test_target_bound_to_official_asset(self):
        target=self.mod.bind_target(self.release());self.assertEqual(target['tag'],'v4.18.41');self.assertEqual(target['sha256'],'a'*64)
    def test_untrusted_asset_rejected(self):
        with self.assertRaises(ValueError):self.mod.bind_target(self.release(browser_download_url='https://example.invalid/a.zip'))
    def test_missing_digest_rejected(self):
        with self.assertRaises(ValueError):self.mod.bind_target(self.release(digest=None))
    def test_zip_traversal_rejected_before_write(self):
        file=self.root/'evil.zip'
        with zipfile.ZipFile(file,'w') as z:z.writestr('../outside','bad')
        with self.assertRaises(ValueError):self.mod.extract_verified(file,{'sha256':hashlib.sha256(file.read_bytes()).hexdigest()},self.root/'target')
        self.assertFalse((self.root/'outside').exists())
    def test_hash_mismatch_rejected(self):
        file=self.root/'bad.zip';file.write_bytes(b'bad')
        with self.assertRaisesRegex(ValueError,'SHA256'):self.mod.extract_verified(file,{'sha256':'a'*64},self.root/'target')
    def test_complete_archive(self):
        file=self.root/'ok.zip'
        with zipfile.ZipFile(file,'w') as z:
            for name in ('node.exe','index.js','wrapper.node','napcat/napcat.mjs'):z.writestr(name,'fixture')
        self.mod.extract_verified(file,{'sha256':hashlib.sha256(file.read_bytes()).hexdigest()},self.root/'target')
        self.assertTrue((self.root/'target/node.exe').is_file())
    def test_incomplete_archive_rejected(self):
        file=self.root/'missing.zip'
        with zipfile.ZipFile(file,'w') as z:z.writestr('node.exe','fixture')
        with self.assertRaisesRegex(ValueError,'incomplete'):self.mod.extract_verified(file,{'sha256':hashlib.sha256(file.read_bytes()).hexdigest()},self.root/'target')
    def test_unknown_existing_runtime_is_preserved(self):
        target=self.mod.bind_target(self.release());cache=self.root/'cache';(cache/target['tag']).mkdir(parents=True)
        (cache/target['tag']/'user.txt').write_text('keep')
        with self.assertRaisesRegex(ValueError,'existing runtime'):self.mod.install(target,'22222',cache,self.root/'local.json',None)
        self.assertEqual((cache/target['tag']/'user.txt').read_text(),'keep')
    def test_install_and_reuse_preserve_private_settings(self):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:
            for name in ('node.exe','index.js','wrapper.node','napcat/napcat.mjs'):z.writestr(name,'fixture')
        data=stream.getvalue();target=self.mod.bind_target(self.release())
        target.update(size=len(data),sha256=hashlib.sha256(data).hexdigest())
        class Opener:
            calls=0
            def open(self,*a,**k):self.calls+=1;return io.BytesIO(data)
        opener=Opener();local=self.root/'local.json'
        local.write_text(json.dumps({'desktop_qq':'private-QQ.exe','unmanaged':'keep'}))
        directory=self.mod.install(target,'22222',self.root/'cache',local,opener)
        cfg=directory/'napcat/config/onebot11_22222.json'
        previous=cfg.read_bytes()
        self.mod.install(target,'22222',self.root/'cache',local,opener)
        self.assertEqual(opener.calls,1);self.assertEqual(cfg.read_bytes(),previous)
        value=json.loads(local.read_text());self.assertEqual(value['unmanaged'],'keep')
        self.assertEqual(value['desktop_qq'],'private-QQ.exe')

class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.mod=load('qq_updater',S/'scripts/update_skill.py')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/S.name;self.root.mkdir()
        (self.root/'SKILL.md').write_text('---\nmetadata:\n  version: "1.0.1"\n---\n')
        (self.root/'runtime.local.json').write_text('{"private":"keep"}')
        self.files={'SKILL.md':b'---\nmetadata:\n  version: "1.1.0"\n---\n'}
    def fetch(self,rel):
        if rel=='update.json':return json.dumps({'name':S.name,'version':'1.1.0','sha256':{k:hashlib.sha256(v).hexdigest() for k,v in self.files.items()}}).encode()
        return self.files[rel]
    def test_update_preserves_machine_settings(self):
        self.assertEqual(self.mod.check(self.root,self.fetch,'2026-10-29'),'updated')
        self.assertEqual((self.root/'runtime.local.json').read_text(),'{"private":"keep"}')
    def test_private_path_even_in_manifest_rejected(self):
        self.files['runtime.local.json']=b'overwrite'
        self.assertEqual(self.mod.check(self.root,self.fetch,'2026-10-29'),'failed')
        self.assertEqual((self.root/'runtime.local.json').read_text(),'{"private":"keep"}')
    def test_failed_update_retains_version(self):
        with patch.object(self.mod,'install',side_effect=OSError('fixture failure')):
            self.assertEqual(self.mod.check(self.root,self.fetch,'2026-10-29'),'failed')
        self.assertIn('1.0.1',(self.root/'SKILL.md').read_text())

if __name__=='__main__':unittest.main()
