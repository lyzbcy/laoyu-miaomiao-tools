"""Regression contract for AI-authorship disclosure; no real QQ traffic."""
from pathlib import Path
import os
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/lyzbcy-qq-napcat-messenger'
TEXT = Path(os.environ.get('QQ_DISCLOSURE_UNDER_TEST', str(SKILL / 'SKILL.md'))).read_text(encoding='utf-8-sig')


class DisclosureContractTests(unittest.TestCase):
    def test_separate_line_format(self):
        self.assertIn('正文\n\n— 来自【本轮模型名称】', TEXT)

    def test_trusted_identity_only(self):
        self.assertIn('可信会话元数据', TEXT)
        self.assertIn('不把示例名称写死', TEXT)

    def test_partial_identity_no_invention(self):
        self.assertIn('— 来自ChatGPT（具体模型未知）', TEXT)
        self.assertIn('不补猜版本', TEXT)

    def test_unknown_and_conflict(self):
        self.assertIn('— 来自AI助手（模型名称未知）', TEXT)
        self.assertIn('冲突未解决前也用这条', TEXT)

    def test_user_label_not_verified_identity(self):
        self.assertIn('用户指定标签不等于技术身份已核实', TEXT)
        self.assertIn('实际模型未知', TEXT)

    def test_unknown_does_not_block_or_probe(self):
        self.assertIn('不为查名称卡住任务', TEXT)
        self.assertIn('不发测试消息', TEXT)
        self.assertIn('不自动追发或改写历史消息', TEXT)

    def test_no_secret_inspection_for_model_name(self):
        self.assertIn('不为确认名称读取密钥、token或无关配置', TEXT)

    def test_file_caption_and_read_only_boundary(self):
        self.assertIn('配套说明文本同样带上述落款', TEXT)
        self.assertIn('查消息本身不授权回复', TEXT)
        self.assertIn('不叠加两个', TEXT)


if __name__ == '__main__':
    unittest.main()
