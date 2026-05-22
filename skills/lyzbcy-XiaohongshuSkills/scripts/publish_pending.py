#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""使用 runtime/input 中的待发布标题和正文发布小红书图文。"""

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
RUNTIME_INPUT_DIR = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "runtime", "input"))
DEFAULT_TITLE_FILE = os.path.join(RUNTIME_INPUT_DIR, "xhs_title.txt")
DEFAULT_CONTENT_FILE = os.path.join(RUNTIME_INPUT_DIR, "xhs_content.txt")


def build_publish_command(args):
    cmd = [
        sys.executable,
        os.path.join(SCRIPT_DIR, "publish.py"),
        "--title-file",
        args.title_file,
        "--content-file",
        args.content_file,
    ]

    if args.images:
        cmd.extend(["--images", *args.images])
    elif args.image_urls:
        cmd.extend(["--image-urls", *args.image_urls])

    if args.preview:
        cmd.append("--preview")
    if args.headless:
        cmd.append("--headless")
    if args.skip_file_check:
        cmd.append("--skip-file-check")
    if args.account:
        cmd.extend(["--account", args.account])
    if args.port:
        cmd.extend(["--port", str(args.port)])

    return cmd


def ensure_file_exists(path, label):
    if os.path.isfile(path):
        return
    print(f"错误: 未找到{label}: {path}", file=sys.stderr)
    sys.exit(2)


def main():
    parser = argparse.ArgumentParser(description="发布 runtime/input 中已准备好的小红书图文草稿")
    parser.add_argument("--title-file", default=DEFAULT_TITLE_FILE, help="标题文件路径")
    parser.add_argument("--content-file", default=DEFAULT_CONTENT_FILE, help="正文文件路径")
    parser.add_argument("--images", nargs="+", help="本地图片路径")
    parser.add_argument("--image-urls", nargs="+", help="图片 URL")
    parser.add_argument("--preview", action="store_true", help="预览模式")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--skip-file-check", action="store_true", help="跳过文件检查")
    parser.add_argument("--account", help="账号名称")
    parser.add_argument("--port", type=int, default=9222, help="CDP 端口")

    args = parser.parse_args()

    ensure_file_exists(args.title_file, "标题文件")
    ensure_file_exists(args.content_file, "正文文件")

    if not (args.images or args.image_urls):
        print("错误: 必须提供 --images 或 --image-urls", file=sys.stderr)
        sys.exit(2)

    cmd = build_publish_command(args)
    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()