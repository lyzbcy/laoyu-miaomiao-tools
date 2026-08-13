#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""微信公众号全自动发布引擎（方案 A：纯官方 API 链路）。

零第三方依赖（仅 Python 标准库），供 skill 的 agent 或任何 cron 直接调用。

链路：stable_token → 正文图 uploadimg → 封面 add_material
      → draft/add 建草稿 → freepublish/submit 发布 → freepublish/get 轮询终态。

用法：
  python3 wechat_api.py token   --config config.json
  python3 wechat_api.py publish --article article.json --config config.json [--dry-run]
  python3 wechat_api.py status  --config config.json --publish-id PUB_XXX

article.json 字段：
  title(必填,≤32字) author(≤16) digest(≤120)
  content_html 或 content_html_file（二选一；正文内 <img> 外链图会被自动
  下载→上传→替换为 mmbiz.qpic.cn URL）
  thumb_image(图文必填,封面图路径) content_source_url(阅读原文)
  article_type: news(默认) | newspic(图片消息,需 image_list)
  need_open_comment / only_fans_can_comment: 0|1

环境变量：
  WECHAT_API_BASE  覆盖默认 API 域名 https://api.weixin.qq.com（联调/测试用）

注意：freepublish 仅限已认证公众号；未认证账号请走浏览器方案（见 skill 的
browser-playbook），或把本脚本当"推草稿"工具用（到 draft/add 为止）。
"""
import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

DEFAULT_API_BASE = "https://api.weixin.qq.com"
CONTENT_IMAGE_MAX_BYTES = 1024 * 1024      # uploadimg：1MB
THUMB_IMAGE_MAX_BYTES = 10 * 1024 * 1024   # add_material type=image：10MB
CONTENT_MAX_CHARS = 20000                  # draft/add content：2 万字符

# Windows 老终端（cp936）打印 ✓/✅ 会 UnicodeEncodeError，统一替换不崩
try:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


class SkillError(Exception):
    """基类：错误消息自带给用户看的中文提示。"""


class ConfigError(SkillError):
    pass


class ArticleError(SkillError):
    pass


class ContentImageError(SkillError):
    pass


class WeChatApiError(SkillError):
    def __init__(self, errcode, errmsg, hint=""):
        self.errcode = errcode
        self.errmsg = errmsg
        self.hint = hint
        msg = "微信接口错误 errcode=%s errmsg=%s" % (errcode, errmsg)
        if hint:
            msg += " ｜排查：%s" % hint
        super().__init__(msg)


# ---------------------------------------------------------------------------
# HTTP 基础（测试通过 monkeypatch _post_json 注入故障）
# ---------------------------------------------------------------------------
def api_base():
    return os.environ.get("WECHAT_API_BASE", DEFAULT_API_BASE)


def _scrub(url):
    """脱敏：URL 里的 access_token 不允许进任何错误输出。"""
    return re.sub(r"access_token=[^&]+", "access_token=***", url)


def _wrap_network_error(url, exc):
    """把 HTTPError/URLError 包成 WeChatApiError，且不泄漏 token。"""
    detail = getattr(exc, "code", "") and " HTTP %s" % exc.code or ""
    return WeChatApiError(-1, "网络异常%s：%s（%s）"
                          % (detail, _scrub(url), exc.__class__.__name__))


def _read(resp):
    raw = resp.read()
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise WeChatApiError(-1, "接口返回非 JSON（%.80s）" % raw)


def _post_json(url, payload, timeout=30):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return _read(resp)
    except urllib.error.HTTPError as exc:
        raise _wrap_network_error(url, exc)
    except OSError as exc:   # URLError / socket.timeout / ConnectionReset…
        raise _wrap_network_error(url, exc)


def _sanitize_filename(name):
    """multipart filename 净化：去引号/换行，防 Content-Disposition 注入。"""
    return re.sub(r'["\r\n\\]', "_", name)[:80] or "upload.bin"


def _post_multipart(url, field, filename, data, content_type, timeout=60):
    boundary = "----SkillBoundary" + uuid.uuid4().hex
    parts = []
    parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; "
                  "filename=\"%s\"\r\nContent-Type: %s\r\n\r\n"
                  % (boundary, field, _sanitize_filename(filename),
                     content_type)).encode("utf-8"))
    parts.append(data)
    parts.append(("\r\n--%s--\r\n" % boundary).encode("utf-8"))
    body = b"".join(parts)
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "multipart/form-data; boundary=%s" % boundary})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return _read(resp)
    except urllib.error.HTTPError as exc:
        raise _wrap_network_error(url, exc)
    except OSError as exc:
        raise _wrap_network_error(url, exc)


def _check_errcode(resp, action):
    """微信成功响应可能没有 errcode 字段；有且非 0 才算错。"""
    errcode = resp.get("errcode", 0)
    if errcode:
        raise WeChatApiError(errcode, resp.get("errmsg", ""), errcode_hint(errcode))
    return resp


# ---------------------------------------------------------------------------
# 错误码 → 人话提示
# ---------------------------------------------------------------------------
_HINTS = {
    40001: "AppSecret 不对，或 access_token 已失效（本脚本会自动刷新重试一次）",
    40014: "access_token 无效/过期，本脚本会自动刷新重试一次",
    40125: "AppSecret 不正确，去公众平台→设置与开发→基本配置 核对",
    40013: "AppID 不正确（invalid appid），核对 config.json 的 appid",
    41002: "缺少 appid 参数",
    40164: "调用方 IP 不在白名单。去 公众平台→设置与开发→基本配置→IP 白名单 添加本机公网 IP",
    40005: "不支持的媒体格式：正文图仅支持 jpg/png",
    40009: "图片超过大小限制：正文图须 <1MB、封面须 <10MB，请压缩后重试",
    41001: "缺少 access_token 参数",
    43101: "用户未关注/无法送达（群发场景）",
    45009: "接口调用次数超限（每日限额）",
    48001: "api 功能未授权——freepublish 仅限【已认证】公众号。未认证账号请改走浏览器发布方案，或仅推草稿后人工发布",
    53401: "发布失败：内容涉嫌违规或触发平台审核，去后台查看详情",
    200013: "已达发布/群发次数上限",
}


def errcode_hint(errcode):
    if errcode in _HINTS:
        return _HINTS[errcode]
    return ("未收录的错误码：可在公众平台后台「设置与开发→接口权限」或"
            "微信开发者社区搜索该 errcode")


# ---------------------------------------------------------------------------
# 配置与文章校验
# ---------------------------------------------------------------------------
def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return load_config_dict(json.load(f))


def load_config_dict(d):
    for key in ("appid", "secret"):
        if not d.get(key):
            raise ConfigError(
                "config 缺少必填字段 %r（在 公众平台→设置与开发→基本配置 里获取）" % key)
    return d


def load_article(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    base_dir = os.path.dirname(os.path.abspath(path))
    article = validate_article(raw, base_dir=base_dir)
    return article


def validate_article(raw, base_dir=None):
    """校验并规范化文章 dict；base_dir 用于解析 content_html_file 相对路径。"""
    art = dict(raw)

    title = (art.get("title") or "").strip()
    if not title:
        raise ArticleError("title 必填（图文标题）")
    if len(title) > 32:
        raise ArticleError("标题 %d 字，超过 32 字上限： %r" % (len(title), title[:40]))
    art["title"] = title

    for key, limit in (("author", 16), ("digest", 120)):
        value = art.get(key) or ""
        if len(value) > limit:
            raise ArticleError("%s %d 字，超过 %d 字上限" % (key, len(value), limit))
        art[key] = value

    # 正文：content_html 优先，其次从 content_html_file 读
    if not art.get("content_html") and art.get("content_html_file"):
        path = art["content_html_file"]
        if base_dir and not os.path.isabs(path):
            path = os.path.join(base_dir, path)
        with open(path, "r", encoding="utf-8") as f:
            art["content_html"] = f.read()
    content = art.get("content_html") or ""
    if not content:
        raise ArticleError("正文为空：需要 content_html 或 content_html_file")
    if len(content) > CONTENT_MAX_CHARS:
        raise ArticleError("正文 %d 字符，超过 2 万字符上限（1MB）" % len(content))

    art.setdefault("article_type", "news")
    if art["article_type"] == "newspic":
        if not art.get("image_list"):
            raise ArticleError("图片消息(article_type=newspic)需要 image_list（本地图片路径数组）")
        art.pop("thumb_image", None)
    elif not art.get("thumb_image"):
        raise ArticleError("图文(news)需要 thumb_image（封面图路径）")

    art.setdefault("need_open_comment", 0)
    art.setdefault("only_fans_can_comment", 0)
    return art


# ---------------------------------------------------------------------------
# 图片工具
# ---------------------------------------------------------------------------
_JPG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def sniff_image(data, content_type=""):
    """返回规范化 MIME；不支持的格式抛错。"""
    if data.startswith(_PNG_MAGIC):
        return "image/png"
    if data.startswith(_JPG_MAGIC):
        return "image/jpeg"
    raise ContentImageError(
        "不支持的图片格式（Content-Type=%s，魔数=%s）：微信正文图仅支持 jpg/png"
        % (content_type or "?", data[:8].hex()))


def _is_private_host(host):
    """SSRF 防护：拒绝私网/回环/链路本地目标（联调 fake server 除外）。"""
    if not host:
        return True
    host = host.lower().rstrip(".")
    if host == "localhost" or host.startswith("127."):
        return True
    if host.startswith(("10.", "192.168.", "169.254.", "0.")):
        return True
    if host.startswith("172."):
        try:
            first = int(host.split(".")[1])
            if 16 <= first <= 31:
                return True
        except ValueError:
            return True
    try:
        import ipaddress
        return ipaddress.ip_address(host).is_private
    except ValueError:
        return False  # 普通域名


def default_downloader(url, timeout=30):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ContentImageError("仅支持 http(s) 图片外链：%r" % url[:80])
    # 联调模式：与 WECHAT_API_BASE 同 host 的本地 server 不算 SSRF
    api_host = urllib.parse.urlparse(api_base()).netloc.split(":")[0]
    if parsed.netloc.split(":")[0] != api_host and _is_private_host(
            parsed.netloc.split(":")[0]):
        raise ContentImageError(
            "外链图指向内网/本机地址（%s），已按 SSRF 防护拒绝下载。"
            "如确有需要请把图放到公网或改用本地文件" % parsed.netloc)
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        ctype = resp.headers.get("Content-Type", "")
        return resp.read(), ctype


def parse_data_uri(uri):
    match = re.match(r"data:(image/[a-zA-Z0-9.+-]+);base64,(.*)", uri, re.S)
    if not match:
        raise ContentImageError("无法解析的 data URI 图片：%s…" % uri[:50])
    return base64.b64decode(match.group(2)), match.group(1)


_PLACEHOLDER_MAX_BYTES = 1024  # ≤1KB 的 data URI 图基本是懒加载占位图


def _placeholder_kind(src):
    """占位图判定：unparseable/unsupported/tiny/None(正常图)。"""
    if not src.startswith("data:"):
        return None
    try:
        data, mime = parse_data_uri(src)
    except (ContentImageError, ValueError):
        return "unparseable"
    if mime not in ("image/png", "image/jpeg"):
        return "unsupported"          # gif 等微信不支持的格式
    if len(data) <= _PLACEHOLDER_MAX_BYTES:
        return "tiny"
    return None


# 仅匹配真正的 src=（前面是空白），不误伤 data-src=
_IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_SRC_ATTR = re.compile(r"(\ssrc\s*=\s*)([\"'])([^\"']+)\2", re.IGNORECASE)
_LAZY_ATTR = re.compile(
    r"\sdata-(?:src|original|lazy-src)\s*=\s*([\"'])([^\"']+)\1", re.IGNORECASE)


def clean_content_images(content_html, uploader, downloader=None, onwarn=None):
    """把正文里的外链图/data URI 图全部换成 mmbiz.qpic.cn URL。

    uploader(name, data, mime) -> 新 URL
    downloader(url, timeout) -> (bytes, content_type)
    onwarn(msg) -> 告警通道（默认打 stderr），例如跳过懒加载占位图

    懒加载处理：src 是占位 data URI（gif/≤1KB）时，优先取同标签的
    data-src / data-original / data-lazy-src。
    """
    if downloader is None:
        downloader = default_downloader
    if onwarn is None:
        onwarn = lambda msg: print("⚠ %s" % msg, file=sys.stderr)

    def fix_tag(match):
        tag = match.group(0)
        src_match = _SRC_ATTR.search(tag)
        if not src_match:
            return tag
        src = src_match.group(3)
        host = urllib.parse.urlparse(src).netloc.lower()
        if host.endswith("mmbiz.qpic.cn"):
            return tag                                   # 已是微信域名
        kind = _placeholder_kind(src)
        if kind:
            lazy = _LAZY_ATTR.search(tag)
            if lazy:
                real_src = lazy.group(2)
                onwarn("检测到懒加载占位图（%s），改用真实图 %s"
                       % (kind, real_src[:80]))
                new_src = migrate_src(real_src, uploader, downloader, onwarn)
                return tag[:src_match.start(3)] + new_src + tag[src_match.end(3):]
            if kind in ("unparseable", "unsupported"):
                onwarn("跳过微信不支持的 data URI 图（%s…）" % src[:40])
                return tag
            # kind=tiny 且无更优来源：按正常小图上传
        new_src = migrate_src(src, uploader, downloader, onwarn)
        return tag[:src_match.start(3)] + new_src + tag[src_match.end(3):]

    return _IMG_TAG.sub(fix_tag, content_html)


def migrate_src(src, uploader, downloader, onwarn=None):
    if onwarn is None:
        onwarn = lambda msg: print("⚠ %s" % msg, file=sys.stderr)
    if src.startswith("data:"):
        try:
            data, mime = parse_data_uri(src)
            mime = sniff_image(data, mime)
        except (ContentImageError, ValueError):
            onwarn("跳过不支持的 data URI 图（仅支持 jpg/png）：%s…" % src[:40])
            return src
    elif src.startswith(("http://", "https://")):
        data, ctype = downloader(src)
        mime = sniff_image(data, ctype)
    else:
        raise ContentImageError(
            "正文图片 src 既不是 http(s) 也不是 data URI：%r" % src[:80])
    if len(data) > CONTENT_IMAGE_MAX_BYTES:
        raise ContentImageError(
            "外链图 %s… 有 %.1fMB，超过正文图 1MB 上限——请先压缩（如转为 jpg 质量 80）"
            % (src[:60], len(data) / 1024.0 / 1024.0))
    ext = "png" if mime == "image/png" else "jpg"
    return uploader("content-%d.%s" % (int(time.time() * 1000), ext), data, mime)


# ---------------------------------------------------------------------------
# API 封装
# ---------------------------------------------------------------------------
def get_stable_token(cfg, force_refresh=False):
    """稳定版 access_token：有效期内重复获取不互踢（官方推荐）。"""
    payload = {
        "grant_type": "client_credential",
        "appid": cfg["appid"],
        "secret": cfg["secret"],
        "force_refresh": force_refresh,
    }
    resp = _post_json(api_base() + "/cgi-bin/stable_token", payload)
    token = resp.get("access_token")
    if not token:
        raise WeChatApiError(resp.get("errcode", -1),
                             resp.get("errmsg", "no access_token returned"),
                             errcode_hint(resp.get("errcode", -1)))
    return token


def _with_token_retry(fn, cfg, token, *args, **kwargs):
    """token 失效(40001/40014)时自动重取一次再试（force_refresh 绕开服务端缓存窗口）。"""
    try:
        return fn(cfg, token, *args, **kwargs)
    except WeChatApiError as exc:
        if exc.errcode not in (40001, 40014):
            raise
    token = get_stable_token(cfg, force_refresh=True)
    return fn(cfg, token, *args, **kwargs)


def upload_content_image(cfg, token, name, data, mime):
    """正文图上传（media/uploadimg）→ 返回 mmbiz URL（无 media_id）。"""
    if len(data) > CONTENT_IMAGE_MAX_BYTES:
        raise ContentImageError("正文图 %s 超过 1MB 上限，请压缩" % name)

    def call(_cfg, _token, _name, _data, _mime):
        url = "%s/cgi-bin/media/uploadimg?access_token=%s" % (api_base(), _token)
        resp = _post_multipart(url, "media", _name, _data, _mime)
        _check_errcode(resp, "uploadimg")
        new_url = resp.get("url")
        if not new_url:
            raise WeChatApiError(-1, "uploadimg 未返回 url（keys=%s, errcode=%s）"
                                 % (sorted(resp.keys()), resp.get("errcode")))
        return new_url

    return _with_token_retry(call, cfg, token, name, data, mime)


def upload_thumb(cfg, token, image_path):
    """封面上传（material/add_material type=image）→ 返回 thumb_media_id。"""
    with open(image_path, "rb") as f:
        data = f.read()
    if len(data) > THUMB_IMAGE_MAX_BYTES:
        raise ContentImageError("封面 %s 超过 10MB 上限" % image_path)
    mime = sniff_image(data)
    name = os.path.basename(image_path) or "cover." + ("png" if mime == "image/png" else "jpg")

    def call(_cfg, _token, _name, _data, _mime):
        url = ("%s/cgi-bin/material/add_material?access_token=%s&type=image"
               % (api_base(), _token))
        resp = _post_multipart(url, "media", _name, _data, _mime)
        _check_errcode(resp, "add_material")
        media_id = resp.get("media_id")
        if not media_id:
            raise WeChatApiError(-1, "add_material 未返回 media_id（keys=%s）"
                                 % sorted(resp.keys()))
        return media_id

    return _with_token_retry(call, cfg, token, name, data, mime)


def add_draft(cfg, token, fields):
    """新建草稿 → 返回草稿 media_id。"""
    def call(_cfg, _token, _fields):
        # URL 必须在 call 内构造：token 重试后要带上新 token
        url = "%s/cgi-bin/draft/add?access_token=%s" % (api_base(), _token)
        resp = _post_json(url, {"articles": [_fields]})
        _check_errcode(resp, "draft/add")
        media_id = resp.get("media_id")
        if not media_id:
            raise WeChatApiError(-1, "draft/add 未返回 media_id（keys=%s）"
                                 % sorted(resp.keys()))
        return media_id

    return _with_token_retry(call, cfg, token, fields)


def submit_publish(cfg, token, media_id):
    """提交发布（异步）→ 返回 publish_id。errcode=0 仅代表提交成功。"""
    def call(_cfg, _token, _media_id):
        url = "%s/cgi-bin/freepublish/submit?access_token=%s" % (api_base(), _token)
        resp = _post_json(url, {"media_id": _media_id})
        _check_errcode(resp, "freepublish/submit")
        publish_id = resp.get("publish_id")
        if not publish_id:
            raise WeChatApiError(-1, "submit 未返回 publish_id（keys=%s）"
                                 % sorted(resp.keys()))
        return publish_id

    return _with_token_retry(call, cfg, token, media_id)


_STATUS_TEXT = {
    0: "success", 1: "in_progress", 2: "original_check_failed",
    3: "normal_failed", 4: "platform_rejected", 5: "deleted_after_publish",
    6: "banned",
}


def get_publish_status(cfg, token, publish_id):
    def call(_cfg, _token, _pid):
        url = "%s/cgi-bin/freepublish/get?access_token=%s" % (api_base(), _token)
        resp = _post_json(url, {"publish_id": _pid})
        _check_errcode(resp, "freepublish/get")
        return resp

    return _with_token_retry(call, cfg, token, publish_id)


def _build_fields(art, content, thumb_media_id=None):
    """按 article_type 构造 draft/add 的单篇字段（news 与 newspic 共用）。"""
    fields = {
        "article_type": art["article_type"],
        "title": art["title"],
        "author": art.get("author", ""),
        "digest": art.get("digest", ""),
        "content": content,
        "need_open_comment": art["need_open_comment"],
        "only_fans_can_comment": art["only_fans_can_comment"],
    }
    if art["article_type"] == "newspic":
        fields["image_info"] = {"image_list": art["_image_urls"]}
    else:
        fields["thumb_media_id"] = thumb_media_id
    if art.get("content_source_url"):
        fields["content_source_url"] = art["content_source_url"]
    return fields


def _upload_images(cfg, token, art, log=None, onwarn=None):
    """上传正文外链图 + 封面/图片消息素材；返回 (content, thumb_media_id)。

    onwarn(msg)：洗图过程的非致命告警通道（懒加载占位图等）。
    """
    log = log or (lambda msg: None)

    def uploader(name, data, mime):
        url = upload_content_image(cfg, token, name, data, mime)
        log("✓ 正文图已上传：%s" % url)
        return url

    content = clean_content_images(art["content_html"], uploader, onwarn=onwarn)

    if art["article_type"] == "newspic":
        image_urls = []
        for path in art["image_list"]:
            with open(path, "rb") as f:
                data = f.read()
            image_urls.append(uploader(os.path.basename(path), data,
                                       sniff_image(data)))
        art["_image_urls"] = image_urls
        return content, None

    thumb_id = upload_thumb(cfg, token, art["thumb_image"])
    log("✓ 封面已上传：thumb_media_id=%s" % thumb_id)
    return content, thumb_id


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def _dry_run_check_resources(art, onwarn):
    """干跑时做一次轻量存在性校验，避免'一切就绪'的假象。"""
    if art["article_type"] == "news" and not os.path.exists(art["thumb_image"]):
        onwarn("封面不存在：%s" % art["thumb_image"])
    for path in art.get("image_list", []) or []:
        if not os.path.exists(path):
            onwarn("image_list 图片不存在：%s" % path)


def publish_article(cfg, article, poll_seconds=5.0, max_polls=36,
                    dry_run=False, log=None):
    """一条龙：洗图 → 封面 → 草稿 → 发布 → 轮询终态。

    cfg["publish_method"]：
      "api"     完整 API 链路（freepublish，需已认证）
      "browser" 只推草稿，返回 draft-ready-browser（配合 publish_browser.py）
      "auto"    默认：先走 api，遇 48001（无权限）自动降级为 browser
                （此时草稿已入箱，直接点发表即可，勿重复建草稿）

    返回 dict：
      dry_run=True → {"status": "dry-run", "steps": [...]}（不触网）
      正常         → {"status": "success", "publish_id", "article_url", ...}
                     或 {"status": "draft-ready-browser", ...}（browser/auto 降级）
    草稿发布后即从草稿箱消失（官方行为，一次性）。
    """
    log = log or (lambda msg: print(msg, file=sys.stderr))
    art = validate_article(article)
    method = cfg.get("publish_method", "auto") if isinstance(cfg, dict) else "auto"
    if method not in ("api", "browser", "auto"):
        raise ConfigError("publish_method 仅支持 api/browser/auto，收到 %r" % method)

    if dry_run:
        steps = [
            "POST /cgi-bin/stable_token（stable_token 获取 access_token）",
            "正文外链图 → POST /cgi-bin/media/uploadimg（≤1MB，jpg/png）",
        ]
        if art["article_type"] == "newspic":
            steps.append("图片消息：image_list %d 张逐一 uploadimg"
                         % len(art["image_list"]))
        else:
            steps.append("封面 %s → POST /cgi-bin/material/add_material?type=image"
                         % art.get("thumb_image"))
        steps.append("POST /cgi-bin/draft/add（标题 %r，摘要 %r）"
                     % (art["title"], art.get("digest", "")))
        if method == "browser":
            steps.append("【browser】到此为止：草稿入箱，改用 scripts/publish_browser.py 点发表")
        else:
            steps.append("POST /cgi-bin/freepublish/submit（发布草稿）")
            steps.append("轮询 POST /cgi-bin/freepublish/get 直至终态")
            if method == "auto":
                steps.append("【auto】若 submit 报 48001（未认证）→ 自动降级：草稿已入箱，"
                             "改用 scripts/publish_browser.py publish --title 点发表（勿重复建草稿）")
        _dry_run_check_resources(art, log)
        return {"status": "dry-run", "title": art["title"],
                "publish_method": method,
                "article_type": art["article_type"], "steps": steps}

    cfg = load_config_dict(cfg)
    token = get_stable_token(cfg)
    log("✓ access_token 已获取")

    content, thumb_id = _upload_images(cfg, token, art, log,
                                       onwarn=lambda m: log("⚠ %s" % m))
    fields = _build_fields(art, content, thumb_id)

    draft_id = add_draft(cfg, token, fields)
    log("✓ 草稿已创建：media_id=%s（去后台草稿箱可见）" % draft_id)

    if method == "browser":
        log("【browser】按配置停在草稿箱，交由浏览器发布")
        return _draft_ready_browser(draft_id, art, "publish_method=browser")

    try:
        publish_id = submit_publish(cfg, token, draft_id)
    except WeChatApiError as exc:
        if method == "auto" and exc.errcode == 48001:
            log("【auto】API 发布无权限(48001)，自动降级浏览器方案（草稿已入箱，勿重复建草稿）")
            return _draft_ready_browser(draft_id, art, "48001 未认证账号")
        raise
    log("✓ 发布任务已提交：publish_id=%s（异步）" % publish_id)

    for i in range(max_polls):
        resp = get_publish_status(cfg, token, publish_id)
        raw_status = resp.get("publish_status")
        status = _STATUS_TEXT.get(raw_status)
        if status == "success":
            item = (resp.get("article_detail", {}).get("item") or [{}])[0]
            result = {
                "status": "success", "publish_id": publish_id,
                "draft_id": draft_id,
                "article_url": item.get("article_url", ""),
            }
            log("✅ 发布成功：%s" % result["article_url"])
            return result
        if status in (None, "in_progress", "unknown"):
            # 未收录的新状态码一律当"进行中"继续轮询，绝不误判失败
            log("… 发布中（第 %d/%d 次轮询，publish_status=%r）"
                % (i + 1, max_polls, raw_status))
            time.sleep(poll_seconds)
            continue
        raise WeChatApiError(
            raw_status if raw_status is not None else -1,
            "发布终态=%s fail_idx=%s" % (status, resp.get("fail_idx", [])),
            "publish_status 见官方文档；2=原创校验失败 3=常规失败 4=平台审核失败 6=封禁")
    raise WeChatApiError(-1, "轮询 %d 次（%ds）仍未到终态" % (max_polls, max_polls * poll_seconds),
                         "可稍后用 status 命令带 --publish-id 查询")


def _draft_ready_browser(draft_id, art, reason):
    """browser/auto 降级的统一返回：草稿已在箱内，下一步是浏览器点发表。"""
    return {
        "status": "draft-ready-browser",
        "draft_id": draft_id,
        "title": art["title"],
        "reason": reason,
        "next": ("草稿已入箱（勿重复 --draft-only）。执行：python3 scripts/"
                 "publish_browser.py publish --title %r（需已 login 保存登录态）；"
                 "或按 references/browser-playbook.md 人工/agent 操作" % art["title"]),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve_config(path=None):
    """定位 config：显式路径 → $WECHAT_AUTOUPLOAD_CONFIG → skill 目录 config.json
    → skill 目录 config.example.json（兜底，仅够 dry-run，会打警告）。"""
    candidates = []
    if path:
        candidates.append(path)
    env = os.environ.get("WECHAT_AUTOUPLOAD_CONFIG")
    if env:
        candidates.append(env)
    candidates.append(os.path.join(SKILL_DIR, "config.json"))
    candidates.append(os.path.join(SKILL_DIR, "config.example.json"))
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            if candidate.endswith(".example.json"):
                print("⚠ 使用示例配置（%s）——只适合 dry-run；"
                      "正式发布请复制为 config.json 并填真实 appid/secret"
                      % candidate, file=sys.stderr)
            return candidate
    raise ConfigError(
        "找不到 config.json（依次找了：%s）。请复制 config.example.json 为 config.json 并填入 appid/secret"
        % "、".join(str(c) for c in candidates if c))


def main(argv=None):
    parser = argparse.ArgumentParser(description="微信公众号全自动发布引擎（纯官方 API）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_token = sub.add_parser("token", help="获取 stable_token（联调用）")
    p_token.add_argument("--config", required=False, default=None,
                         help="缺省依次找 $WECHAT_AUTOUPLOAD_CONFIG、skill 目录下 config.json")

    p_pub = sub.add_parser("publish", help="上传素材→建草稿→发布→轮询终态")
    p_pub.add_argument("--article", required=True, help="article.json 路径")
    p_pub.add_argument("--config", required=False, default=None)
    p_pub.add_argument("--dry-run", action="store_true",
                       help="只打印将执行的步骤，不发起任何请求")
    p_pub.add_argument("--poll-seconds", type=float, default=5.0)
    p_pub.add_argument("--max-polls", type=int, default=36)
    p_pub.add_argument("--draft-only", action="store_true",
                       help="只推到草稿箱（不调用 freepublish，适合未认证号+浏览器/人工发布）")

    p_status = sub.add_parser("status", help="查询发布任务终态")
    p_status.add_argument("--config", required=False, default=None)
    p_status.add_argument("--publish-id", required=True)

    args = parser.parse_args(argv)
    cfg = load_config(resolve_config(args.config))

    if args.cmd == "token":
        print(json.dumps({"access_token": get_stable_token(cfg)}, ensure_ascii=False))
        return 0

    if args.cmd == "status":
        token = get_stable_token(cfg)
        print(json.dumps(get_publish_status(cfg, token, args.publish_id),
                         ensure_ascii=False, indent=2))
        return 0

    article = load_article(args.article)
    if args.draft_only:
        return _draft_only(cfg, article)

    result = publish_article(cfg, article,
                             poll_seconds=args.poll_seconds,
                             max_polls=args.max_polls,
                             dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _draft_only(cfg, article):
    """只推草稿（未认证号的浏览器/人工发布前置步骤）。"""
    art = validate_article(article)
    token = get_stable_token(cfg)
    content, thumb_id = _upload_images(
        cfg, token, art, log=lambda msg: print(msg, file=sys.stderr),
        onwarn=lambda m: print("⚠ %s" % m, file=sys.stderr))
    fields = _build_fields(art, content, thumb_id)
    draft_id = add_draft(cfg, token, fields)
    print(json.dumps({"status": "draft-only", "draft_id": draft_id,
                      "title": art["title"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
