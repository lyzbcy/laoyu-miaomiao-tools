from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
class DeclarationRules(unittest.TestCase):
 def test_original_separate_from_ai(self):
  s=(R/'SKILL.md').read_text('utf-8');self.assertIn('原创声明不等于 AI 内容声明',s);self.assertIn('保存重开',s)
 def test_channels_first_and_no_duplicate(self):
  s=(R/'references/expansion.md').read_text('utf-8');self.assertIn('公众号「视频号」入口',s);self.assertIn('禁止公众号另走「本地上传」',s);self.assertIn('唯一动态标识',s)
 def test_per_article_mass_send(self):
  s=(R/'SKILL.md').read_text('utf-8');self.assertIn('公众号群发默认关闭',s);self.assertIn('本次群发授权不扩展',s);self.assertIn('较新的明确授权覆盖',s)
 def test_no_fabricated_switch_or_repost(self):
  s=(R/'SKILL.md').read_text('utf-8');self.assertIn('当前入口未提供该控件',s);self.assertIn('不删除重发',s)
