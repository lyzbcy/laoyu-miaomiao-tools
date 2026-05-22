#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""小红书浏览器管理入口。"""

import argparse
import os
import subprocess
import sys

import requests


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

    result = subprocess.run(cmd, capture_output=False, text=True)
    return result.returncode == 0


def check_browser_status(port=9222):
    try:
        response = requests.get(f"http://127.0.0.1:{port}/json", timeout=2)
        if response.status_code == 200:
            return True, len(response.json())
    except Exception:
        pass
    return False, 0


def main():
    parser = argparse.ArgumentParser(description="小红书浏览器管理脚本")
    parser.add_argument("action", choices=["start", "kill", "status", "restart"], help="操作")
    parser.add_argument("--port", type=int, default=9222, help="CDP 端口")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--account", help="账号名称")
    args = parser.parse_args()

    if args.action == "status":
        is_running, page_count = check_browser_status(args.port)
        if is_running:
            print(f"✓ 浏览器运行中 (端口 {args.port}, {page_count} 个页面)")
        else:
            print(f"✗ 浏览器未运行 (端口 {args.port})")
        return

    print(f"{args.action} 浏览器 (端口 {args.port})...")
    ok = run_chrome_launcher(args.action, port=args.port, headless=args.headless, account=args.account)
    if not ok:
        print(f"✗ 浏览器{args.action}失败")
        sys.exit(1)
    print(f"✓ 浏览器{args.action}完成")


if __name__ == "__main__":
    main()
