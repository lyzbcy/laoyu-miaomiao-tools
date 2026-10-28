import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from select_motion import select


class SelectionTests(unittest.TestCase):
    def test_use_case_changes_output(self):
        examples = [('product_reveal', 1, False, 'hero_dolly'),
                    ('feature_overview', 2, False, 'depth_stack'),
                    ('feature_overview', 3, False, 'orbit_gallery'),
                    ('hook_statement', 0, True, 'kinetic_mask'),
                    ('scene_bridge', 2, False, 'whip_bridge'),
                    ('brand_payoff', 0, True, 'focus_pull')]
        for intent, images, copy, expected in examples:
            with self.subTest(intent=intent):
                self.assertEqual(select(dict(intent=intent, images=images, has_short_copy=copy))['selected']['recipe'], expected)

    def test_missing_assets_are_explained_not_fabricated(self):
        plan = select(dict(intent='scene_bridge', images=0))
        self.assertIsNone(plan['selected'])
        self.assertTrue(plan['fallback'])
        self.assertTrue(plan['rejected'][0]['missing_conditions'])

    def test_low_motion_avoids_camera_and_whip(self):
        for intent in ['scene_bridge', 'feature_overview', 'product_reveal']:
            plan = select(dict(intent=intent, images=3, has_short_copy=True, motion='reduced'))
            self.assertEqual(plan['selected']['recipe'], 'focus_pull')
            self.assertEqual(plan['selected']['shot_overrides'], {'reducedMotion': True})

    def test_reject_invalid_briefs(self):
        for brief in [dict(intent='unknown'), dict(intent='product_reveal', images=-1),
                      dict(intent='product_reveal', images=True), dict(intent='product_reveal', has_short_copy='yes')]:
            with self.assertRaises(ValueError):
                select(brief)


if __name__ == '__main__':
    unittest.main()
