#!/usr/bin/env python3
"""首次登录:打开通知页等待扫码,轮询检测登录成功。二维码截图存 login-qr.png 供用户扫描。
用法: xvfb-run -a python3 login_once.py
截图会随轮询每30s刷新(二维码会过期),需及时把图发给用户手机扫。"""
import asyncio
import sys
from pathlib import Path

from xhs_reply import PROFILE_DIR, XHS_URL, check_login

QR_PNG = Path(__file__).resolve().parent / "login-qr.png"


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR), headless=False,
            args=["--no-first-run", "--no-default-browser-check", "--disable-gpu"],
            viewport={"width": 1280, "height": 900})
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.goto(XHS_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        if await check_login(page):
            print("ALREADY_LOGGED_IN")
            await browser.close()
            return 0
        await page.screenshot(path=str(QR_PNG), full_page=False)
        print(f"QR_SAVED {QR_PNG}")
        for i in range(120):  # 最多等 10 分钟
            await page.wait_for_timeout(5000)
            if await check_login(page):
                print("LOGIN_OK")
                await browser.close()
                return 0
            if i % 6 == 5:  # 每30s刷新二维码截图
                await page.screenshot(path=str(QR_PNG))
                print(f"QR_REFRESHED {(i + 1) // 6}")
        print("LOGIN_TIMEOUT")
        await browser.close()
        return 3


sys.exit(asyncio.run(main()))
