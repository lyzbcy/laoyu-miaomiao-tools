"""Closeout reminders survive independently of chat history."""
from pathlib import Path
import importlib.util, json, tempfile, unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'skills/software-video-production/scripts/closeout.py'
spec=importlib.util.spec_from_file_location('closeout_cases',SOURCE)
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


class Closeout(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.ledger=self.root/'closeout.json'
        c.plan(self.ledger)
        self.proof=self.root/'evidence.json';self.proof.write_text('{}')

    def test_init_persists_pr_archive_and_cleanup_even_before_delivery(self):
        result=c.audit(self.ledger)
        self.assertFalse(result['complete'])
        for name in ['experience_review','contribution','archive','cleanup','contribution_cleanup']:
            self.assertIn(name,result['remaining'])

    def test_resume_does_not_reset_decisions(self):
        c.record(self.ledger,'experience_review','valuable',self.proof)
        with self.assertRaises(ValueError):c.plan(self.ledger)
        self.assertEqual(c.load(self.ledger)['tasks']['experience_review']['status'],'valuable')

    def test_cannot_record_a_pr_without_the_consent_receipt(self):
        with self.assertRaises(ValueError):
            c.record(self.ledger,'contribution','submitted',self.proof,url='https://github.com/example/project/pull/1')

    def test_submitted_pr_retains_approval_and_url(self):
        c.record(self.ledger,'contribution','approved',self.proof)
        c.record(self.ledger,'contribution','submitted',self.proof,url='https://github.com/example/project/pull/1')
        self.assertNotIn('contribution',c.audit(self.ledger)['remaining'])
        self.assertEqual(c.audit(self.ledger)['pr_url'],'https://github.com/example/project/pull/1')

    def test_changed_consent_invalidates_submitted_state(self):
        c.record(self.ledger,'contribution','approved',self.proof)
        self.proof.write_text('changed')
        with self.assertRaises(ValueError):
            c.record(self.ledger,'contribution','submitted',self.proof,url='https://github.com/example/project/pull/1')

    def test_archive_requires_the_preserved_files_to_exist_and_match(self):
        index=self.root/'archive.json';index.write_text(json.dumps({'files':[{'path':str(self.proof),'sha256':c.digest(self.proof)}]}))
        c.record(self.ledger,'archive','verified',index)
        self.proof.write_text('modified')
        self.assertEqual(c.audit(self.ledger)['remaining']['archive'],'result_evidence_invalid')

    def test_cleanup_cannot_claim_a_file_was_removed_while_it_exists(self):
        receipt=self.root/'cleanup.json';receipt.write_text(json.dumps({'deleted':[str(self.proof)]}))
        with self.assertRaises(ValueError):c.record(self.ledger,'cleanup','cleaned',receipt)

    def test_cleanup_requires_separate_consent_even_when_paths_are_absent(self):
        receipt=self.root/'cleanup.json';receipt.write_text(json.dumps({'deleted':[str(self.root/'already-absent')]}))
        with self.assertRaises(ValueError):c.record(self.ledger,'cleanup','cleaned',receipt)
        c.record(self.ledger,'cleanup','approved',self.proof)
        c.record(self.ledger,'cleanup','cleaned',receipt)
        self.assertNotIn('cleanup',c.audit(self.ledger)['remaining'])

    def test_awaiting_cleanup_consent_remains_visible(self):
        c.record(self.ledger,'cleanup','awaiting_consent',self.proof,reason='four old exports')
        self.assertEqual(c.audit(self.ledger)['remaining']['cleanup'],'awaiting_consent')

    def test_no_value_assessment_can_skip_pr_but_not_silently(self):
        with self.assertRaises(ValueError):c.record(self.ledger,'contribution','not_needed',self.proof)
        c.record(self.ledger,'experience_review','not_valuable',self.proof)
        c.record(self.ledger,'contribution','not_needed',self.proof)
        self.assertNotIn('contribution',c.audit(self.ledger)['remaining'])

    def test_shipped_copies_match(self):
        other=ROOT/'skills/lyzbcy-video-publish-assistant/scripts/closeout.py'
        self.assertEqual(SOURCE.read_bytes(),other.read_bytes())


if __name__=='__main__':unittest.main()
