#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json

import requests
import websockets


async def send_login_code():
    response = requests.get("http://127.0.0.1:9222/json", timeout=5)
    pages = response.json()

    ws_url = None
    for page in pages:
        if "xiaohongshu" in page.get("url", ""):
            ws_url = page.get("webSocketDebuggerUrl")
            break

    if not ws_url:
        raise RuntimeError("找不到小红书页面")

    async with websockets.connect(ws_url) as ws:
        expression = """
        let buttons = document.querySelectorAll('button');
        let sendBtn = null;
        for (let btn of buttons) {
            if (btn.textContent.includes('发送验证码') || btn.textContent.includes('获取验证码')) {
                sendBtn = btn;
                break;
            }
        }
        if (sendBtn) {
            sendBtn.click();
            '已点击发送验证码';
        } else {
            sendBtn = document.querySelector('.send-code-btn') || document.querySelector('[class*="code"]');
            if (sendBtn) {
                sendBtn.click();
                '已点击发送验证码';
            } else {
                '找不到发送验证码按钮';
            }
        }
        """
        await ws.send(json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": expression},
        }))
        print(await ws.recv())


if __name__ == "__main__":
    asyncio.run(send_login_code())
