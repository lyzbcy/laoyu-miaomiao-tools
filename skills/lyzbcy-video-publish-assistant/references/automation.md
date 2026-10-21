# 执行与断点

脚本仅使用现有登录浏览器和真实页面控件，不用私有投稿API，不下载浏览器或模型。同一任务一个session，四平台串行；换视频换run-dir。CLI默认只准备，`mode: prepare`本身不授权公开。

```powershell
python scripts/prepare_upload.py /project/upload-manifest.json --output /project/preflight.json
python scripts/publish.py /project/upload-manifest.json --platform douyin --session video-task --run-dir /project/run --step open
python scripts/publish.py /project/upload-manifest.json --platform douyin --session video-task --run-dir /project/run --step prepare
```

顺序：upload → text → declaration → topics → settings → covers → save → reopen → verify。YouTube在保存前额外检查版权/转码。正常运行只输出绿灯摘要；黄灯保存pending断点并退避，红灯一份诊断后停止。恢复同一命令会跳过done步骤，不清空视频input测试上传。

封面画布/缩略图变更已检测后，Agent按每种比例看一次实际预览，再执行：

```powershell
python scripts/publish.py /project/upload-manifest.json --platform douyin --session video-task --run-dir /project/run --step review-covers --evidence /project/run/douyin-cover-3x4.jpg
```

## manifest

```json
{
  "video":"final.mp4", "video_sha256":"actual-sha256",
  "covers":{"4:3":"cover43.jpg","3:4":"cover34.jpg","16:9":"cover169.jpg"},
  "mode":"prepare",
  "platforms":{
    "bilibili":{"title":"标题","description":"简介","topics":["AI编程"],"activity_topics":["已选定的一个活动话题"]},
    "youtube":{"title":"标题","description":"说明","topics":["Animation"],"made_for_kids":false,"ai_disclosure":false,"category":"科学和技术","language":"zh-Hans","visibility":"private"}
  }
}
```

`activity_topics`可省略，最多一个。遇活动专用错误时走活动选择并回读，不能把该词改成普通字符串后声称成功；第二个受限词明确记入omitted。活动选择DOM未出现或不唯一即红灯，不能猜候选。

YouTube `context`读取当前AI问句，内容判断先于 `declaration`；普通合成旁白或卡通不自动等同逼真误导修改。Shorts/普通视频以页面实际类型、视频ID及缩略图比例判断。

## 用户授权的正式发布

```powershell
python scripts/publish.py /project/upload-manifest.json --platform youtube --session video-task --run-dir /project/run --step review-plan
python scripts/publish.py /project/upload-manifest.json --platform youtube --session video-task --run-dir /project/run --step submit --authorization /project/authorization.json
python scripts/publish.py /project/upload-manifest.json --platform youtube --session video-task --run-dir /project/run --step confirm
```

`review-plan`只生成未批准的模板。用户授权已在当前会话明确给出且具体成片/文案/封面已可审时，可记录该授权；否则给出实际预览后询问。不要把过往影片的同意迁移到新片。

```json
{"approved":true,"platforms":{"youtube":{"review_fingerprint":"review-plan返回值","visibility":"public"}}}
```

指纹覆盖当前视频哈希、该平台文案和全部封面哈希，改任一项即失效。草稿核验和封面验收未绿不提交；点击前记录submission_attempted。不明结果续查confirm；即使指令重试也不重复点击。`submitted`只证明受理，`published/public`需对应终态证据。

## 改动与诊断

确认用户在编辑后将state的`human_takeover`设true；禁止继续text/topics/prepare覆盖，读当前现场并保留其字段。换文案会使旧核验失效，不能拿旧manifest恢复现场。封面检查证据单独按指纹保存，普通inspect不覆盖它。

定位变化只修当前适配/本地profiles后单步继续。页面被关闭或登录失效只报当前平台红灯，不新建相同投稿。转码黄灯不采屏、不重新上传；跨平台继续独立工作。
