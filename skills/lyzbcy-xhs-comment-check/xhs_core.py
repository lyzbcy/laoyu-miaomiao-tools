#!/usr/bin/env python3
"""纯逻辑层:稳定ID/通知文本解析/垃圾过滤/persona加载。无浏览器依赖。"""
import hashlib
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PERSONA_FILE = BASE_DIR / "persona.json"


def stable_id(username: str, text: str) -> str:
    """md5 稳定去重 ID。开源版用 Python hash() 有随机盐,跨进程不稳定,必须替换。"""
    return hashlib.md5(f"{username}\x00{text[:200]}".encode("utf-8")).hexdigest()


def load_persona() -> dict:
    with PERSONA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


# 通知条目 innerText 里混入的 UI 文本(dry-run 实测):
TIME_LINE = re.compile(r"^(\d+\s*(秒|分钟|小时|天)前|刚刚|昨天.*|前天.*|\d{1,2}-\d{1,2}|\d{4}-\d{1,2}-\d{1,2}.*)$")
ACTION_LINE = re.compile(r"^(评论|赞|收藏|关注|回复)了?(你的)?(笔记|图片|视频|评论)?.*$")
BUTTON_LINE = re.compile(r"^(回复|查看|点赞|举报|删除|复制)$")


def parse_notification_text(text: str):
    """解析通知条目 innerText。返回 {username, comment} 或 None(不可回复/他人回复)。

    清洗流水线:剥离时间行/动作行(含粘时间的)/按钮文本行 → 首行=用户名 → 其余=评论正文。
    「回复了你的评论」+含「作者」= 别人在回复我的评论,不是新评论 → None。
    """
    if "回复了你的评论" in text and "作者" in text:
        return None
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return None
    username = lines[0]
    body = []
    for l in lines[1:]:
        if TIME_LINE.match(l) or BUTTON_LINE.match(l):
            continue
        if ACTION_LINE.match(l) and len(l) <= 20:
            continue  # 动作行(可能粘着时间),短于20字才算,避免误杀长评论
        body.append(l)
    comment = "\n".join(body).strip()
    if not comment or len(comment) <= 3:
        return None
    return {"username": username, "comment": comment}


def is_spam(text: str, persona: dict) -> bool:
    """垃圾/引流过滤。规则平移开源版 + persona 词表。"""
    t = text.strip()
    if len(t) <= 3 or t.isdigit():
        return True
    if "该评论已删除" in t:
        return True
    kws = persona.get("spamKeywords", [])
    return any(kw in t for kw in kws)


def is_malicious(text: str, persona: dict) -> bool:
    """提示注入检测:命中走机械模板,绝不进 LLM(平移抖音纪律)。"""
    t = text.lower()
    return any(kw.lower() in t for kw in persona.get("maliciousKeywords", []))


BATCH_PROMPT_TEMPLATE = """你是小红书博主「{name}」本人,需要一次性回复自己笔记下的 {n} 条评论。
账号定位:{accountProfile}
你的性格:{persona}

每条评论的回复要求:
- 像朋友聊天,自然口语,不要官方腔、不要营销感
- 60~120字,最多1个emoji
- 有干货就给干货,不懂就说不懂,真诚第一
- 不引导加群/私信,不承诺任何收益
- 只输出回复正文:不要emoji开头、不要署名,前后缀系统会自动加

待回复列表(JSON数组,含 id/用户名/笔记主题/评论内容):
{items_json}

输出要求:只输出一个 JSON 对象,key 是评论的 id,value 是对应的回复正文(纯文本)。不要输出任何其他文字、不要用代码围栏。示例:
{{"id1": "回复正文1", "id2": "回复正文2"}}"""


def build_batch_prompt(persona: dict, items: list) -> str:
    """打包 prompt:人设+规则只出现一次,摊薄固定输入成本(单条约 250 token)。"""
    idt = persona["identity"]
    slim = [{"id": it["id"], "user": it["username"],
             "note": it.get("note_context", ""), "comment": it["comment"]} for it in items]
    return fill_template(BATCH_PROMPT_TEMPLATE, persona, n=len(items),
                         items_json=json.dumps(slim, ensure_ascii=False, indent=1))


def parse_batch_response(text: str, items: list) -> dict:
    """解析打包回复为 {id: reply}。容错:剥代码围栏;畸形/不完整返回部分结果或空(由调用方兜底)。"""
    body = (text or "").strip()
    if body.startswith("```"):
        first_nl = body.find("\n")
        body = body[first_nl + 1:] if first_nl != -1 else ""
        if body.rstrip().endswith("```"):
            body = body.rstrip()[:-3].rstrip()
    start, end = body.find("{"), body.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    try:
        data = json.loads(body[start:end + 1])
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    valid_ids = {it["id"] for it in items}
    return {k: str(v).strip() for k, v in data.items() if k in valid_ids and v and str(v).strip()}


def format_reply(text: str, persona: dict) -> str:
    """强制统一格式(对齐抖音):🦞开头 + 固定签名结尾。
    LLM 不守规矩(自带emoji/署名)时先剥掉再包装。"""
    idt = persona["identity"]
    emoji = idt.get("emoji", "🦞")
    sig = idt.get("signature", "")
    body = (text or "").strip()
    # 剥掉 LLM 自己加的 emoji 前缀
    if body.startswith(emoji):
        body = body[len(emoji):].lstrip()
    # 剥掉 LLM 自己加的签名行(完整版或简写版,任何「——来自」开头的行)
    if sig and sig in body:
        body = body.replace(sig, "").strip()
    body = re.sub(r"^\s*——来自.*$", "", body, flags=re.MULTILINE).strip()
    body = body.strip()
    if not body:
        body = "谢谢支持~"
    return f"{emoji} {body}\n\n{sig}"


def fill_template(template: str, persona: dict, **extra) -> str:
    """填充 {emoji}/{sig}/{name}/{accountProfile}/{persona}/{noteContext}/{comment} 等占位。"""
    idt = persona["identity"]
    mapping = {
        "emoji": idt.get("emoji", ""),
        "sig": idt.get("signature", ""),
        "name": idt.get("name", ""),
        "accountProfile": persona.get("accountProfile", ""),
        "persona": idt.get("persona", ""),
        **extra,
    }
    out = template
    for k, v in mapping.items():
        out = out.replace("{" + k + "}", str(v))
    return out
