import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import contribution as c
import update_skill as u


def skill(v):
    return f'---\nname: lyzbcy-fitness-tracker\nmetadata:\n  version: "{v}"\n---\n'.encode()


class UpdateTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        (self.root/'SKILL.md').write_bytes(skill('1.2.0'))
        self.files={'SKILL.md':skill('1.2.1'),'scripts/example.py':b'updated\n'}
        self.calls=[]

    def tearDown(self):
        self.tmp.cleanup()

    def remote(self, version='1.2.1'):
        self.files['SKILL.md']=skill(version)
        data={'name':u.NAME,'version':version,'release_tag':'v1.50.0',
              'sha256':{k:hashlib.sha256(v).hexdigest() for k,v in self.files.items()}}
        raw=json.dumps(data).encode()
        def fetch(rel,rev):
            self.calls.append((rel,rev))
            return raw if rel=='update.json' else self.files[rel]
        release=lambda tag:{'tag_name':tag,'draft':False,'prerelease':False,'target_commitish':'a'*40,
                            'assets':[{'name':u.NAME+'.zip','state':'uploaded'}]}
        return fetch,release

    def check(self, **kwargs):
        f,r=self.remote(kwargs.pop('version','1.2.1'))
        return u.check(self.root,fetch=f,release=r,today='2026-11-02',**kwargs)

    def test_update_pins_files_and_keeps_private_data(self):
        (self.root/'config.json').write_text('private config')
        self.assertEqual(self.check(),'updated')
        self.assertEqual(u.local_version(self.root),(1,2,1))
        self.assertEqual((self.root/'config.json').read_text(),'private config')
        self.assertTrue(all(ref=='a'*40 for rel,ref in self.calls if rel!='update.json'))
        self.assertFalse((self.root/'.update-backup').exists())

    def test_once_per_day_and_manual_force_queries_again(self):
        self.assertEqual(self.check(),'updated')
        self.calls.clear()
        self.assertEqual(self.check(),'already_checked');self.assertFalse(self.calls)
        self.assertEqual(self.check(force=True),'current');self.assertTrue(self.calls)
        state=json.loads((self.root/'.update-check.json').read_text())
        self.assertEqual(state['last_success'],'2026-11-02')

    def test_network_failure_preserves_old_and_retries_next_day(self):
        fail=lambda *_: (_ for _ in ()).throw(OSError('offline'))
        self.assertEqual(u.check(self.root,fetch=fail,today='2026-11-02'),'failed')
        self.assertEqual(u.local_version(self.root),(1,2,0))
        state=json.loads((self.root/'.update-check.json').read_text())
        self.assertNotIn('last_success',state)
        self.assertEqual(self.check(),'already_checked')
        f,r=self.remote()
        self.assertEqual(u.check(self.root,fetch=f,release=r,today='2026-11-03'),'updated')

    def test_corrupt_file_does_not_install_anything(self):
        f,r=self.remote()
        def corrupt(rel,ref):
            return b'corrupt' if rel=='scripts/example.py' else f(rel,ref)
        self.assertEqual(u.check(self.root,fetch=corrupt,release=r,force=True),'failed')
        self.assertEqual((self.root/'SKILL.md').read_bytes(),skill('1.2.0'))
        self.assertFalse((self.root/'scripts/example.py').exists())

    def test_cached_binary_remains_byte_exact_and_is_not_downloaded(self):
        binary=b'font\x00\r\nunchanged'
        (self.root/'font.ttf').write_bytes(binary);self.files['font.ttf']=binary
        self.assertEqual(self.check(),'updated')
        self.assertNotIn('font.ttf',[x[0] for x in self.calls])
        self.assertEqual((self.root/'font.ttf').read_bytes(),binary)

    def test_local_customization_is_not_overwritten(self):
        path=self.root/'custom.py';path.write_bytes(b'user changes')
        (self.root/'update.json').write_text(json.dumps({'sha256':{'custom.py':hashlib.sha256(b'original').hexdigest()}}))
        self.assertEqual(self.check(),'failed')
        self.assertEqual(path.read_bytes(),b'user changes')

    def test_paths_and_user_data_cannot_be_managed(self):
        for rel in ['../escape','/tmp/escape','config.json','workspace/config.json','.git/config','a\\b','C:/escape']:
            with self.assertRaises(ValueError):u.safe_path(self.root,rel)
        self.assertEqual(u.safe_path(self.root,'.gitignore'),self.root/'.gitignore')

    def test_drafts_missing_packages_and_mutable_refs_are_rejected(self):
        f,r=self.remote()
        for change in [{'draft':True},{'prerelease':True},{'assets':[]},{'target_commitish':'main'}]:
            self.assertEqual(u.check(self.root,fetch=f,release=lambda tag:{**r(tag),**change},force=True),'failed')

    def test_install_failure_rolls_back_and_cleans_journal(self):
        real=u.os.replace
        def fail_entry(src,dst):
            if str(dst).endswith('SKILL.md'):raise OSError('locked entry')
            return real(src,dst)
        with patch.object(u.os,'replace',side_effect=fail_entry):
            self.assertEqual(self.check(),'failed')
        self.assertEqual((self.root/'SKILL.md').read_bytes(),skill('1.2.0'))
        self.assertFalse((self.root/'scripts/example.py').exists())
        self.assertFalse((self.root/'.update-journal.json').exists())

    def test_recovery_runs_before_daily_throttle(self):
        b=self.root/'.update-backup';b.mkdir();(b/'SKILL.md').write_bytes(skill('1.2.0'))
        (self.root/'SKILL.md').write_bytes(skill('9.0.0'))
        (self.root/'.update-journal.json').write_text(json.dumps({'SKILL.md':True}))
        (self.root/'.update-check.json').write_text(json.dumps({'last_attempt':'2026-11-02'}))
        self.assertEqual(self.check(),'already_checked')
        self.assertEqual(u.local_version(self.root),(1,2,0))

    def test_no_downgrade_and_numeric_version_order(self):
        self.assertGreater(u.version('0.10.0'),u.version('0.9.9'))
        self.assertEqual(self.check(version='1.1.9'),'current')
        self.assertEqual(u.local_version(self.root),(1,2,0))

    def test_background_is_detached_silent_and_never_fetches_in_caller(self):
        with patch.object(u,'source_checkout',return_value=False),patch.object(u.subprocess,'Popen') as spawn:
            u.start_background(self.root)
            self.assertEqual(spawn.call_count,1)
            self.assertEqual(spawn.call_args.kwargs['stdout'],u.subprocess.DEVNULL)
        (self.root/'.git').mkdir()
        self.assertEqual(self.check(),'source_checkout')


class ContributionTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.summary=self.root/'reviewed.md';self.summary.write_text('Synthetic grouping reproduction and verified fix.',encoding='utf-8')
        self.diff=self.root/'minimal.patch';self.diff.write_text('--- old\n+++ new\n+synthetic fixture\n',encoding='utf-8')

    def tearDown(self):self.tmp.cleanup()

    def prepare(self):return c.prepare(self.root,self.summary,self.diff,confirmed=True)

    def test_requires_final_confirmation_and_rejects_raw_records(self):
        with self.assertRaises(ValueError):c.prepare(self.root,self.summary)
        raw=self.root/'records.jsonl';raw.write_text('{}')
        with self.assertRaises(ValueError):c.prepare(self.root,raw,confirmed=True)
        self.summary.write_text('Private local path /home/example/training')
        with self.assertRaises(ValueError):self.prepare()

    def test_pending_is_not_consent(self):
        draft=self.prepare();result=c.answer(self.root,draft['run_id'],'pending')
        self.assertFalse(result['submitted']);self.assertFalse(result['cleaned'])
        self.assertTrue(Path(draft['draft']).is_file())

    def test_decline_cleans_owned_files_and_preserves_originals(self):
        draft=self.prepare();result=c.answer(self.root,draft['run_id'],'decline')
        self.assertTrue(result['folder_removed'])
        self.assertTrue(self.summary.exists());self.assertTrue(self.diff.exists())

    def test_accept_requires_result_before_cleanup_and_allows_anonymous(self):
        draft=self.prepare()
        with self.assertRaises(ValueError):c.answer(self.root,draft['run_id'],'accept')
        self.assertTrue(Path(draft['draft']).exists())
        result=c.answer(self.root,draft['run_id'],'accept',result_url='https://github.com/lyzbcy/laoyu-miaomiao-tools/pull/123')
        self.assertEqual(result['credit'],'anonymous');self.assertFalse(result['merged'])
        self.assertTrue(result['folder_removed'])

    def test_failed_submission_retains_minimal_patch_then_cleans(self):
        draft=self.prepare();target=self.root/'contributions/reviewed.patch'
        result=c.answer(self.root,draft['run_id'],'accept',patch_out=target)
        self.assertEqual(target.read_bytes(),self.diff.read_bytes());self.assertTrue(result['folder_removed'])
        self.assertIsNone(result['pr_url'])

    def test_unknown_files_are_not_recursively_deleted(self):
        draft=self.prepare();folder=Path(draft['draft']).parent
        (folder/'somebody-elses.txt').write_text('keep')
        result=c.answer(self.root,draft['run_id'],'decline')
        self.assertFalse(result['folder_removed']);self.assertTrue((folder/'somebody-elses.txt').is_file())

    def test_traversal_and_symlinks_are_rejected(self):
        with self.assertRaises(ValueError):c.run_dir(self.root,'../other')
        draft=self.prepare()
        with patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaises(ValueError):c.answer(self.root,draft['run_id'],'decline')
        self.assertTrue(Path(draft['draft']).exists())


if __name__=='__main__':unittest.main()
