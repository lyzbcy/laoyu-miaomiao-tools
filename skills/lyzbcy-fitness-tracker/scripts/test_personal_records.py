import unittest
from personal_records import summaries

DATE = '2026-01-05'

def row(day, name, weight, reps, **fields):
    return {'date': day, 'exercise': name, 'weight': weight, 'reps': reps, **fields}

class PosterPRTest(unittest.TestCase):
    def check_pr(self, today, history, config=None):
        return summaries(today, history + today, DATE, config)

    def test_self_weight_new_and_tie_with_earliest_date(self):
        name = '自重引体向上'
        history = [row('2026-01-02', name, 0, 4), row('2026-01-01', name, 0, 4)]
        new = self.check_pr([row(DATE, name, 0, 5)], history)
        self.assertEqual(new[name], {'new': True, 'detail': '自重 × 5次', 'date': DATE})
        tied = self.check_pr([row(DATE, name, 0, 4)], history)
        self.assertEqual(tied[name], {'new': False, 'detail': '自重 × 4次', 'date': '2026-01-01'})

    def test_raw_plates_across_spelling_and_estimates_but_not_machines(self):
        name = '双头绳绳索面拉'
        fields = {'equipment': 'A', 'reportedUnit': 'plate', 'reportedWeight': 4.5, 'weightEstimated': True}
        history = [row('2026-01-02', '双头绳面拉', 36, 12, **fields),
                   row('2026-01-03', name, 100, 50, **{**fields, 'equipment': 'B'})]
        result = self.check_pr([row(DATE, name, 18, 13, **fields)], history)
        self.assertEqual(result[name]['detail'], '4.5片 × 13次')
        self.assertTrue(result[name]['new'])

    def test_historical_dumbbell_config_uses_dated_set_and_per_hand(self):
        name = '哑铃飞鸟'
        today = row(DATE, name, 13.6077711, 10, reportedUnit='lb', reportedWeight=30, note='左右各15lb')
        history = [row('2026-01-01', name, 16, 14, note='单边8kg×14'),
                   row('2026-01-02', name, 16, 11, note='35lb单只')]
        config = {'chest': {name: {'weight': 16, 'reps': 14}}}
        self.assertEqual(self.check_pr([today], history, config)[name],
                         {'new': False, 'detail': '每手 8 kg × 14次', 'date': '2026-01-01'})

    def test_tradeoff_future_and_unverified_baseline_never_claim_pr(self):
        name = '卧推'
        history = [row('2026-01-02', name, 60, 12), row('2026-01-06', name, 90, 15)]
        result = self.check_pr([row(DATE, name, 65, 10)], history)
        self.assertEqual(result[name], {'new': False, 'detail': '60 kg × 12次', 'date': '2026-01-02'})
        self.assertFalse(self.check_pr([row(DATE, name, 65, 10)], history[1:]))

    def test_standard_bodyweight_alias_keeps_higher_historical_record(self):
        name = '自重引体向上'
        history = [row('2026-01-01', '引体向上', 0, 6, note='自重全程'),
                   row('2025-12-29', '引体向上', 0, 10, note='辅助20kg'),
                   row('2026-01-03', '引体向上', 0, 11, note='窄距自重')]
        result = self.check_pr([row(DATE, name, 0, 5)], history)
        self.assertEqual(result[name], {'new': False, 'detail': '自重 × 6次', 'date': '2026-01-01'})
