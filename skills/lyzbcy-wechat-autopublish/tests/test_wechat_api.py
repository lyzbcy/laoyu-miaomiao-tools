#!/usr/bin/env python3
"""wechat_api.py 的测试套件（单元 + 集成，全部指向本地 fake server，不触网）。

运行：python3 tests/test_wechat_api.py
"""
import base64
import json
import os
import re
import sys
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

import wechat_api  # noqa: E402

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
TINY_PNG = PNG_MAGIC + b"\x00\x00\x00\rIHDR" + b"\x00" * 8  # 伪 PNG，够测魔数即可（正文图用）


def _make_cover_png(w=900, h=383):
    """假封面：IHDR 头是 900x383（image_size 只读头），数据乱填——fake server 不解析。"""
    import zlib, struct

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))
    return (PNG_MAGIC
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\x01\x02" * 64))
            + chunk(b"IEND", b""))


COVER_PNG = _make_cover_png()


# ---------------------------------------------------------------------------
# 可编程 fake 微信 API 服务器
# ---------------------------------------------------------------------------
class FakeAPI:
    """记录请求、按路径弹出预设响应；支持同路径多次不同响应（测 token 重试）。"""

    def __init__(self):
        self.requests = []            # [(path, query, body_bytes), ...]
        self.responses = {}           # path -> [resp_dict, ...] 依次弹出
        self.files = {}               # path -> (bytes, content_type) 用于假外链图
        self.lock = threading.Lock()

    def expect(self, path, *responses):
        self.responses[path] = list(responses)

    def pop_response(self, path):
        with self.lock:
            queue = self.responses.get(path)
            if not queue:
                return {"errcode": -99, "errmsg": "unexpected path: %s" % path}
            resp = queue.pop(0)
            if queue == []:
                self.responses.pop(path, None)
            return resp

    def record(self, path, query, body):
        with self.lock:
            self.requests.append((path, query, body))


def make_handler(fake):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # 静音
            pass

        def _read_body(self):
            length = int(self.headers.get("Content-Length") or 0)
            return self.rfile.read(length) if length else b""

        def _serve_file(self, path):
            data, ctype = fake.files[path]
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            from urllib.parse import urlparse
            parsed = urlparse(self.path)
            path, query = parsed.path, parsed.query
            fake.record(path, query, b"")
            if path in fake.files:
                return self._serve_file(path)
            body = json.dumps(fake.pop_response(path)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            from urllib.parse import urlparse
            parsed = urlparse(self.path)
            path, query = parsed.path, parsed.query
            body = self._read_body()
            fake.record(path, query, body)
            if path in fake.files:
                return self._serve_file(path)
            resp = fake.pop_response(path)
            body_out = json.dumps(resp).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body_out)))
            self.end_headers()
            self.wfile.write(body_out)

    return Handler


class FakeServerTestCase(unittest.TestCase):
    """所有需要 fake server 的测试的基类。"""

    @classmethod
    def setUpClass(cls):
        cls.fake = FakeAPI()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.fake))
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls._old_base = os.environ.get("WECHAT_API_BASE")
        os.environ["WECHAT_API_BASE"] = cls.base

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        if cls._old_base is None:
            os.environ.pop("WECHAT_API_BASE", None)
        else:
            os.environ["WECHAT_API_BASE"] = cls._old_base

    def setUp(self):
        self.fake.requests.clear()
        self.fake.responses.clear()
        self.fake.files.clear()

    # -- 便捷构造 -----------------------------------------------------------
    CFG = {
        "appid": "wx1234",
        "secret": "super-secret",
    }

    def cfg(self, **extra):
        c = dict(self.CFG)
        c.update(extra)
        return c


# ---------------------------------------------------------------------------
# 配置 / 文章校验
# ---------------------------------------------------------------------------
class TestArticleValidation(unittest.TestCase):
    def article(self, **override):
        a = {
            "title": "本周 AI 学习周报",
            "digest": "一句话摘要",
            "content_html": "<p>hello</p>",
            "thumb_image": "cover.jpg",
        }
        a.update(override)
        return {k: v for k, v in a.items() if v is not None}

    def test_valid_article_passes(self):
        art = wechat_api.validate_article(self.article())
        self.assertEqual(art["title"], "本周 AI 学习周报")

    def test_title_over_32_chars_rejected(self):
        with self.assertRaises(wechat_api.ArticleError) as ctx:
            wechat_api.validate_article(self.article(title="标" * 33))
        self.assertIn("32", str(ctx.exception))

    def test_title_exactly_32_ok(self):
        wechat_api.validate_article(self.article(title="标" * 32))

    def test_missing_title_rejected(self):
        with self.assertRaises(wechat_api.ArticleError):
            wechat_api.validate_article(self.article(title=None))

    def test_digest_over_120_rejected(self):
        with self.assertRaises(wechat_api.ArticleError):
            wechat_api.validate_article(self.article(digest="摘" * 121))

    def test_author_over_16_rejected(self):
        with self.assertRaises(wechat_api.ArticleError):
            wechat_api.validate_article(self.article(author="作" * 17))

    def test_content_over_20k_chars_rejected(self):
        with self.assertRaises(wechat_api.ArticleError):
            wechat_api.validate_article(self.article(content_html="<p>" + "x" * 20001 + "</p>"))

    def test_content_html_file_loaded(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write("<p>from file</p>")
            path = f.name
        try:
            art = wechat_api.validate_article(
                self.article(content_html=None, content_html_file=path)
            )
            self.assertEqual(art["content_html"], "<p>from file</p>")
        finally:
            os.unlink(path)

    def test_newspic_requires_image_list(self):
        with self.assertRaises(wechat_api.ArticleError):
            wechat_api.validate_article(
                self.article(article_type="newspic", thumb_image=None)
            )


class TestConfigValidation(unittest.TestCase):
    def test_missing_appid_rejected(self):
        with self.assertRaises(wechat_api.ConfigError):
            wechat_api.load_config_dict({"secret": "x"})

    def test_missing_secret_rejected(self):
        with self.assertRaises(wechat_api.ConfigError):
            wechat_api.load_config_dict({"appid": "x"})


# ---------------------------------------------------------------------------
# 正文图片清洗
# ---------------------------------------------------------------------------
class TestCleanContentImages(unittest.TestCase):
    def test_external_image_replaced(self):
        seen = []

        def uploader(name, data, ctype):
            seen.append((name, data[:8], ctype))
            return "http://mmbiz.qpic.cn/abc123"

        def dl(url, timeout=30):
            return TINY_PNG, "image/png"

        html = '<p><img src="https://cdn.example.com/cat.png"></p>'
        out = wechat_api.clean_content_images(html, uploader, downloader=dl)
        self.assertEqual(out, '<p><img src="http://mmbiz.qpic.cn/abc123"></p>')
        self.assertEqual(seen[0][1], PNG_MAGIC)
        self.assertEqual(seen[0][2], "image/png")

    def test_mmbiz_image_skipped(self):
        called = []

        def uploader(*a):
            called.append(a)
            raise AssertionError("mmbiz 图不应再上传")

        html = '<img src="https://mmbiz.qpic.cn/already-there">'
        out = wechat_api.clean_content_images(html, uploader)
        self.assertEqual(out, html)
        self.assertEqual(called, [])

    def test_data_uri_uploaded(self):
        payload = base64.b64encode(TINY_PNG).decode()

        def uploader(name, data, ctype):
            return "http://mmbiz.qpic.cn/from-data"

        out = wechat_api.clean_content_images(
            '<img src="data:image/png;base64,%s">' % payload, uploader
        )
        self.assertEqual(out, '<img src="http://mmbiz.qpic.cn/from-data">')

    def test_oversized_image_rejected_with_hint(self):
        big = b"\x89PNG\r\n\x1a\n" + b"\x00" * (1024 * 1024 + 1)

        def dl(url, timeout=30):
            return big, "image/png"

        html = '<img src="https://cdn.example.com/huge.png">'
        with self.assertRaises(wechat_api.ContentImageError) as ctx:
            wechat_api.clean_content_images(
                html, lambda *a: "", downloader=dl
            )
        self.assertIn("压缩", str(ctx.exception))

    def test_non_jpg_png_rejected(self):
        def dl(url, timeout=30):
            return b"GIF89a" + b"\x00" * 10, "image/gif"

        with self.assertRaises(wechat_api.ContentImageError):
            wechat_api.clean_content_images(
                '<img src="https://x.com/a.gif">',
                lambda *a: "",
                downloader=dl,
            )


# ---------------------------------------------------------------------------
# 错误码提示
# ---------------------------------------------------------------------------
class TestErrorHints(unittest.TestCase):
    def test_40164_ip_whitelist(self):
        hint = wechat_api.errcode_hint(40164)
        self.assertIn("IP 白名单", hint)

    def test_53402_cover_crop(self):
        # 2026-08-14 真机实测：1x1 封面导致 draft/add 报 53402 封面裁剪失败
        hint = wechat_api.errcode_hint(53402)
        self.assertIn("封面", hint)

    def test_40001_secret_or_token(self):
        hint = wechat_api.errcode_hint(40001)
        self.assertIn("AppSecret", hint)

    def test_40013_invalid_appid(self):
        # 2026-08-14 真机实测：stable_token 传错 appid 返回 40013 invalid appid
        hint = wechat_api.errcode_hint(40013)
        self.assertIn("appid", hint.lower())

    def test_48001_no_permission(self):
        hint = wechat_api.errcode_hint(48001)
        self.assertIn("认证", hint)

    def test_unknown_code_has_generic(self):
        hint = wechat_api.errcode_hint(99999)
        self.assertTrue(len(hint) > 0)


class TestCoverSizeCheck(unittest.TestCase):
    """2026-08-14 真机实测教训：过小封面会让 draft/add 报 53402，必须提前拦截。"""

    def _png(self, w, h):
        import zlib, struct

        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))
        return (b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(b"\x00\x01\x02" * (w * h)))
                + chunk(b"IEND", b""))

    def test_image_size_reads_png(self):
        self.assertEqual(wechat_api.image_size(self._png(900, 383)), (900, 383))

    def test_tiny_cover_rejected_before_upload(self):
        with self.assertRaises(wechat_api.ContentImageError) as ctx:
            wechat_api.check_cover_size(self._png(1, 1))
        self.assertIn("53402", str(ctx.exception))

    def test_proper_cover_passes(self):
        wechat_api.check_cover_size(self._png(900, 383))     # 不抛即通过

    def test_narrow_cover_rejected(self):
        with self.assertRaises(wechat_api.ContentImageError):
            wechat_api.check_cover_size(self._png(200, 100))


# ---------------------------------------------------------------------------
# 集成：全链路 publish（fake server）
# ---------------------------------------------------------------------------
class TestPublishFlow(FakeServerTestCase):
    def setUp(self):
        super().setUp()
        self.fake.files["/remote/cover.png"] = (TINY_PNG, "image/png")
        self.fake.expect(
            "/cgi-bin/stable_token",
            {"access_token": "TOKEN1", "expires_in": 7200},
        )
        self.fake.expect(
            "/cgi-bin/media/uploadimg",
            {"url": "http://mmbiz.qpic.cn/content-img", "errcode": 0},
        )
        self.fake.expect(
            "/cgi-bin/material/add_material",
            {"media_id": "THUMB_ID", "url": "http://mmbiz.qpic.cn/thumb"},
        )
        self.fake.expect(
            "/cgi-bin/draft/add",
            {"media_id": "DRAFT_ID"},
        )
        self.fake.expect(
            "/cgi-bin/freepublish/submit",
            {"errcode": 0, "errmsg": "ok", "publish_id": "PUB_1"},
        )
        self.fake.expect(
            "/cgi-bin/freepublish/get",
            {"errcode": 0, "publish_status": 0,
             "article_detail": {"count": 1,
                                 "item": [{"article_url": "https://mp.weixin.qq.com/s/final"}]}},
        )

    def article(self, tmpdir):
        cover = os.path.join(tmpdir, "cover.png")
        with open(cover, "wb") as f:
            f.write(COVER_PNG)
        return {
            "title": "本周 AI 学习周报",
            "digest": "摘要",
            "content_html": '<img src="%s/remote/cover.png">' % self.base,
            "thumb_image": cover,
        }

    def test_full_publish_flow(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = wechat_api.publish_article(
                self.cfg(), self.article(tmp), poll_seconds=0.01
            )
        self.assertEqual(result["publish_id"], "PUB_1")
        self.assertEqual(result["article_url"], "https://mp.weixin.qq.com/s/final")
        self.assertEqual(result["status"], "success")
        # 校验调用顺序（外链图下载 /remote/... 不算微信 API 调用）
        paths = [r[0] for r in self.fake.requests if r[0].startswith("/cgi-bin/")]
        self.assertEqual(paths, [
            "/cgi-bin/stable_token",
            "/cgi-bin/media/uploadimg",
            "/cgi-bin/material/add_material",
            "/cgi-bin/draft/add",
            "/cgi-bin/freepublish/submit",
            "/cgi-bin/freepublish/get",
        ])
        # draft/add 的 body 应包含 thumb_media_id 与清洗后的正文（按 path 取，跳过外链图下载）
        def bodies_of(path):
            return [r[2] for r in self.fake.requests if r[0] == path]

        draft_body = json.loads(bodies_of("/cgi-bin/draft/add")[0])
        self.assertEqual(draft_body["articles"][0]["thumb_media_id"], "THUMB_ID")
        self.assertIn("mmbiz.qpic.cn/content-img",
                      draft_body["articles"][0]["content"])
        # add_material 收到的应是 PNG 二进制（multipart）
        self.assertIn(PNG_MAGIC, bodies_of("/cgi-bin/material/add_material")[0])

    def test_publish_status_still_in_progress_then_success(self):
        # 第一次 get 返回发布中，第二次成功
        self.fake.expect(
            "/cgi-bin/freepublish/get",
            {"errcode": 0, "publish_status": 1},
            {"errcode": 0, "publish_status": 0,
             "article_detail": {"count": 1,
                                 "item": [{"article_url": "https://mp.weixin.qq.com/s/ok"}]}},
        )
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = wechat_api.publish_article(
                self.cfg(), self.article(tmp), poll_seconds=0.01, max_polls=5
            )
        self.assertEqual(result["status"], "success")

    def test_publish_failed_status_raises(self):
        self.fake.expect(
            "/cgi-bin/freepublish/get",
            {"errcode": 0, "publish_status": 3, "fail_idx": [0]},
        )
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(wechat_api.WeChatApiError) as ctx:
                wechat_api.publish_article(
                    self.cfg(), self.article(tmp), poll_seconds=0.01, max_polls=2
                )
        self.assertIn("3", str(ctx.exception))


class TestTokenRefreshRetry(FakeServerTestCase):
    def test_40001_then_retry_with_new_token(self):
        self.fake.expect(
            "/cgi-bin/stable_token",
            {"access_token": "TOKEN_OLD", "expires_in": 7200},
            {"access_token": "TOKEN_NEW", "expires_in": 7200},
        )
        self.fake.expect("/cgi-bin/draft/add", {"media_id": "DRAFT_ID"})
        states = {"n": 0}

        original = wechat_api._post_json

        def flaky_post(url, payload, timeout=30):
            if "/cgi-bin/draft/add" in url and states["n"] == 0:
                states["n"] += 1
                return {"errcode": 40001, "errmsg": "invalid credential"}
            return original(url, payload, timeout)

        wechat_api._post_json = flaky_post
        try:
            old_token = wechat_api.get_stable_token(self.cfg())
            self.assertEqual(old_token, "TOKEN_OLD")
            media_id = wechat_api.add_draft(self.cfg(), old_token, {
                "title": "t" * 5, "digest": "d",
                "content": "<p>x</p>", "thumb_media_id": "T1",
            })
        finally:
            wechat_api._post_json = original
        # 重试成功：拿到草稿 ID；stable_token 被调 2 次（初始+刷新）；
        # 第一次 draft/add 被 client 侧 mock 拦截（不触网），只有重试那次
        # 真正到达 server，且 query 带的是新 token
        self.assertEqual(media_id, "DRAFT_ID")
        self.assertEqual(states["n"], 1)
        token_calls = [r for r in self.fake.requests
                       if r[0] == "/cgi-bin/stable_token"]
        self.assertEqual(len(token_calls), 2)
        draft_calls = [r for r in self.fake.requests
                       if r[0] == "/cgi-bin/draft/add"]
        self.assertEqual(len(draft_calls), 1)
        self.assertIn("TOKEN_NEW", draft_calls[0][1])


class TestIpWhitelist(FakeServerTestCase):
    def test_40164_raises_with_hint(self):
        self.fake.expect(
            "/cgi-bin/stable_token",
            {"errcode": 40164, "errmsg": "invalid ip"},
        )
        with self.assertRaises(wechat_api.WeChatApiError) as ctx:
            wechat_api.get_stable_token(self.cfg())
        self.assertIn("IP 白名单", str(ctx.exception))


class TestDryRun(unittest.TestCase):
    def test_dry_run_makes_no_network_calls(self):
        # 把 API base 指向一个必然连不上的地址；dry-run 下不应产生任何请求
        os.environ["WECHAT_API_BASE"] = "http://127.0.0.1:1"
        try:
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                cover = os.path.join(tmp, "cover.png")
                with open(cover, "wb") as f:
                    f.write(COVER_PNG)
                article = {
                    "title": "干跑测试",
                    "digest": "d",
                    "content_html": "<p>正文，含 mmbiz.qpic.cn 图则无需上传</p>",
                    "thumb_image": cover,
                }
                plan = wechat_api.publish_article(
                    self.cfg(), article, dry_run=True
                )
            self.assertEqual(plan["status"], "dry-run")
            self.assertIn("steps", plan)
            joined = json.dumps(plan, ensure_ascii=False)
            self.assertIn("draft/add", joined)
            self.assertIn("freepublish/submit", joined)
        finally:
            os.environ.pop("WECHAT_API_BASE", None)

    def test_dry_run_warns_missing_cover(self):
        import tempfile, io, contextlib
        with tempfile.TemporaryDirectory() as tmp:
            article = {"title": "t", "digest": "d", "content_html": "<p>x</p>",
                       "thumb_image": os.path.join(tmp, "不存在.png")}
            warnings = []
            plan = wechat_api.publish_article(
                self.cfg(), article, dry_run=True,
                log=lambda m: warnings.append(m))
        self.assertTrue(any("不存在" in w for w in warnings))

    CFG = {"appid": "wx1234", "secret": "super-secret"}

    @classmethod
    def setUpClass(cls):
        pass

    def cfg(self, **extra):
        c = dict(self.CFG)
        c.update(extra)
        return c


# ---------------------------------------------------------------------------
# 复查修复点：懒加载占位图 / SSRF / 正则边界 / 状态轮询 / publish_method
# ---------------------------------------------------------------------------
class TestLazyPlaceholder(unittest.TestCase):
    def _uploader(self, calls):
        def uploader(name, data, ctype):
            calls.append(name)
            return "http://mmbiz.qpic.cn/" + name
        return uploader

    def test_gif_placeholder_with_data_original(self):
        payload = base64.b64encode(b"GIF89a" + b"\x00" * 16).decode()
        html = ('<img src="data:image/gif;base64,%s" '
                'data-original="https://cdn.example.com/real.jpg">'
                '<img src="https://cdn.example.com/plain.png">' % payload)
        calls = []
        dl_urls = []

        def dl(url, timeout=30):
            dl_urls.append(url)
            return TINY_PNG, "image/png"

        out = wechat_api.clean_content_images(
            html, self._uploader(calls), downloader=dl)
        # 占位 gif 被替换为 data-original 真实图；两个 http 图都被上传
        self.assertIn("mmbiz.qpic.cn/content-", out)
        self.assertNotIn("data:image/gif", out)
        self.assertEqual(sorted(dl_urls),
                         ["https://cdn.example.com/plain.png",
                          "https://cdn.example.com/real.jpg"])

    def test_unsupported_data_uri_without_fallback_skipped(self):
        payload = base64.b64encode(b"GIF89a" + b"\x00" * 16).decode()
        html = '<img src="data:image/gif;base64,%s">' % payload
        calls = []
        out = wechat_api.clean_content_images(
            html, self._uploader(calls),
            downloader=lambda *a: (_ for _ in ()).throw(AssertionError("不应下载")))
        self.assertEqual(out, html)          # 原样保留，不上传
        self.assertEqual(calls, [])

    def test_single_quote_src_supported(self):
        def dl(url, timeout=30):
            return TINY_PNG, "image/png"
        out = wechat_api.clean_content_images(
            "<img src='https://x.com/a.png'>", self._uploader([]), downloader=dl)
        self.assertIn("mmbiz.qpic.cn/content-", out)

    def test_data_src_attr_not_mistaken_as_src(self):
        # 只有 data-src、没有 src 的标签不应触发迁移
        html = '<img data-src="https://cdn.example.com/lazy.png">'
        out = wechat_api.clean_content_images(
            html, self._uploader([]),
            downloader=lambda *a: (_ for _ in ()).throw(AssertionError("不应下载")))
        self.assertEqual(out, html)


class TestSSRFProtection(unittest.TestCase):
    def test_metadata_ip_rejected(self):
        with self.assertRaises(wechat_api.ContentImageError) as ctx:
            wechat_api.default_downloader("http://169.254.169.254/latest/meta-data")
        self.assertIn("SSRF", str(ctx.exception))

    def test_private_ip_rejected(self):
        with self.assertRaises(wechat_api.ContentImageError):
            wechat_api.default_downloader("http://192.168.1.1/cat.png")

    def test_api_base_host_exempt_for_local_debug(self):
        # 联调：与 WECHAT_API_BASE 同 host 的本地 fake server 不拦截
        import threading
        from http.server import ThreadingHTTPServer
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(FakeAPI()))
        base = "http://127.0.0.1:%d" % server.server_address[1]
        threading.Thread(target=server.serve_forever, daemon=True).start()
        old = os.environ.get("WECHAT_API_BASE")
        os.environ["WECHAT_API_BASE"] = base
        try:
            data, _ = wechat_api.default_downloader(base + "/img/x.png")
            self.assertIsInstance(data, bytes)   # 未被 SSRF 拦截即可
        finally:
            os.environ.pop("WECHAT_API_BASE", None)
            if old:
                os.environ["WECHAT_API_BASE"] = old
            server.shutdown()
            server.server_close()


class TestScrubAndNetError(unittest.TestCase):
    def test_scrub_hides_token(self):
        self.assertEqual(
            wechat_api._scrub("https://api.weixin.qq.com/x?access_token=SECRET123&b=1"),
            "https://api.weixin.qq.com/x?access_token=***&b=1")

    def test_post_json_wraps_urlerror_with_scrub(self):
        # 指向不存在的端口 → URLError，消息不得包含我们塞的 token
        url = "http://127.0.0.1:9/cgi-bin/draft/add?access_token=TOKENSECRET"
        with self.assertRaises(wechat_api.WeChatApiError) as ctx:
            wechat_api._post_json(url, {"a": 1}, timeout=2)
        self.assertNotIn("TOKENSECRET", str(ctx.exception))
        self.assertIn("***", str(ctx.exception))


class TestPollAndPublishMethod(FakeServerTestCase):
    def setUp(self):
        super().setUp()
        self.fake.files["/remote/cover.png"] = (TINY_PNG, "image/png")
        for path, resp in [
            ("/cgi-bin/stable_token", {"access_token": "T", "expires_in": 7200}),
            ("/cgi-bin/media/uploadimg",
             {"url": "http://mmbiz.qpic.cn/c", "errcode": 0}),
            ("/cgi-bin/material/add_material", {"media_id": "TH"}),
            ("/cgi-bin/draft/add", {"media_id": "D"}),
            ("/cgi-bin/freepublish/submit", {"errcode": 0, "publish_id": "P"}),
        ]:
            self.fake.expect(path, resp)

    def article(self, tmpdir):
        cover = os.path.join(tmpdir, "cover.png")
        with open(cover, "wb") as f:
            f.write(COVER_PNG)
        return {"title": "标题x", "digest": "d",
                "content_html": '<img src="%s/remote/cover.png">' % self.base,
                "thumb_image": cover}

    def test_unknown_status_keeps_polling_then_success(self):
        self.fake.expect("/cgi-bin/freepublish/get",
                         {"errcode": 0, "publish_status": 99},
                         {"errcode": 0, "publish_status": 0,
                          "article_detail": {"count": 1,
                                             "item": [{"article_url": "https://s/ok"}]}})
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = wechat_api.publish_article(
                self.cfg(), self.article(tmp), poll_seconds=0.01, max_polls=5)
        self.assertEqual(result["status"], "success")

    def test_poll_exhaustion_raises(self):
        self.fake.expect("/cgi-bin/freepublish/get",
                         {"errcode": 0, "publish_status": 1},
                         {"errcode": 0, "publish_status": 1})
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(wechat_api.WeChatApiError) as ctx:
                wechat_api.publish_article(
                    self.cfg(), self.article(tmp), poll_seconds=0.01, max_polls=2)
        self.assertIn("轮询", str(ctx.exception))

    def test_browser_method_stops_at_draft(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = wechat_api.publish_article(
                self.cfg(publish_method="browser"), self.article(tmp),
                poll_seconds=0.01)
        self.assertEqual(result["status"], "draft-ready-browser")
        self.assertEqual(result["draft_id"], "D")
        self.assertIn("publish_browser.py", result["next"])
        paths = [r[0] for r in self.fake.requests if r[0].startswith("/cgi-bin/")]
        self.assertNotIn("/cgi-bin/freepublish/submit", paths)

    def test_auto_method_downgrades_on_48001(self):
        self.fake.expect("/cgi-bin/freepublish/submit",
                         {"errcode": 48001, "errmsg": "api unauthorized"})
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            result = wechat_api.publish_article(
                self.cfg(publish_method="auto"), self.article(tmp),
                poll_seconds=0.01)
        self.assertEqual(result["status"], "draft-ready-browser")
        self.assertIn("48001", result["reason"])

    def test_api_method_raises_on_48001_without_downgrade(self):
        self.fake.expect("/cgi-bin/freepublish/submit",
                         {"errcode": 48001, "errmsg": "api unauthorized"})
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(wechat_api.WeChatApiError) as ctx:
                wechat_api.publish_article(
                    self.cfg(publish_method="api"), self.article(tmp),
                    poll_seconds=0.01)
        self.assertIn("认证", str(ctx.exception))     # 48001 的 hint

    def test_invalid_publish_method_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(wechat_api.ConfigError):
                wechat_api.publish_article(
                    self.cfg(publish_method="yaml"), self.article(tmp), dry_run=True)

    def test_multipart_has_sanitized_filename(self):
        self.fake.expect("/cgi-bin/freepublish/get",
                         {"errcode": 0, "publish_status": 0,
                          "article_detail": {"count": 1,
                                             "item": [{"article_url": "https://s/1"}]}})
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            cover = os.path.join(tmp, '怪名字"quoted.png')
            with open(cover, "wb") as f:
                f.write(COVER_PNG)
            article = {"title": "t", "digest": "d",
                       "content_html": "<p>x</p>", "thumb_image": cover}
            wechat_api.publish_article(self.cfg(), article, poll_seconds=0.01)
        body = [r[2] for r in self.fake.requests
                if r[0] == "/cgi-bin/material/add_material"][0]
        self.assertIn(b'name="media"', body)
        match = re.search(rb'filename="([^"]*)"', body)
        self.assertTrue(match)
        self.assertNotIn(b'"', match.group(1))       # 引号被净化

    def test_retry_non_token_error_passes_through(self):
        # 40164（IP 白名单）不应触发 token 重试，直接抛出
        self.fake.expect("/cgi-bin/draft/add",
                         {"errcode": 40164, "errmsg": "invalid ip"})
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(wechat_api.WeChatApiError) as ctx:
                wechat_api.publish_article(self.cfg(), self.article(tmp),
                                           poll_seconds=0.01)
        self.assertIn("IP 白名单", str(ctx.exception))
        token_calls = [r for r in self.fake.requests
                       if r[0] == "/cgi-bin/stable_token"]
        self.assertEqual(len(token_calls), 1)        # 没有重取 token

    def test_second_40001_still_fails(self):
        self.fake.expect("/cgi-bin/stable_token",
                         {"access_token": "T1", "expires_in": 7200},
                         {"access_token": "T2", "expires_in": 7200})
        responses = iter([{"errcode": 40001, "errmsg": "x"},
                          {"errcode": 40001, "errmsg": "y"}])
        original = wechat_api._post_json
        states = {"n": 0}

        def always_bad(url, payload, timeout=30):
            if "/cgi-bin/draft/add" in url:
                states["n"] += 1
                return next(responses)
            return original(url, payload, timeout)

        wechat_api._post_json = always_bad
        try:
            with self.assertRaises(wechat_api.WeChatApiError):
                wechat_api.add_draft(self.cfg(), "T1", {
                    "title": "t", "digest": "d",
                    "content": "<p>x</p>", "thumb_media_id": "T"})
        finally:
            wechat_api._post_json = original
        self.assertEqual(states["n"], 2)             # 试了两次后放弃

    def test_force_refresh_used_on_retry(self):
        # 重试时 stable_token 请求体应带 force_refresh=true
        self.fake.expect("/cgi-bin/stable_token",
                         {"access_token": "T1", "expires_in": 7200},
                         {"access_token": "T2", "expires_in": 7200},
                         {"access_token": "T3", "expires_in": 7200})
        self.fake.expect("/cgi-bin/draft/add",
                         {"errcode": 40001, "errmsg": "x"},
                         {"media_id": "OK"})
        wechat_api.get_stable_token(self.cfg())
        media_id = None
        try:
            media_id = wechat_api.add_draft(self.cfg(), "T1", {
                "title": "t", "digest": "d",
                "content": "<p>x</p>", "thumb_media_id": "T"})
        except wechat_api.WeChatApiError:
            pass
        self.assertEqual(media_id, "OK")
        token_bodies = [json.loads(r[2]) for r in self.fake.requests
                        if r[0] == "/cgi-bin/stable_token"]
        self.assertEqual(len(token_bodies), 2)
        self.assertIs(token_bodies[0]["force_refresh"], False)
        self.assertIs(token_bodies[1]["force_refresh"], True)

    def test_submit_missing_publish_id_raises(self):
        self.fake.expect("/cgi-bin/freepublish/submit", {"errcode": 0, "errmsg": "ok"})
        with self.assertRaises(wechat_api.WeChatApiError) as ctx:
            wechat_api.submit_publish(self.cfg(), "T", "D")
        self.assertIn("publish_id", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
