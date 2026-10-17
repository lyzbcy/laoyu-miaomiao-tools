# 脚本工作流

维护入口`publish.py`；`browser.py`封装唯一临时UTF-8请求体、桥接错误、可信鼠标键盘、可见控件、真实文件input和截图；`profiles.json`维护平台选择器。只操作网页，不使用私有投稿API。

## 执行

依赖Python3.10+、curl（Windows为curl.exe）、已连接的Kimi扩展与用户登录浏览器。不下载另一个浏览器或模型。下面路径替换为当前任务路径，命令从skill目录执行。

```powershell
python -X utf8 scripts/prepare_upload.py /project/upload-manifest.json --output /project/preflight.json
python -X utf8 scripts/publish.py /project/upload-manifest.json --platform youtube --session video-project --run-dir /project/publish-run --step open
python -X utf8 scripts/publish.py /project/upload-manifest.json --platform youtube --session video-project --run-dir /project/publish-run --step inspect
python -X utf8 scripts/publish.py /project/upload-manifest.json --platform youtube --session video-project --run-dir /project/publish-run --step prepare
```

平台键：`douyin`、`bilibili`、`xiaohongshu`、`youtube`。同任务所有平台复用session；每次选回对应任务页，不借用无关标签。`open`只在本session没有该平台时开新页。

步骤：`upload → text → declaration → topics → settings → covers → save → reopen → verify`。可单步执行；`status`读断点。`prepare`遇到封面检查点或实际错误就停，已确认步骤不重做。检查封面截图后：

```powershell
python -X utf8 scripts/publish.py /project/upload-manifest.json --platform youtube --session video-project --run-dir /project/publish-run --step review-covers --evidence /project/publish-run/youtube-cover-preview.jpg
python -X utf8 scripts/publish.py /project/upload-manifest.json --platform youtube --session video-project --run-dir /project/publish-run --step prepare
```

通过其他浏览器工具完成某步时，记录实际操作与截图，不虚构该步已经由脚本执行。旧快照不能作为当前页面证据。

## Manifest

兼容v1.0的`video`、`covers`、`platforms`与`mode: prepare`。相对路径相对manifest解析。可选`video_sha256`锁定成片。标题限长抖音30/B站80/小红书20/YouTube100，仍以现场为准。

```json
{
  "video":"final.mp4",
  "covers":{"4:3":"cover43.jpg","3:4":"cover34.jpg","16:9":"cover169.jpg"},
  "mode":"prepare",
  "platforms":{
    "youtube":{
      "title":"作品标题","description":"说明与实际歌曲来源",
      "topics":["作品主题","Animation"],
      "made_for_kids":false,"ai_disclosure":true,
      "category":"音乐","language":"zh-Hans","visibility":"private"
    }
  }
}
```

`made_for_kids`按实际受众判断，不能仅因卡通角色就设儿童向。`ai_disclosure`须先读当前Studio问句；“AI使用情况”和“逼真内容修改”不可盲目同选。`edit_url`只记录页面已展示的对应稿件链接。

## 恢复与维护

- `*-state.json`绑定视频哈希、文案哈希和session。换视频用新run-dir；改文案会清除旧填表结果。
- 文件写入前记录`upload_attempted`。出现不确定响应，先`inspect`检查进度、标题、时长、草稿，不自动清空或重传。确认从未选入文件后可留证修复状态。
- `--profiles /project/selector-overrides.json`局部覆盖定位，选择器由当前DOM观察获得。默认profile不放账号、稿件ID、本次`@e`号、tabId或绝对路径。
- 失败留存JSON和JPG；结束关闭焦点模拟，保持任务标签给用户审核，不关闭session。
- 富文本必须回读；话题必须选准确候选。B站正确视频input位于`.bcc-upload-wrapper`内，不能用另一个`buploader`。小红书草稿保存在当前浏览器本地。
- `settings`不擅自替国内平台选择分区；最终检查后按当前内容选择实际分区。YouTube的类别/语言从manifest读取。
- 新平台须增加profile、适配步骤和现场保存回读证据后才称“支持”。微信视频号、快手是后续建议；微博可补传播。横版MV可发YouTube常规视频，Shorts/TikTok/Reels需另做竖版排版。
