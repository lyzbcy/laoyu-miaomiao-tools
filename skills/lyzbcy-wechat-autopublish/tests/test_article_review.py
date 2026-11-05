import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('article_review', Path(__file__).parents[1] / 'scripts/article_review.py')
m = importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class ArticleReviewTests(unittest.TestCase):
    def setUp(self):
        self.plan = {'account': '示例号', 'title': '示例文章', 'native_video_nonce': 'current', 'video_description': '本期说明'}
        self.observed = {'account': '示例号', 'rows': [{'title': '示例文章', 'status': '已发表', 'url': 'https://mp.weixin.qq.com/s/example'}],
                         'article': {'account': '示例号', 'title': '示例文章', 'url': 'https://mp.weixin.qq.com/s/example', 'videos': [{'nonce': 'current', 'description': '本期说明'}]}}

    def test_verified_does_not_mean_public_when_under_review(self):
        self.observed['rows'][0]['status'] = '审核中'
        r = m.publication(self.observed, self.plan)
        self.assertEqual(r['status'], 'under_review');self.assertFalse(r['published'])

    def test_published_record_still_requires_public_readback(self):
        self.observed.pop('article')
        self.assertEqual(m.publication(self.observed, self.plan)['status'], 'pending')

    def test_same_title_old_video_rejected(self):
        self.observed['article']['videos'][0]['nonce'] = 'previous'
        self.assertEqual(m.publication(self.observed, self.plan)['reason'], 'current_video_identity_mismatch')

    def test_temporary_preview_is_not_permanent(self):
        self.observed['rows'][0]['url'] = 'https://mp.weixin.qq.com/s/example?tempkey=preview'
        self.assertEqual(m.publication(self.observed, self.plan)['reason'], 'permanent_url_missing')

    def test_duplicate_record_is_ambiguous(self):
        self.observed['rows'] *= 2
        self.assertEqual(m.publication(self.observed, self.plan)['reason'], 'current_record_not_unique')

    def test_current_article_and_video_match_without_claiming_playback(self):
        r = m.publication(self.observed, self.plan)
        self.assertTrue(r['published']);self.assertTrue(r['native_video_verified']);self.assertFalse(r['mobile_playback_verified'])

    def test_wrong_account_stops(self):
        self.observed['account'] = '另一个号'
        self.assertEqual(m.publication(self.observed, self.plan)['status'], 'blocked')

    def test_plain_text_does_not_pass_styled_layout_check(self):
        r = m.layout('<p>正文</p>', 2, 5)
        self.assertEqual(set(r['errors']), {'heading_structure_missing', 'inline_styles_missing'})

    def test_native_markup_count_is_structural_only(self):
        r = m.layout('<h2 style="color:#123">标题</h2><table><tr><td>结果</td></tr></table><mp-common-videosnap></mp-common-videosnap>', 1, 1)
        self.assertTrue(r['valid']);self.assertEqual(r['tables'], 1);self.assertEqual(r['native_videos'], 1)


if __name__ == '__main__':
    unittest.main()
