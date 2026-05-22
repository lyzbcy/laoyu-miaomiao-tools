import asyncio
import websockets
import json
import requests
import base64

async def get_home_qrcode():
    # 获取可用的页面
    resp = requests.get('http://127.0.0.1:9222/json')
    pages = resp.json()
    
    # 找到小红书页面或创建新页面
    ws_url = None
    page_id = None
    for page in pages:
        if 'xiaohongshu' in page.get('url', ''):
            ws_url = page['webSocketDebuggerUrl']
            page_id = page['id']
            break
    
    if not ws_url and pages:
        # 使用第一个页面
        ws_url = pages[0]['webSocketDebuggerUrl']
        page_id = pages[0]['id']
    
    print(f'连接到: {ws_url}')
    
    async with websockets.connect(ws_url) as ws:
        msg_id = 1
        
        # 导航到小红书主页
        cmd = {
            'id': msg_id,
            'method': 'Page.navigate',
            'params': {'url': 'https://www.xiaohongshu.com'}
        }
        await ws.send(json.dumps(cmd))
        response = await ws.recv()
        print('导航结果:', response)
        
        # 等待页面加载
        await asyncio.sleep(3)
        
        # 获取二维码图片
        msg_id += 1
        expression = """
        let qrImg = document.querySelector('img[src*="qr"]');
        if (qrImg) {
            qrImg.src;
        } else {
            // 尝试找其他二维码
            let imgs = document.querySelectorAll('img');
            for (let img of imgs) {
                if (img.src && (img.src.includes('qr') || img.width > 100)) {
                    img.src;
                }
            }
            'no_qr';
        }
        """
        cmd = {
            'id': msg_id,
            'method': 'Runtime.evaluate',
            'params': {'expression': expression}
        }
        await ws.send(json.dumps(cmd))
        response = await ws.recv()
        print('二维码结果:', response)
        
        # 截图
        msg_id += 1
        cmd = {
            'id': msg_id,
            'method': 'Page.captureScreenshot',
            'params': {'format': 'png'}
        }
        await ws.send(json.dumps(cmd))
        response = await ws.recv()
        result = json.loads(response)
        
        if 'result' in result and 'data' in result['result']:
            img_data = base64.b64decode(result['result']['data'])
            with open(r'C:\Users\24676\.openclaw\workspace\screenshots\xhs_home_page.png', 'wb') as f:
                f.write(img_data)
            print('截图已保存到: C:\\Users\\24676\\.openclaw\\workspace\\screenshots\\xhs_home_page.png')

asyncio.run(get_home_qrcode())
