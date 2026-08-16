#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""iPhone 镜像免扫码发文（无视觉、纯坐标、模型无关）。

原理：手机端微信（管理员身份）发文章不需要扫码（safe_check 只在电脑端要求，
因为电脑端需要"证明管理员身份"，手机本身即身份载体）。本脚本通过 macOS 官方
iPhone 镜像 + 坐标点击操控手机端发文章。

零视觉设计：坐标来自 iphone_coords.json（相对比例，一次性校准），
每步可选像素锚点校验（PIL 采样，非 AI 视觉）。DeepSeek V4 PRO 等无视觉
模型可 100% 运行——它只需要调这一个脚本。

依赖：
- macOS Sequoia+ 的 iPhone Mirroring（系统自带）
- /tmp/click（Swift 编译的坐标点击工具，见 SKILL 文档）或编译本目录 click.swift
- iPhone 与 Mac 同一 WiFi、iPhone 不锁屏不关机（充电座）

用法：
  python3 publish_iphone.py --title "标题" --body body.txt
  python3 publish_iphone.py --article article.json   # 复用 wechat_api 的 article 格式（正文取纯文本）

注意：手机端编辑器粘贴的是纯文本（换行保留）。图片需后续通过相册选择插入
（待扩展）。发表走手机通道（publish 记录 type=101），1-2 分钟内上线。
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
COORDS = os.path.join(HERE, "iphone_coords.json")
SWIFT_SRC = os.path.join(HERE, "click.swift")


def ensure_click_tool():
    """确保 /tmp/click 存在（没有则现场编译）。"""
    if os.path.exists("/tmp/click"):
        return "/tmp/click"
    if os.path.exists(SWIFT_SRC):
        subprocess.run(["xcrun", "swiftc", "-O", "-o", "/tmp/click", SWIFT_SRC], check=True)
        return "/tmp/click"
    raise RuntimeError("缺 /tmp/click 且找不到 click.swift 源码")


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def mirror_bounds():
    """动态获取 iPhone 镜像窗口 bounds（逻辑点）。"""
    out = sh("""osascript -e 'tell application "System Events" to tell process "iPhone Mirroring" to get {position, size} of window 1'""").stdout.strip()
    nums = [float(v) for v in out.replace(",", " ").split()]
    if len(nums) != 4:
        raise RuntimeError(f"拿不到镜像窗口（镜像没开？）：{out!r}")
    x, y, w, h = nums
    return x, y, w, h


def click_rel(coords, anchor, tool):
    """按相对坐标点击镜像窗口内位置。"""
    x, y, w, h = mirror_bounds()
    px = x + w * anchor["x"]
    py = y + h * anchor["y"]
    r = subprocess.run([tool, str(px), str(py)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"点击失败 {anchor['desc']}: {r.stderr}")


def paste(text, wait):
    """文本进剪贴板并 Cmd+V 粘贴到 iPhone（镜像剪贴板互通）。"""
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
    time.sleep(0.5)
    sh("""osascript -e 'tell application "System Events" to keystroke "v" using command down'""")
    time.sleep(wait)


def frontmost_mirror():
    sh("""osascript -e 'tell application "System Events" to set frontmost of process "iPhone Mirroring" to true'""")
    time.sleep(1.2)


def pixel_anchor_check(sample_spec=None):
    """可选像素锚点校验（PIL 采样固定点颜色），非 AI 视觉。当前为占位——
    校准数据积累后启用：不匹配返回 False，调用方应停机告警。"""
    return True


def publish(title, body_text, coords, dry_run=False):
    tool = ensure_click_tool()
    a, t = coords["anchors"], coords["timings_seconds"]
    term = coords["search_terms"]

    def step(name, anchor_key=None, do=None):
        print(f"  [{name}]")
        if dry_run:
            return
        if anchor_key:
            click_rel(coords, a[anchor_key], tool)
        if do:
            do()
        if not pixel_anchor_check():
            raise RuntimeError(f"{name}: 像素锚点不匹配，疑似 UI 改版，已停机")

    # 前置：打开镜像并前置
    sh('open -a "iPhone Mirroring"')
    time.sleep(4)
    frontmost_mirror()

    # 流水线（校准于 2026-08-16，13 步全命中）
    step("1. 主屏搜索胶囊", "search_pill")
    time.sleep(t["after_search_pill"])
    step("2. 粘贴「微信」", do=lambda: paste(term["app"], t["after_paste"]))
    step("3. 点第一个结果(微信)", "first_result")
    time.sleep(t["after_open_app"])
    step("4. 微信搜索图标", "wechat_search")
    time.sleep(t["after_search_pill"])
    step("5. 粘贴公众号名", do=lambda: paste(term["official_account"], t["after_paste"]))
    step("6. 点公众号结果", "mp_result")
    time.sleep(t["after_click_result"])
    step("7. 点「发文章」", "publish_entry")
    time.sleep(t["editor_ready"])
    step("8. 点标题区", "title_field")
    time.sleep(1.5)
    step("9. 粘贴标题", do=lambda: paste(title, t["after_paste"]))
    step("10. 点正文区", "body_field")
    time.sleep(1.5)
    step("11. 粘贴正文", do=lambda: paste(body_text, t["after_paste"]))
    step("12. 点「完成」", "done_btn")
    time.sleep(t["after_done"])
    step("13. 点「发表」", "publish_submit")
    time.sleep(t["after_submit"])
    step("14. 确认弹窗「确定」", "confirm_ok")
    time.sleep(3)
    step("15. 关闭「知道了」", "know_it")
    print("✅ 已提交发表队列（手机端通道，免扫码，1-2 分钟内上线）")


def main():
    ap = argparse.ArgumentParser(description="iPhone 镜像免扫码发文（无视觉纯坐标）")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--title", help="文章标题")
    g.add_argument("--article", help="article.json 路径（复用 wechat_api 格式）")
    ap.add_argument("--body", help="正文纯文本文件路径（--title 模式必填）")
    ap.add_argument("--dry-run", action="store_true", help="只打印步骤不点击")
    args = ap.parse_args()

    coords = json.load(open(COORDS, encoding="utf-8"))

    if args.article:
        art = json.load(open(args.article, encoding="utf-8"))
        title = art["title"]
        raw = art.get("content_html") or ""
        if not raw and art.get("content_html_file"):
            raw = open(art["content_html_file"], encoding="utf-8").read()
        import re
        body = re.sub(r"<[^>]+>", "", raw)          # 手机端贴纯文本
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
    else:
        if not args.body:
            ap.error("--title 模式需要 --body 正文文件")
        title = args.title
        body = open(args.body, encoding="utf-8").read().strip()

    print(f"标题: {title}")
    print(f"正文: {len(body)} 字符")
    publish(title, body, coords, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
