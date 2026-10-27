import copy,hashlib,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from series_state import day_number,metric_value,prepare

class SeriesTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        cover=b'\x89PNG\r\n\x1a\nsynthetic-test';(self.root/'cover.png').write_bytes(cover)
        self.profile={'epochDate':'2026-10-19','timezone':'Asia/Shanghai','episodes':[{'itemId':'100','title':'合成上期','workflow':'software-video-production','published':True,'publishedAt':'2026-10-26T12:00:00+08:00'},{'itemId':'200','title':'无关新作品','workflow':'other','published':True,'publishedAt':'2026-10-27T12:00:00+08:00'}]}
        self.snapshot={'itemId':'100','sourceUrl':'https://creator.douyin.com/creator-micro/work-management/work-detail/100','snapshotAt':'2026-10-27T10:00:00Z','approved':True,'period':'cumulative','coverPath':'cover.png','coverSha256':hashlib.sha256(cover).hexdigest(),'coverApproved':True,'metrics':{'followers':{'sourceLabel':'涨粉量','raw':'0'}}}
    def tearDown(self):self.tmp.cleanup()
    def build(self):return prepare(self.profile,self.snapshot,'2026-10-27',self.root)
    def test_inclusive_calendar(self):
        self.assertEqual(day_number('2026-10-19','2026-10-27'),9)
        with self.assertRaises(ValueError):day_number('2026-10-19','2026-10-18')
    def test_exact_and_rounded_display(self):
        self.assertEqual(metric_value('1,234')['value'],1234);self.assertTrue(metric_value('1.2万')['approximate'])
        for v in ['未知','--','1,23','-2','']: 
            with self.assertRaises(ValueError):metric_value(v)
    def test_unrelated_latest_and_unpublished_are_excluded(self):
        self.profile['episodes'].append({'itemId':'300','workflow':'software-video-production','published':False})
        self.assertEqual(self.build()['previous']['itemId'],'100')
        self.assertEqual(self.build()['visualStyle'],'cupertino')
        self.profile['visualStyle']='fluent';self.assertEqual(self.build()['visualStyle'],'fluent')
    def test_mismatched_snapshot_fails(self):
        self.snapshot['itemId']='200'
        with self.assertRaisesRegex(ValueError,'latest'):self.build()
    def test_work_followers_not_account_net_growth(self):
        self.snapshot['metrics']['followers']['sourceLabel']='净增粉丝'
        with self.assertRaisesRegex(ValueError,'label'):self.build()
    def test_missing_metrics_are_omitted_zero_is_preserved(self):
        metrics=self.build()['previous']['metrics'];self.assertEqual(set(metrics),{'followers'});self.assertEqual(metrics['followers']['value'],0)
    def test_cover_hash_and_approval_are_enforced(self):
        self.snapshot['coverSha256']='bad'
        with self.assertRaisesRegex(ValueError,'hash'):self.build()
    def test_wrong_period_and_early_snapshot_fail(self):
        self.snapshot['period']='last7days'
        with self.assertRaises(ValueError):self.build()
        self.snapshot['period']='cumulative';self.snapshot['snapshotAt']='2020-01-01T00:00:00Z'
        with self.assertRaises(ValueError):self.build()

if __name__=='__main__':unittest.main()
