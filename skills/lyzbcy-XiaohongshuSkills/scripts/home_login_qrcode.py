#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import base64
import json
from pathlib import Path

import requests
import websockets


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
QRCODE_DIR = SKILL_DIR / "runtime" / "qrcode"
SCREENSHOT_DIR = SKILL_DIR / "runtime" / "screenshots"


async def get_home_qrcode():
    response = requests.get("http://127.0.0.1:9222/json", timeout=5)
    pages = response.json()

    ws_url = None
    for page in pages:
        if "xiaohongshu" in page.get("url", ""):
            ws_url = page.get("webSocketDebuggerUrl")
            break

    if not ws_url and pages:
        ws_url = pages[0].get("webSocketDebuggerUrl")

    if not ws_url:
        raise RuntimeError("找不到可用的小红书页面")

    QRCODE_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    async with websockets.connect(ws_url) as ws:
        msg_id = 1

        await ws.send(json.dumps({
            "id": msg_id,
            "method": "Page.navigate",
            "params": {"url": "https://www.xiaohongshu.com"},
        }))
        await ws.recv()

        await asyncio.sleep(3)

        msg_id += 1
        await ws.send(json.dumps({
            "id": msg_id,
            "method": "Page.captureScreenshot",
            "params": {"format": "png"},
        }))
        response = json.loads(await ws.recv())
        image_base64 = response.get("result", {}).get("data")
        if not image_base64:
            raise RuntimeError("截图失败")

        screenshot_path = SCREENSHOT_DIR / "xhs_home_page.png"
        screenshot_path.write_bytes(base64.b64decode(image_base64))

        qrcode_path = QRCODE_DIR / "xhs_login_qrcode.png"
        qrcode_path.write_bytes(base64.b64decode(image_base64))

        print(f"截图已保存到: {screenshot_path}")
        print(f"二维码占位图已保存到: {qrcode_path}")


if __name__ == "__main__":
    asyncio.run(get_home_qrcode())
