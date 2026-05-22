#!/usr/bin/env python3
"""
浏览器回复执行脚本
支持：平台配置、dry-run、发送日志
"""
import argparse, json, shlex, subprocess, sys, time
from pathlib import Path
from datetime import datetime

# 获取脚本所在目录
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent


def run(cmd: str, dry_run: bool = False):
    """执行命令"""
    print(f"$ {cmd}")
    if not dry_run:
        subprocess.run(cmd, shell=True, check=True)


def load_config() -> dict:
    """加载全局配置"""
    config_path = SKILL_DIR / "config.json"
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {"dryRunByDefault": True, "maxRepliesPerRun": 50}


def load_platform_profile(platform: str) -> dict:
    """加载平台配置"""
    profile_path = SKILL_DIR / "profiles" / f"{platform}.json"
    if profile_path.exists():
        return json.loads(profile_path.read_text(encoding="utf-8"))
    return {}


def main():
    p = argparse.ArgumentParser(description="通过浏览器自动回复评论")
    p.add_argument("drafts_json", help="回复草稿 JSON 文件")
    p.add_argument("--platform", default="douyin", help="平台名称 (douyin/xiaohongshu)")
    p.add_argument("--session-name", default=None, help="浏览器会话名称")
    p.add_argument("--max-replies", type=int, default=None, help="最大回复数量")
    p.add_argument("--force-review", action="store_true", help="强制审核模式")
    p.add_argument("--dry-run", action="store_true", help="试运行模式")
    p.add_argument("--wait-ms", type=int, default=1200, help="回复间隔(毫秒)")
    p.add_argument("--browser-cmd", default="npx -y agent-browser", help="浏览器命令")
    args = p.parse_args()

    # 加载配置
    config = load_config()
    profile = load_platform_profile(args.platform)

    # 合并参数
    dry_run = args.dry_run or config.get("dryRunByDefault", False)
    max_replies = args.max_replies or config.get("maxRepliesPerRun", 50)
    wait_ms = args.wait_ms or profile.get("rateLimit", {}).get("delayBetweenReplies", 1200)
    session_name = args.session_name or profile.get("sessionProfile", f"{args.platform}-comment")

    # 加载草稿
    drafts = json.loads(Path(args.drafts_json).read_text(encoding="utf-8"))

    # 筛选可发送的回复
    sendable = []
    for item in drafts:
        action = item.get("suggested_action", "")
        if action in {"public_reply", "public_reply_plus_dm"}:
            sendable.append(item)
        elif action == "public_reply_review" and args.force_review:
            sendable.append(item)

    sendable = sendable[:max_replies]
    print(f"📋 加载 {len(sendable)} 条待发送回复")
    if not sendable:
        print("没有需要发送的回复")
        return

    if dry_run:
        print("⚠️  试运行模式 (dry-run)，不会实际发送")

    # 打开评论管理页面
    comment_url = profile.get("commentUrl", f"https://creator.{args.platform}.com/comment/manage")
    run(f"{args.browser_cmd} --session-name {shlex.quote(session_name)} open {shlex.quote(comment_url)}", dry_run)
    run(f"{args.browser_cmd} --session-name {shlex.quote(session_name)} wait --load networkidle", dry_run)

    # 执行回复
    log = []
    selectors = profile.get("selectors", {})
    reply_box = selectors.get("replyBox", "textarea")
    submit_btn = selectors.get("submitButton", "button[type=submit]")

    for idx, item in enumerate(sendable, 1):
        reply = item.get("public_reply", "").strip()
        if not reply:
            continue

        print(f"\n[{idx}/{len(sendable)}] 回复: {item.get('comment', '')[:30]}...")

        fill_cmd = f'{args.browser_cmd} --session-name {shlex.quote(session_name)} fill {shlex.quote(reply_box)} {shlex.quote(reply)}'
        click_cmd = f'{args.browser_cmd} --session-name {shlex.quote(session_name)} click {shlex.quote(submit_btn)}'

        if dry_run:
            print(f"  [dry-run] {fill_cmd}")
            print(f"  [dry-run] {click_cmd}")
        else:
            run(fill_cmd)
            run(click_cmd)
            time.sleep(wait_ms / 1000)

        log.append({
            "timestamp": datetime.now().isoformat(),
            "platform": args.platform,
            "comment": item.get("comment", ""),
            "reply": reply,
            "intent": item.get("intent"),
            "dry_run": dry_run,
        })

    # 保存日志
    out = Path(args.drafts_json).with_suffix(".sent-log.json")
    out.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ 发送日志: {out}")
    print(f"✓ 共处理 {len(log)} 条回复")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败: {e}", file=sys.stderr)
        sys.exit(e.returncode or 1)
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
        sys.exit(1)
