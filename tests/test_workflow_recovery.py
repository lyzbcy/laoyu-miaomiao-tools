"""Local-only workflow proof and compact recovery tests."""
from pathlib import Path
import hashlib, importlib.util, json, tempfile, unittest

ROOT=Path(__file__).resolve().parents[1]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


w=module('workflow_audit',ROOT/'skills/software-video-production/scripts/workflow_audit.py')
r=module('run_status',ROOT/'skills/lyzbcy-video-publish-assistant/scripts/run_status.py')


class EvidenceWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.path=self.root/'workflow.json'
        self.proof=self.root/'proof.txt';self.proof.write_text('observed evidence')

    def test_conditional_steps_are_created_only_when_requested(self):
        result=w.plan(self.path,series=True,image_cover=True)
        self.assertIn('series_context',result['steps']);self.assertIn('cover_generation',result['steps'])
        self.assertFalse(w.audit(self.path)['complete'])

    def test_existing_workflow_cannot_be_reset(self):
        w.plan(self.path)
        with self.assertRaises(ValueError):w.plan(self.path)

    def test_file_proofs_complete_the_declared_steps(self):
        data=w.plan(self.path)
        for name in data['steps']:w.record(self.path,name,evidence=self.proof)
        result=w.audit(self.path)
        self.assertTrue(result['production_complete'])
        self.assertFalse(result['complete'])
        self.assertIn('contribution',result['closeout']['remaining'])

    def test_changed_proof_invalidates_done_step(self):
        w.plan(self.path);w.record(self.path,'hook',evidence=self.proof)
        self.proof.write_text('revised')
        self.assertEqual(w.audit(self.path)['remaining']['hook'],'evidence_changed')

    def test_missing_proof_does_not_mark_complete(self):
        w.plan(self.path)
        with self.assertRaises(ValueError):w.record(self.path,'hook',evidence=self.root/'absent')

    def test_blocked_step_retains_reason(self):
        w.plan(self.path);w.record(self.path,'audio',blocked='waiting for source')
        self.assertEqual(w.audit(self.path)['remaining']['audio'],'waiting for source')

    def test_removed_required_series_step_is_rejected(self):
        data=w.plan(self.path,series=True);del data['steps']['series_context'];w.save(self.path,data)
        with self.assertRaises(ValueError):w.audit(self.path)


class CompactRecovery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.item={'title':'Test'}
        self.state={'video_sha256':'video','copy_sha256':hashlib.sha256(json.dumps(self.item,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'steps':{}}

    def next(self,platform='youtube'):
        return r.next_action(platform,self.item,self.state,'video',self.root)

    def test_changed_copy_stops_reuse(self):
        self.item['title']='Changed';self.assertEqual(self.next()['action'],'review_changed_manifest')

    def test_uncertain_upload_never_recommends_upload(self):
        self.state['upload_attempted']=True;self.assertEqual(self.next()['action'],'inspect_upload_once')

    def test_attempted_post_only_recommends_query(self):
        self.state['submission_attempted']=True;self.state['last_error']={'step':'submit','error':'timeout'}
        self.assertEqual(self.next()['action'],'confirm')

    def test_matching_public_receipt_needs_no_browser_read(self):
        self.state.update(submission_attempted=True,youtube_video_id='abcdefghijk')
        (self.root/'youtube-publication.json').write_text(json.dumps({'gate':{'proof':{'status':'public','video_id':'abcdefghijk'}}}))
        self.assertEqual(self.next()['action'],'done')

    def test_other_video_receipt_does_not_finish(self):
        self.state.update(submission_attempted=True,youtube_video_id='abcdefghijk')
        (self.root/'youtube-publication.json').write_text(json.dumps({'gate':{'proof':{'status':'public','video_id':'12345678901'}}}))
        self.assertEqual(self.next()['action'],'confirm')

    def test_completed_cover_still_needs_crop_review(self):
        self.state['steps']={name:{'status':'done'} for name in ['upload','text','declaration','topics','settings','covers','checks']}
        self.assertEqual(self.next()['action'],'review_covers')

    def test_local_error_is_repaired_without_another_full_inspect(self):
        self.state['last_error']={'step':'topics','error':'one target missing'}
        self.assertEqual(self.next()['action'],'repair_from_local_error')

    def test_experimental_platform_is_never_treated_as_cli_supported(self):
        self.assertEqual(self.next('x')['action'],'manual_ui_adapter_required')
        self.state['submission_attempted']=True
        self.assertEqual(self.next('x')['action'],'query_manual_ui')

    def test_changed_manual_terminal_evidence_requires_query(self):
        proof=self.root/'proof.json';proof.write_text('observed')
        self.state.update(submission_attempted=True,terminal_review={
            'status':'published','id':'observed-id','video_sha256':'video',
            'copy_sha256':self.state['copy_sha256'],'evidence':str(proof),
            'evidence_sha256':r.digest(proof)})
        self.assertEqual(self.next('bilibili')['action'],'done')
        proof.write_text('changed')
        self.assertEqual(self.next('bilibili')['action'],'confirm')


if __name__=='__main__':unittest.main()
