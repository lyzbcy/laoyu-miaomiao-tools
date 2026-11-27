from pathlib import Path
import unittest,sys
from unittest.mock import Mock
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from publish import Publisher
from browser import UIError
class UploadReady(unittest.TestCase):
 def test_no_save_click_when_upload_still_pending(self):
  p=SimpleNamespace(p='douyin',j={},body=lambda:'上传过程中请不要删除/移动文件\n取消上传',b=Mock(),tap=Mock())
  p.b.wait.side_effect=UIError('timeout')
  result=Publisher.save(p)
  self.assertEqual(result['reason'],'upload_in_progress_before_save')
  p.tap.assert_not_called()
 def test_xiaohongshu_upload_not_saved_early(self):
  p=SimpleNamespace(p='xiaohongshu',j={},body=lambda:'上传中 28%\n取消上传',b=Mock(),tap=Mock())
  p.b.wait.side_effect=UIError('timeout')
  self.assertEqual(Publisher.save(p)['reason'],'upload_in_progress_before_save')
  p.b.semantic.assert_not_called()
 def test_xiaohongshu_empty_draft_not_saved(self):
  p=SimpleNamespace(p='xiaohongshu',j={},body=lambda:'暂未上传视频',b=Mock(),tap=Mock())
  with self.assertRaisesRegex(UIError,'xiaohongshu_video_missing_before_save'):Publisher.save(p)
  p.b.semantic.assert_not_called()
 def test_ready_page_saves(self):
  p=SimpleNamespace(p='douyin',j={},body=lambda:'预览视频\n暂存离开',b=Mock(),tap=Mock())
  p.b.wait.return_value={'url':'draft','text':'继续编辑'}
  self.assertEqual(Publisher.save(p)['text'],'继续编辑')
  p.tap.assert_called_once_with('暂存离开')
if __name__=='__main__':unittest.main()
