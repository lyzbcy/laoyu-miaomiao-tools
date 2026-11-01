"""Regression checks use temporary ledgers; never append to real training history."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import daily_poster as p


def row(action='set', time='15:30:00', **extra):
    return dict(date='2026-10-31', ts=f'2026-10-31T{time}+08:00', action=action,
                **({'exercise': '器械划船', 'weight': 40, 'reps': 12,
                    'session': 'pull', 'muscleGroup': 'back'} if action == 'set' else {}), **extra)


class FactsTest(unittest.TestCase):
    def test_volume_preserves_half_reps_and_excludes_bodyweight(self):
        rows = [row(), {**row(), 'reps': 1.5}, {**row(), 'weight': 0},
                {**row(), 'weight': None}, row('note', note='体重80kg，左手右手都做了')]
        a = p.aggregate(rows, '2026-10-31')
        self.assertEqual(a['today_kg'], 540)
        self.assertEqual(a['reps'], 37.5)
        self.assertEqual(a['uncounted_sets'], 2)

    def test_history_does_not_include_future(self):
        rows = [row(), {**row(), 'date': '2026-10-30'}, {**row(), 'date': '2026-11-01'}]
        self.assertEqual(p.aggregate(rows, '2026-10-31')['history_kg'], 960)

    def test_complete_requires_end_after_last_set(self):
        a = p.aggregate([row('session_end', '15:00:00'), row()], '2026-10-31')
        self.assertFalse(a['complete'])
        a = p.aggregate([row('session_start', '15:00:00'), row(), row('session_end', '16:00:00')], '2026-10-31')
        self.assertTrue(a['complete'])
        self.assertTrue(a['exact_timing'])
        self.assertEqual(a['duration_minutes'], 60)

    def test_missing_start_labeled_as_record_span(self):
        a = p.aggregate([row(), row('session_end', '16:00:00')], '2026-10-31')
        self.assertTrue(a['complete'])
        self.assertFalse(a['exact_timing'])
        self.assertIn('跨度', a['timing_basis'])

    def test_multiple_sessions_do_not_claim_active_duration(self):
        a = p.aggregate([row('session_start', '10:00:00'), row('session_end', '11:00:00'),
                         row('session_start', '15:00:00'), row(), row('session_end', '16:00:00')], '2026-10-31')
        self.assertIn('含间歇', a['timing_basis'])
        self.assertFalse(a['exact_timing'])

    def test_naive_time_assumed_shanghai_and_mismatch_rejected(self):
        a = p.aggregate([{**row(), 'ts': '2026-10-31T15:30:00'}], '2026-10-31')
        self.assertEqual(a['start'], '15:30')
        with self.assertRaises(ValueError):
            p.aggregate([{**row(), 'ts': '2026-10-30T20:00:00+08:00'}], '2026-10-31')

    def test_cardio_duration_is_not_zero(self):
        a = p.aggregate([row('cardio', '16:00:00', durationMin=35, exercise='游泳')], '2026-10-31')
        self.assertEqual((a['start'], a['end'], a['duration_minutes']), ('15:25', '16:00', 35))
        self.assertEqual(a['today_kg'], 0)

    def test_bad_records_fail_visibly(self):
        for value in [-1, 'NaN', float('inf'), True]:
            with self.assertRaises(ValueError):
                p.aggregate([{**row(), 'weight': value}], '2026-10-31')
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'bad.jsonl'
            path.write_text('{}\nnot json\n')
            with self.assertRaisesRegex(ValueError, '第 2 行'):
                p.read_records(path)


class RenderingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.records = self.dir/'records.jsonl'
        self.records.write_text('\n'.join(json.dumps(x, ensure_ascii=False) for x in [row(), row('session_end', '16:00:00')]), encoding='utf-8')
        self.data = p.make_input(self.records, '2026-10-31')

    def tearDown(self):
        self.tmp.cleanup()

    def test_facts_and_stale_source_rejected(self):
        bad = copy.deepcopy(self.data)
        bad['facts']['today_kg'] += 999
        with self.assertRaisesRegex(ValueError, 'facts'):
            p.validate_input(bad)
        self.records.write_text(self.records.read_text()+'\n{}')
        with self.assertRaisesRegex(ValueError, '已有变化'):
            p.validate_input(self.data)

    def test_model_copy_and_choices_validated(self):
        bad = copy.deepcopy(self.data)
        bad['copy']['stickers']['today'] = '../../secret'
        with self.assertRaisesRegex(ValueError, '表情编号'):
            p.validate_input(bad)
        bad = copy.deepcopy(self.data)
        bad['copy']['stickers']['today'] = 'remaster_meal'
        with self.assertRaisesRegex(ValueError, '语义不符'):
            p.validate_input(bad)
        bad = copy.deepcopy(self.data)
        bad['copy']['highlight_exercises'] = ['试图只列一个动作']
        with self.assertRaisesRegex(ValueError, '未知 copy'):
            p.validate_input(bad)

    def test_render_watermark_cta_stickers_determinism_and_tamper(self):
        # At maximum allowed copy lengths, typography must fit without clipping.
        self.data['copy']['title'] = '今天认真训练每个动作全都安排上了'
        self.data['copy']['tags'] = '肩 · 背 · 胸 · 三头 · 臀 · 腿 · 二头 · 核心'
        first, second = self.dir/'one.png', self.dir/'two.png'
        a = p.render(self.data, first)
        p.render(self.data, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertTrue(p.check(first)['ok'])
        self.assertEqual(a['watermark']['text'], '捞鱼')
        self.assertEqual(len(a['stickers']), 7)
        self.assertIn('回复“健身”', a['cta'])
        self.assertNotIn('我健身', a['cta'])
        first.write_bytes(first.read_bytes()+b'tampered')
        with self.assertRaises(ValueError):
            p.check(first)

    def test_tiny_comparisons_not_zero_and_long_sets_are_summarized(self):
        self.assertIn('＜ 0.1', p.comparison(40, p.Decimal(2000), '小汽车'))
        self.assertIn('0.1', p.comparison(100, p.Decimal(2000), '小汽车'))
        self.assertIn('组', p.set_detail([{**row(), 'reps': i} for i in range(1, 20)]))

    def test_complete_grouped_list_expands_and_covers_every_set(self):
        rows = [{**row(), 'exercise': '动作'+str(i), 'muscleGroup': ['back', 'shoulders', 'chest', 'glutes', 'triceps'][i%5], 'reps': i+1} for i in range(17)]
        rows.extend([{**row(), 'exercise': '动作0', 'reps': 5}, {**row(), 'exercise': '动作0', 'reps': 8}])
        self.records.write_text('\n'.join(json.dumps(r) for r in rows))
        value = p.make_input(self.records, '2026-10-31')
        a = p.render(value, self.dir/'all.png')
        self.assertEqual(a['coverage']['sets'], 19)
        self.assertEqual(a['coverage']['exercises'], 17)
        self.assertEqual(a['coverage']['body_parts'], 5)
        self.assertGreater(a['size'][1], 2160)
        drawn = [x['text'] for x in a['text_layout']]
        for i in range(17):
            self.assertIn('动作'+str(i), drawn)
        self.assertTrue(p.check(self.dir/'all.png')['ok'])

    def test_long_set_details_preserve_all_sets_without_truncation(self):
        items = [{**row(), 'reps': i} for i in range(1, 21)]
        self.records.write_text('\n'.join(json.dumps(r) for r in items))
        value = p.make_input(self.records, '2026-10-31')
        a = p.render(value, self.dir/'many.png')
        text = a['body_groups'][0]['items'][0]['detail']
        for i in range(1, 21):
            self.assertIn(f'× {i}次', text)
        self.assertEqual(a['coverage']['sets'], 20)
        self.assertNotIn('…', text)

    def test_remastered_defaults_and_legacy_require_explicit_reason(self):
        for role, key in self.data['copy']['stickers'].items():
            self.assertTrue(p.catalog()[key]['remastered'])
            self.assertIn(p.ROLE_CONTEXTS[role], p.catalog()[key]['contexts'])



if __name__ == '__main__':
    unittest.main()
