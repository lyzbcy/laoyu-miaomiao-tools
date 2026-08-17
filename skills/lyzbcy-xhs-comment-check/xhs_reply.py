#!/usr/bin/env python3
"""小红书通知页评论采集+回复。移植自 Fisher0012/xhs-auto-reply(MIT)并强化:
1) md5 稳定去重(原版 Python hash 跨进程失配会重复回复)
2) 登录失效检测(LOGIN_EXPIRED,防止把登录页当评论)
3) 发送后核验(点了发送≠发成功)
4) dry-run 模式 + max-replies 可调 + 恶意注入路由(不进 LLM)
浏览器交互路线(开源验证过): notification?type=comment → 「评论和@」Tab
→ .tabs-content-container 条目 → 点"回复" → textarea.comment-input → 点"发送"
运行方式: xvfb-run -a python3 xhs_reply.py [--dry-run] [--max-replies N]
"""
import argparse
import asyncio
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from xhs_core import (stable_id, load_persona, parse_notification_text, is_spam, is_malicious,
                      fill_template, format_reply, build_batch_prompt, parse_batch_response)

BASE_DIR = Path(__file__).resolve().parent
REPLIED_FILE = BASE_DIR / "replied_ids.json"
OUTPUT_DIR = BASE_DIR / "comments-output"
PROFILE_DIR = Path(os.environ.get("XHS_PROFILE_DIR", str(Path.home() / ".openclaw/xhs-profile")))
XHS_URL = "https://www.xiaohongshu.com/notification?type=comment"

DEFAULTS = {"reply_delay_min": 8, "reply_delay_max": 25, "max_replies": 15, "start_delay_max": 300}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.StreamHandler()])
log = logging.getLogger("xhs-reply")


def load_replied() -> set:
    if REPLIED_FILE.exists():
        return set(json.loads(REPLIED_FILE.read_text(encoding="utf-8")))
    return set()


def save_replied(ids: set):
    REPLIED_FILE.write_text(json.dumps(sorted(ids), ensure_ascii=False, indent=2), encoding="utf-8")


def write_result(payload: dict, name: str):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ── LLM(ws-claw-corp,key 自动探测自 openclaw.json) ──
def llm_client():
    from openai import OpenAI
    cfg_path = Path(os.environ.get("OPENCLAW_CONFIG", str(Path.home() / ".openclaw/openclaw.json")))
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    prov = cfg["models"]["providers"]["ws-claw-corp"]
    base = prov.get("baseUrl") or prov.get("baseURL") or prov.get("url")
    if base and "/v1" not in base:
        base = base.rstrip("/") + "/v1"
    model = prov.get("defaultModel") or "th-deepseek-v4-pro-202606"
    return OpenAI(api_key=prov["apiKey"], base_url=base), model


def generate_reply(comment: str, note_context: str, persona: dict) -> str:
    """恶意注入 → 机械模板;LLM 空回复/失败 → 重试1次 → 兜底模板。
    (ws-claw-corp 偶发返回空内容是已知老问题,必须兜底)"""
    if is_malicious(comment, persona):
        log.info("命中恶意关键词,走机械模板(不进LLM)")
        return fill_template(persona["replyTemplates"]["malicious"], persona)
    prompt = fill_template(persona["systemPromptTemplate"], persona,
                           noteContext=note_context, comment=comment)
    for attempt in range(2):
        try:
            client, model = llm_client()
            # max_tokens 必须 ≥2000:该模型输出先走思维链(实测烧 300~700),300 会被思维链吃光导致 content=''(finish=length)
            rsp = client.chat.completions.create(model=model, max_tokens=2000, temperature=0.8,
                                                 messages=[{"role": "user", "content": prompt}])
            content = (rsp.choices[0].message.content or "").strip()
            if content:
                return format_reply(content, persona)  # 统一强制格式:🦞开头+固定签名
            log.warning(f"LLM 返回空内容(第{attempt + 1}次)")
        except Exception as e:
            log.warning(f"LLM 调用失败(第{attempt + 1}次): {e}")
    templates = persona["replyTemplates"]
    fallback = templates["fallbackShort"] if len(comment) <= 10 else templates["fallbackLong"]
    return fill_template(fallback, persona)


def note_context_for(note_hash, persona) -> str:
    for prefix, desc in persona.get("knownNotes", {}).items():
        if note_hash and note_hash.startswith(prefix[:16]):
            return desc
    return persona.get("accountProfile", "博主的小红书笔记")


async def check_login(page) -> bool:
    """登录态预检:被重定向到登录页/出现登录元素 → False。"""
    if "login" in page.url:
        return False
    found_login_ui = await page.evaluate("""() => !!(
        document.querySelector('.login-container') || document.querySelector('.qrcode') ||
        document.querySelector('[class*="login-modal"]') ||
        (document.body && document.body.innerText.includes('扫码登录') && !document.querySelector('.tabs-content-container'))
    )""")
    return not found_login_ui


async def collect(page):
    """切「评论和@」并抓取条目。返回 (登录正常?, items)。"""
    await page.goto(XHS_URL, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(random.randint(2000, 3500))
    if not await check_login(page):
        return False, []
    await page.evaluate("""() => {
        const tabs = document.querySelectorAll('.reds-tab-item.tab-item');
        const t = Array.from(tabs).find(t => t.textContent.includes('评论和@'));
        if (t) t.click();
    }""")
    await page.wait_for_timeout(2000)
    items = await page.evaluate("""() => {
        const c = document.querySelector('.tabs-content-container');
        if (!c) return [];
        return Array.from(c.children).map((item, idx) => {
            const text = item.innerText ? item.innerText.trim() : '';
            const img = item.querySelector('img[src*="notes"], img[src*="spectrum"]');
            return {idx, text, note_hash: img ? img.src.split('/').slice(-1)[0].split('?')[0] : null};
        }).filter(i => i.text.length > 5);
    }""")
    return True, items


async def send_one(page, idx: int, reply_text: str) -> str:
    """对第 idx 条执行回复。返回 verified|sent|click_fail|fill_fail|send_fail。"""
    clicked = await page.evaluate("""(idx) => {
        const c = document.querySelector('.tabs-content-container');
        const item = c && c.children[idx];
        if (!item) return false;
        const btn = Array.from(item.querySelectorAll('*')).find(e =>
            e.textContent && e.textContent.trim() === '回复' && e.children.length === 0);
        if (btn) { btn.click(); return true; }
        return false;
    }""", idx)
    if not clicked:
        return "click_fail"
    await page.wait_for_timeout(random.randint(1200, 2000))
    filled = await page.evaluate("""(t) => {
        const ta = document.querySelector('textarea.comment-input');
        if (!ta) return false;
        const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
        setter.call(ta, t);
        ta.dispatchEvent(new Event('input', {bubbles: true}));
        return true;
    }""", reply_text)
    if not filled:
        return "fill_fail"
    await page.wait_for_timeout(random.randint(800, 1500))
    sent = await page.evaluate("""() => {
        const btn = Array.from(document.querySelectorAll('*')).find(e =>
            e.textContent && e.textContent.trim() === '发送' && e.children.length === 0 && e.offsetParent !== null);
        if (btn) { btn.click(); return true; }
        return false;
    }""")
    if not sent:
        return "send_fail"
    await page.wait_for_timeout(random.randint(1500, 3000))
    # 核验:回复框收起 或 条目内出现我们的回复片段(参数打包成单对象,Playwright只收一个arg)
    verified = await page.evaluate("""(p) => {
        const c = document.querySelector('.tabs-content-container');
        const item = c && c.children[p.idx];
        if (!item) return false;
        const open = item.querySelector('textarea.comment-input');
        return !open || item.innerText.includes(p.frag);
    }""", {"idx": idx, "frag": reply_text[:15]})
    return "verified" if verified else "sent"


def generate_replies_batch(queue: list, persona: dict) -> dict:
    """打包生成:一次 LLM 调用出全部回复(省输入 token:人设/规则只发一次)。
    恶意评论不进 LLM(直接模板);返回 {id: 已格式化回复}。缺条由调用方单条兜底。"""
    out = {}
    safe = []
    for q in queue:
        if is_malicious(q["comment"], persona):
            log.info(f"命中恶意关键词,走机械模板: @{q['username']}")
            out[q["id"]] = fill_template(persona["replyTemplates"]["malicious"], persona)
        else:
            safe.append(q)
    if not safe:
        return out
    # 输出预算:每条预留 ~900(思维链+正文),上限 16000(模型 maxTokens 131072,安全)
    budget = min(16000, 900 * len(safe) + 500)
    for attempt in range(2):
        try:
            client, model = llm_client()
            rsp = client.chat.completions.create(
                model=model, max_tokens=budget, temperature=0.8,
                messages=[{"role": "user", "content": build_batch_prompt(persona, safe)}])
            content = (rsp.choices[0].message.content or "").strip()
            parsed = parse_batch_response(content, safe) if content else {}
            if parsed:
                log.info(f"打包生成 {len(parsed)}/{len(safe)} 条(一次调用)")
                for q in safe:
                    if q["id"] in parsed:
                        out[q["id"]] = format_reply(parsed[q["id"]], persona)
                if len(parsed) == len(safe):
                    return out  # 全中,无需兜底
                break  # 部分成功,缺的走单条兜底
            log.warning(f"打包调用结果不可解析(第{attempt + 1}次)")
        except Exception as e:
            log.warning(f"打包调用失败(第{attempt + 1}次): {e}")
    return out


async def run(dry_run: bool, max_replies: int):
    from playwright.async_api import async_playwright
    persona = load_persona()
    replied = load_replied()
    stats = {"collected": 0, "skipped_replied": 0, "skipped_spam": 0, "replied": 0,
             "unverified": 0, "errors": 0, "dry_run": bool(dry_run)}
    detail = []

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), headless=False,
            args=["--no-first-run", "--no-default-browser-check", "--disable-gpu"],
            viewport={"width": 1280, "height": 900})
        page = browser.pages[0] if browser.pages else await browser.new_page()
        ok, items = await collect(page)
        if not ok:
            await browser.close()
            log.error("登录态失效")
            write_result({"status": "LOGIN_EXPIRED", "time": str(datetime.now())}, "unreplied-latest.json")
            print("LOGIN_EXPIRED")
            return 2
        stats["collected"] = len(items)
        log.info(f"抓到 {len(items)} 条通知")

        queue = []
        for it in items:
            parsed = parse_notification_text(it["text"])
            if parsed is None:
                continue
            cid = stable_id(parsed["username"], parsed["comment"])
            if cid in replied:
                stats["skipped_replied"] += 1
                continue
            if is_spam(parsed["comment"], persona):
                stats["skipped_spam"] += 1
                replied.add(cid)  # 垃圾也标记,避免反复看到
                continue
            queue.append({**parsed, "id": cid, "idx": it["idx"], "note_hash": it["note_hash"],
                          "note_context": note_context_for(it["note_hash"], persona)})
            if len(queue) >= max_replies:
                break

        # 打包一次生成全部回复(缺失/失败的条目单条兜底)
        batch = generate_replies_batch(queue, persona)
        for q in queue:
            q["reply"] = batch.get(q["id"]) or generate_reply(q["comment"], q["note_context"], persona)
        write_result({"count": len(queue), "items": queue, "stats": stats}, "reply-plan.json")

        if dry_run:
            log.info(f"DRY-RUN: 生成 {len(queue)} 条回复计划,未发送")
            await browser.close()
            save_replied(replied)
            print(json.dumps({"status": "DRY_RUN", "count": len(queue), "stats": stats}, ensure_ascii=False))
            return 0

        for q in queue:
            try:
                res = await send_one(page, q["idx"], q["reply"])
                if res == "verified":
                    stats["replied"] += 1
                    replied.add(q["id"])
                elif res == "sent":
                    stats["unverified"] += 1
                    replied.add(q["id"])  # 保守:已发送未核验也记录,宁可少回不重复回
                else:
                    stats["errors"] += 1
                detail.append({"username": q["username"], "comment": q["comment"][:50],
                               "reply": q["reply"][:60], "result": res})
                await page.wait_for_timeout(random.randint(
                    DEFAULTS["reply_delay_min"], DEFAULTS["reply_delay_max"]) * 1000)
            except Exception as e:
                stats["errors"] += 1
                log.error(f"处理 {q.get('username', '?')} 出错: {e}")
        await browser.close()

    save_replied(replied)
    write_result({"stats": stats, "detail": detail, "time": str(datetime.now())}, "run-result.json")
    print(json.dumps({"status": "DONE", **stats}, ensure_ascii=False))
    return 0 if stats["errors"] == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只采集+生成计划,不发送")
    ap.add_argument("--max-replies", type=int, default=DEFAULTS["max_replies"])
    ap.add_argument("--no-start-delay", action="store_true", help="跳过随机启动延迟(测试用)")
    a = ap.parse_args()
    if not a.no_start_delay:
        delay = random.randint(0, DEFAULTS["start_delay_max"])
        log.info(f"随机启动延迟 {delay}s (可用 --no-start-delay 跳过)")
        time.sleep(delay)
    sys.exit(asyncio.run(run(a.dry_run, a.max_replies)))


if __name__ == "__main__":
    main()
