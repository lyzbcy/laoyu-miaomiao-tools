#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""方案 B 的独立部署实现：用持久化登录态把 mp.weixin.qq.com 草稿箱里的草稿点发表。

依赖（可选，仅本脚本需要；wechat_api.py 保持零依赖）：
  pip3 install playwright && python3 -m playwright install chromium

子命令：
  login    有头浏览器打开公众平台，人工扫码后保存登录态（首次一次性操作）
  publish  用已保存登录态，把指定标题的草稿点「发表」并截图验证

⚠️ 后台 DOM 会改版：选择器是"尽力而为"（语义化文本定位）。
失败时按 references/browser-playbook.md 的语义步骤人工/agent 操作，
并顺手把新选择器更新进本脚本。绝不允许静默失败。
"""
import argparse
import json
import os
import sys
import time

MP_HOME = "https://mp.weixin.qq.com/"
DEFAULT_STATE = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "state", "mp_storage_state.json")


def _require_playwright():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except ImportError:
        print("未安装 playwright。先执行：\n"
              "  pip3 install playwright && python3 -m playwright install chromium",
              file=sys.stderr)
        return False


def _secure_state(path):
    """登录态文件等价于账号凭据：落盘后立刻收紧权限为 600。"""
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _logged_in(page):
    """登录成功启发式：跳到 /cgi-bin/ 后台页。"""
    return "/cgi-bin/" in page.url and "login" not in page.url


def _shot(page, state_dir, name):
    logs = os.path.join(state_dir, "logs")
    os.makedirs(logs, exist_ok=True)
    path = os.path.join(logs, "%s-%s.png" % (time.strftime("%Y%m%d-%H%M%S"), name))
    try:
        page.screenshot(path=path, full_page=True)
        print("截图：%s" % path, file=sys.stderr)
    except Exception as exc:  # 截图失败不阻断主流程
        print("截图失败(%s)：%s" % (name, exc), file=sys.stderr)


def cmd_login(args):
    if not _require_playwright():
        return 2
    from playwright.sync_api import sync_playwright
    os.makedirs(os.path.dirname(os.path.abspath(args.state)), exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(MP_HOME)
        print("请在浏览器中用管理员/运营者微信扫码登录（%d 秒内）…" % args.timeout,
              file=sys.stderr)
        deadline = time.time() + args.timeout
        while time.time() < deadline:
            if _logged_in(page):
                break
            time.sleep(2)
        if not _logged_in(page):
            print("超时未登录成功，未保存登录态。", file=sys.stderr)
            browser.close()
            return 1
        context.storage_state(path=args.state)
        _secure_state(args.state)
        _shot(page, os.path.dirname(os.path.abspath(args.state)), "login-ok")
        print(json.dumps({"status": "login-saved", "state": args.state},
                         ensure_ascii=False))
        browser.close()
        return 0


def cmd_publish(args):
    if not _require_playwright():
        return 2
    if not os.path.exists(args.state):
        print("登录态不存在：%s\n先执行 login 子命令扫码保存。" % args.state,
              file=sys.stderr)
        return 2
    from playwright.sync_api import sync_playwright
    state_dir = os.path.dirname(os.path.abspath(args.state))
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(storage_state=args.state)
        page = context.new_page()
        page.goto(MP_HOME)
        page.wait_for_load_state("networkidle")
        if not _logged_in(page):
            print("登录态已失效：请重新执行 login 子命令扫码。", file=sys.stderr)
            _shot(page, state_dir, "login-expired")
            browser.close()
            return 3
        # 进草稿箱：语义化点击（DOM 改版时按 browser-playbook.md 人工走）
        try:
            page.get_by_text("草稿", exact=False).first.click(timeout=8000)
        except Exception:
            page.goto("https://mp.weixin.qq.com/cgi-bin/appmsg"
                      "?t=media/appmsg_list&lang=zh_CN")
        page.wait_for_load_state("networkidle")
        _shot(page, state_dir, "draft-list")

        # 找目标标题
        try:
            row = page.get_by_text(args.title, exact=False).first
            row.scroll_into_view_if_needed(timeout=8000)
            row.hover(timeout=8000)
        except Exception as exc:
            print("未找到标题为 %r 的草稿：%s" % (args.title, exc), file=sys.stderr)
            _shot(page, state_dir, "draft-not-found")
            browser.close()
            return 4

        # 点该行的「发表」（hover 后出现的操作按钮）
        published = False
        for label in ("发表", "群发"):
            try:
                btn = row.locator(
                    "xpath=ancestor-or-self::*[.//text()=%r]"
                    "//*[@role='button' or self::a or self::button]"
                    "[.//text()=%r or @aria-label=%r]"
                    % (args.title, label, label)).first
                btn.click(timeout=4000)
                published = True
                break
            except Exception:
                continue
        if not published:
            print("自动定位「发表」按钮失败（DOM 可能改版）。"
                  "截图已存 state/logs/，请按 browser-playbook.md 人工完成最后一步，"
                  "并更新本脚本选择器。", file=sys.stderr)
            _shot(page, state_dir, "publish-btn-not-found")
            browser.close()
            return 5
        _shot(page, state_dir, "publish-clicked")

        # 确认弹窗（出现「发表/确定」类按钮就点；不确定时截图留证）
        time.sleep(1.5)
        for label in ("发表", "确定", "确认"):
            try:
                page.get_by_role("button", name=label).last.click(timeout=3000)
                break
            except Exception:
                continue
        page.wait_for_timeout(3000)
        _shot(page, state_dir, "publish-result")
        # 保存最新登录态（后台会续期）
        context.storage_state(path=args.state)
        _secure_state(args.state)
        print(json.dumps({"status": "publish-clicked", "title": args.title,
                          "note": "以 state/logs/ 截图为准核实发表结果"},
                         ensure_ascii=False))
        browser.close()
        return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="微信公众平台草稿箱浏览器发布（方案 B，需 playwright）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_login = sub.add_parser("login", help="扫码登录并保存登录态")
    p_login.add_argument("--state", default=DEFAULT_STATE)
    p_login.add_argument("--timeout", type=int, default=180,
                         help="等待扫码秒数（默认 180）")
    p_login.set_defaults(fn=cmd_login)

    p_pub = sub.add_parser("publish", help="把指定标题的草稿点发表")
    p_pub.add_argument("--title", required=True, help="草稿标题（模糊匹配）")
    p_pub.add_argument("--state", default=DEFAULT_STATE)
    p_pub.add_argument("--headless", action="store_true",
                       help="无头模式（默认有头，便于观察）")
    p_pub.set_defaults(fn=cmd_publish)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
