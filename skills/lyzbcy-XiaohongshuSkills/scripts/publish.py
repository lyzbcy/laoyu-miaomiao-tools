#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""小红书发布封装入口。"""

import argparse
import os
import subprocess
import sys


if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_chrome_launcher(action, port=9222, headless=False, account=None):
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, "chrome_launcher.py")]

    if action == "start":
        if headless:
            cmd.append("--headless")
        if account:
            cmd.extend(["--account", account])
        cmd.extend(["--port", str(port)])
    elif action == "kill":
        cmd.append("--kill")
        cmd.extend(["--port", str(port)])
    elif action == "restart":
        cmd.append("--restart")
        if headless:
            cmd.append("--headless")
        if account:
            cmd.extend(["--account", account])
        cmd.extend(["--port", str(port)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def run_publish(args):
    try:
        print("[xhs-publish] Step 1: 启动 Chrome...")
        if not run_chrome_launcher("start", port=args.port, headless=args.headless, account=args.account):
            print("错误: Chrome 启动失败", file=sys.stderr)
            return 2

        print("[xhs-publish] Step 2: 执行发布...")
        cmd = [sys.executable, os.path.join(SCRIPT_DIR, "publish_pipeline.py")]
        cmd.extend(["--port", str(args.port)])

        if args.headless:
            cmd.append("--headless")
        if args.account:
            cmd.extend(["--account", args.account])
        if args.title_file:
            cmd.extend(["--title-file", args.title_file])
        elif args.title:
            cmd.extend(["--title", args.title])
        if args.content_file:
            cmd.extend(["--content-file", args.content_file])
        elif args.content:
            cmd.extend(["--content", args.content])
        if args.images:
            cmd.extend(["--images", *args.images])
        elif args.image_urls:
            cmd.extend(["--image-urls", *args.image_urls])
        elif args.video:
            cmd.extend(["--video", args.video])
        elif args.video_url:
            cmd.extend(["--video-url", args.video_url])
        if args.preview:
            cmd.append("--preview")
        if args.skip_file_check:
            cmd.append("--skip-file-check")

        result = subprocess.run(cmd)
        return result.returncode
    finally:
        print("[xhs-publish] Step 3: 关闭 Chrome...")
        run_chrome_launcher("kill", port=args.port)


def main():
    parser = argparse.ArgumentParser(description="小红书发布封装脚本")
    parser.add_argument("--title", help="笔记标题")
    parser.add_argument("--title-file", help="从文件读取标题")
    parser.add_argument("--content", help="笔记正文")
    parser.add_argument("--content-file", help="从文件读取正文")
    parser.add_argument("--images", nargs="+", help="本地图片路径")
    parser.add_argument("--image-urls", nargs="+", help="图片 URL")
    parser.add_argument("--video", help="本地视频路径")
    parser.add_argument("--video-url", help="视频 URL")
    parser.add_argument("--preview", action="store_true", help="预览模式")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--port", type=int, default=9222, help="CDP 端口")
    parser.add_argument("--account", help="账号名称")
    parser.add_argument("--skip-file-check", action="store_true", help="跳过文件检查")

    args = parser.parse_args()

    if not args.title and not args.title_file:
        print("错误: 必须提供 --title 或 --title-file", file=sys.stderr)
        sys.exit(2)
    if not args.content and not args.content_file:
        print("错误: 必须提供 --content 或 --content-file", file=sys.stderr)
        sys.exit(2)
    if not (args.images or args.image_urls or args.video or args.video_url):
        print("错误: 必须提供图片或视频", file=sys.stderr)
        sys.exit(2)

    sys.exit(run_publish(args))


if __name__ == "__main__":
    main()
