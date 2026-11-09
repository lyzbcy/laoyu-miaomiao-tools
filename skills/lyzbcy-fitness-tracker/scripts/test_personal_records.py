import unittest
from personal_records import summaries

DATE = '2026-01-05'

def row(day, name, weight, reps, **fields):
    return {'date': day, 'exercise': name, 'weight': weight, 'reps': reps, **fields}

class PosterPRTest(unittest.TestCase):
    def check_pr(self, today, history):
        return summaries(today, history + today, DATE)

    def test_self_weight_new_and_tie_with_earliest_date(self):
        name = '自重引体向上'
        history = [row('2026-01-02', name, 0, 4), row('2026-01-01', name, 0, 4)]
        new = self.check_pr([row(DATE, name, 0, 5)], history)
        self.assertEqual(new[name], [{'lane': 'bodyweight', 'new': True, 'detail': '自重 × 5次', 'date': DATE}])
        tied = self.check_pr([row(DATE, name, 0, 4)], history)
        self.assertEqual(tied[name], [{'lane': 'bodyweight', 'new': False, 'detail': '自重 × 4次', 'date': '2026-01-01'}])

    def test_raw_plates_across_spelling_and_estimates_but_not_machines(self):
        name = '双头绳绳索面拉'
        fields = {'equipment': 'A', 'reportedUnit': 'plate', 'reportedWeight': 4.5, 'weightEstimated': True}
        history = [row('2026-01-02', '双头绳面拉', 36, 12, **fields),
                   row('2026-01-03', name, 100, 50, **{**fields, 'equipment': 'B'})]
        result = self.check_pr([row(DATE, name, 18, 13, **{**fields, 'reportedWeight': 5})], history)
        self.assertEqual(result[name][0]['detail'], '5片 × 13次')
        self.assertTrue(result[name][0]['new'])

    def test_dumbbell_uses_heaviest_dated_per_hand_record(self):
        name = '哑铃飞鸟'
        today = row(DATE, name, 13.6077711, 10, reportedUnit='lb', reportedWeight=30, note='左右各15lb')
        history = [row('2026-01-01', name, 16, 14, note='单边8kg×14'),
                   row('2026-01-02', name, 16, 11, note='35lb单只')]
        self.assertEqual(self.check_pr([today], history)[name],
                         [{'lane': 'regular', 'new': False, 'detail': '每手 35 lb × 11次', 'date': '2026-01-02'}])

    def test_heavier_group_wins_and_future_never_sets_baseline(self):
        name = '卧推'
        history = [row('2026-01-02', name, 60, 12), row('2026-01-06', name, 90, 15)]
        result = self.check_pr([row(DATE, name, 65, 10)], history)
        self.assertEqual(result[name], [{'lane': 'regular', 'new': True, 'detail': '65 kg × 10次', 'date': DATE}])
        self.assertFalse(self.check_pr([row(DATE, name, 65, 10)], history[1:])[name][0]['new'])

    def test_standard_bodyweight_alias_keeps_higher_historical_record(self):
        name = '自重引体向上'
        history = [row('2026-01-01', '引体向上', 0, 6, note='自重全程'),
                   row('2025-12-29', '引体向上', 0, 10, note='辅助20kg'),
                   row('2026-01-03', '引体向上', 0, 11, note='窄距自重')]
        result = self.check_pr([row(DATE, name, 0, 5)], history)
        self.assertEqual(result[name], [{'lane': 'bodyweight', 'new': False, 'detail': '自重 × 6次', 'date': '2026-01-01'}])

    def test_high_reps_do_not_block_heavier_load_and_stop_counting_at_twelve(self):
        name = '哑铃侧平举'
        history = [row('2026-01-01', name, 2.5, 100, note='每手2.5kg'),
                   row('2026-01-02', name, 5, 12, note='每手5kg')]
        self.assertTrue(self.check_pr([row(DATE, name, 6, 8, note='每手6kg')], history)[name][0]['new'])
        same = self.check_pr([row(DATE, name, 5, 20, note='每手5kg')], history)
        self.assertEqual(same[name], [{'lane': 'regular', 'new': False, 'detail': '每手 5 kg × 12次', 'date': '2026-01-02'}])

    def test_parallel_records_do_not_replace_each_other(self):
        name = '卧推'
        history = [row('2026-01-01', name, 70, 7), row('2026-01-02', name, 95, 2)]
        records = self.check_pr([row(DATE, name, 100, 1)], history)[name]
        self.assertEqual(records, [
            {'lane': 'regular', 'new': False, 'detail': '70 kg × 7次', 'date': '2026-01-01'},
            {'lane': 'limit', 'new': True, 'detail': '100 kg × 1次', 'date': DATE},
        ])

    def test_six_reps_boundary_and_first_lane(self):
        name = '卧推'
        history = [row('2026-01-01', name, 70, 7)]
        records = self.check_pr([row(DATE, name, 75, 6), row(DATE, name, 100, 5.5)], history)[name]
        self.assertEqual(records, [
            {'lane': 'regular', 'new': True, 'detail': '75 kg × 6次', 'date': DATE},
            {'lane': 'limit', 'new': False, 'detail': '100 kg × 5.5次', 'date': DATE},
        ])
