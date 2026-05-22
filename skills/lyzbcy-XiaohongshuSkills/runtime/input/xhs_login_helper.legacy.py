import asyncio
import websockets
import json

async def send_login_code():
    # 获取可用的页面
    import requests
    resp = requests.get('http://127.0.0.1:9222/json')
    pages = resp.json()
    
    # 找到小红书登录页
    ws_url = None
    for page in pages:
        if 'xiaohongshu' in page.get('url', ''):
            ws_url = page['webSocketDebuggerUrl']
            break
    
    if not ws_url:
        print('找不到小红书页面')
        return
    
    print(f'连接到: {ws_url}')
    
    async with websockets.connect(ws_url) as ws:
        msg_id = 1
        
        # 点击发送验证码按钮
        expression = """
        // 找到发送验证码按钮
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
            // 尝试其他选择器
            sendBtn = document.querySelector('.send-code-btn') || document.querySelector('[class*="code"]');
            if (sendBtn) {
                sendBtn.click();
                '已点击发送验证码';
            } else {
                '找不到发送验证码按钮';
            }
        }
        """
        
        cmd = {
            'id': msg_id,
            'method': 'Runtime.evaluate',
            'params': {'expression': expression}
        }
        await ws.send(json.dumps(cmd))
        response = await ws.recv()
        print('点击发送验证码结果:', response)

asyncio.run(send_login_code())
