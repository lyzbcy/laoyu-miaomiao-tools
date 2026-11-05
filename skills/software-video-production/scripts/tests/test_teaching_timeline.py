import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('teaching_timeline', Path(__file__).parents[1] / 'teaching_timeline.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TeachingTimelineTests(unittest.TestCase):
    def plan(self):
        return {'duration': 5, 'segments': [
            {'id': 'first', 'start': 0, 'end': 2, 'zh': '先看结果。', 'en': 'Check the result.'},
            {'id': 'second', 'start': 2, 'end': 5, 'zh': '换个条件再试。', 'en': 'Change one condition.'}],
            'events': [{'segment_id': 'first', 'at': 0.2, 'kind': 'camera', 'before': 'wide', 'after': 'result closeup', 'reason': 'show evidence'}]}

    def test_section_transition_does_not_cover_second_sentence(self):
        report = module.check(self.plan())
        self.assertFalse(report['valid'])
        self.assertIn('second: no mapped change event', report['errors'])

    def test_trimmed_preview_tail_requires_retiming(self):
        plan = self.plan()
        plan['duration'] = 4
        report = module.check(plan)
        self.assertIn('second: speech outside final timeline', report['errors'])

    def test_bilingual_and_event_identity_are_not_implicit(self):
        plan = self.plan()
        plan['segments'][0]['en'] = ''
        plan['events'][0]['segment_id'] = 'stale-id'
        report = module.check(plan)
        self.assertIn('first: missing bilingual text', report['errors'])
        self.assertIn('event 0: unknown segment', report['errors'])

    def test_generated_checkpoints_never_claim_review_passed(self):
        plan = self.plan()
        plan['events'].append({'segment_id': 'second', 'at': 2, 'kind': 'effect', 'before': 'success', 'after': 'connection fails', 'reason': 'test a prediction'})
        report = module.check(plan, 1.5)
        self.assertTrue(report['valid'])
        self.assertEqual([p['at'] for p in report['checkpoints']], [0, 1.5, 3, 4.5])
        self.assertTrue(all(p['human_review'] is None for p in report['checkpoints']))


if __name__ == '__main__':
    unittest.main()
