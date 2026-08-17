"""xhs_core 纯逻辑层单元测试。运行: python3 -m unittest test_xhs_core -v"""
import unittest

from xhs_core import stable_id, parse_notification_text, is_spam, load_persona, fill_template


class TestStableId(unittest.TestCase):
    def test_deterministic(self):
        a = stable_id("用户A", "好看!")
        b = stable_id("用户A", "好看!")
        c = stable_id("用户B", "好看!")
        self.assertEqual(a, b, "同输入必须同ID(开源版hash()跨进程失配的坑)")
        self.assertNotEqual(a, c, "不同用户必须不同ID")
        self.assertEqual(len(a), 32, "md5十六进制长度32")

    def test_ignores_tail_beyond_200(self):
        self.assertEqual(stable_id("u", "x" * 300), stable_id("u", "x" * 250),
                         "超200字符尾部差异不影响ID")


class TestParseNotification(unittest.TestCase):
    def test_normal_comment(self):
        r = parse_notification_text("小明\n评论了你的笔记\n这个教程太有用了,求IDE配置\n2026-08-17")
        self.assertIsNotNone(r)
        self.assertEqual(r["username"], "小明")
        self.assertIn("这个教程太有用了", r["comment"])

    def test_skip_others_reply(self):
        # 「回复了你的评论」+「作者」= 别人回复我,不是新评论
        self.assertIsNone(parse_notification_text("小红\n回复了你的评论\n作者说得对\n2026-08-17"))

    def test_too_few_lines(self):
        self.assertIsNone(parse_notification_text("只有一行"))
        self.assertIsNone(parse_notification_text(""))

    def test_action_line_skipped(self):
        # 动作行("赞了你的图片")不应混入评论正文
        r = parse_notification_text("小明\n赞了你的图片\n期待更新\n2026-08-17")
        self.assertIsNotNone(r)
        self.assertIn("期待更新", r["comment"])
        self.assertNotIn("赞了你的图片", r["comment"])


class TestSpamAndPersona(unittest.TestCase):
    def setUp(self):
        self.p = load_persona()

    def test_spam_rules(self):
        self.assertTrue(is_spam("好", self.p), "超短文本")
        self.assertTrue(is_spam("666", self.p), "纯数字")
        self.assertTrue(is_spam("该评论已删除", self.p))
        self.assertTrue(is_spam("加我交流群", self.p), "引流词命中")
        self.assertFalse(is_spam("这篇写得真好,请问用什么IDE配置的?", self.p), "正常评论")

    def test_fill_template(self):
        out = fill_template(self.p["replyTemplates"]["fallbackShort"], self.p)
        self.assertIn(self.p["identity"]["emoji"], out)
        self.assertIn(self.p["identity"]["signature"], out)

    def test_persona_complete(self):
        for key in ["identity", "accountProfile", "spamKeywords", "maliciousKeywords",
                    "replyTemplates", "systemPromptTemplate"]:
            self.assertIn(key, self.p, f"persona 缺字段 {key}")
        for key in ["name", "persona", "signature", "emoji"]:
            self.assertIn(key, self.p["identity"], f"identity 缺字段 {key}")



class TestParseRealWorld(unittest.TestCase):
    """dry-run 实测发现的解析问题:innerText 混入时间/动作/按钮文本。"""

    def test_strips_time_lines(self):
        r = parse_notification_text("ATRI\n评论了你的笔记4小时前\n和府捞面是人类吗\n回复")
        self.assertIsNotNone(r)
        self.assertEqual(r["username"], "ATRI")
        self.assertNotIn("评论了你的笔记", r["comment"], "动作+时间行必须剥离")
        self.assertNotIn("4小时前", r["comment"], "时间必须剥离")
        self.assertNotIn("回复", r["comment"], "尾部按钮文本必须剥离")
        self.assertIn("和府捞面是人类吗", r["comment"])

    def test_strips_yesterday_and_date(self):
        r = parse_notification_text("牛肉饭里有香菜\n评论了你的笔记昨天 21:34\n？？？怎么p1一大半听都没听过\n回复")
        self.assertIsNotNone(r)
        self.assertIn("？？？怎么p1", r["comment"])
        self.assertNotIn("昨天", r["comment"])

    def test_strips_pure_date_line(self):
        r = parse_notification_text("Sara\n评论了你的笔记06-16\n要排队了\n回复")
        self.assertIsNotNone(r)
        self.assertIn("要排队了", r["comment"])
        self.assertNotIn("06-16", r["comment"])



class TestFormatReply(unittest.TestCase):
    """固定格式:🦞开头 + ——来自周五涵(小龙虾自动回复) 结尾,代码强制包装。"""

    def setUp(self):
        from xhs_core import format_reply
        self.fmt = format_reply
        self.p = load_persona()

    def test_wraps_plain_text(self):
        out = self.fmt("这个教程很有用", self.p)
        self.assertTrue(out.startswith("🦞"), "必须🦞开头")
        self.assertIn("这个教程很有用", out)
        self.assertTrue(out.rstrip().endswith(self.p["identity"]["signature"]), "必须固定签名结尾")

    def test_strips_llm_added_prefix(self):
        # LLM 可能自己加 emoji 前缀,包装时去重
        out = self.fmt("🦞 哈哈谢谢支持", self.p)
        self.assertFalse(out.startswith("🦞🦞"), "不得出现双emoji")

    def test_strips_llm_added_signature(self):
        out = self.fmt("谢谢!\n\n——来自周五涵", self.p)
        self.assertEqual(out.count("——来自"), 1, "签名只出现一次")



class TestBatchReply(unittest.TestCase):
    """打包调用:一个 prompt 生成 N 条回复,JSON 对应 id。"""

    def setUp(self):
        from xhs_core import build_batch_prompt, parse_batch_response
        self.build = build_batch_prompt
        self.parse = parse_batch_response
        self.p = load_persona()
        self.items = [
            {"id": "aaa", "username": "张三", "comment": "求IDE配置", "note_context": "编程笔记"},
            {"id": "bbb", "username": "李四", "comment": "太有用了", "note_context": "健身笔记"},
        ]

    def test_prompt_contains_all_ids_and_comments(self):
        s = self.build(self.p, self.items)
        for kw in ["aaa", "bbb", "求IDE配置", "太有用了", "JSON"]:
            self.assertIn(kw, s, f"打包prompt缺 {kw}")
        self.assertEqual(s.count("像朋友聊天"), 1, "回复规则块只出现一次(摊薄固定成本)")

    def test_parse_plain_json(self):
        out = self.parse('{"aaa": "回复1", "bbb": "回复2"}', self.items)
        self.assertEqual(out, {"aaa": "回复1", "bbb": "回复2"})

    def test_parse_fenced_json(self):
        out = self.parse('```json\n{"aaa": "回复1", "bbb": "回复2"}\n```', self.items)
        self.assertEqual(len(out), 2)

    def test_parse_broken_returns_empty(self):
        self.assertEqual(self.parse('乱码不是JSON{{{', self.items), {})

    def test_parse_partial(self):
        out = self.parse('{"aaa": "只有一条"}', self.items)
        self.assertEqual(out, {"aaa": "只有一条"}, "缺的条目不出现,由调用方兜底")


if __name__ == "__main__":
    unittest.main()
