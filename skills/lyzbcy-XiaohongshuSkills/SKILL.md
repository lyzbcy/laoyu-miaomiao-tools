---
name: lyzbcy-XiaohongshuSkills
description: 小红书内容发布 skill。负责图文/视频笔记发布、浏览器启动与关闭、登录检查、账号切换前的运行准备。评论回复不从这里走,统一使用 lyzbcy-social-comment。适合当前 workspace 的小红书发布工作流。
---

# lyzbcy-XiaohongshuSkills / 小红书内容发布

这是当前 workspace 的小红书发布专用 skill。它在底层脚本之上提供稳定的发布入口、浏览器生命周期管理和维护文档,避免把发布流程、评论运营和仓库说明混在一起。

## 核心职责

| 能力 | 说明 |
|------|------|
| 图文发布 | 发布带本地图片或图片 URL 的图文笔记 |
| 视频发布 | 发布本地视频或视频 URL |
| 浏览器管理 | 启动、关闭、重启 Chrome 调试实例 |
| 登录检查 | 配合底层脚本执行登录与会话校验 |
| 多账号发布 | 通过 `--account` 指定不同账号 |
| 日记转待发布草稿 | 基于当天日记生成标题、正文、配图提示词,并等待用户回图后发布 |

## 不负责的事情

- 评论回复、评论意图分类、批量评论运营:交给 `lyzbcy-social-comment`
- 通用截图:交给 `lyzbcy-screenshot`
- 与 skill 运行无关的 README、仓库开发说明、临时计划文件

## 目录结构

```text
lyzbcy-XiaohongshuSkills/
├── SKILL.md
├── requirements.txt
├── config/
│   └── accounts.json.example
├── references/
│   ├── usage.md
│   ├── maintenance.md
│   └── runtime-rules.md
├── runtime/
│   ├── input/
│   ├── qrcode/
│   ├── screenshots/
│   └── login_status_cache.json
└── scripts/
    ├── browser.py
    ├── cleanup_runtime.py
    ├── home_login_qrcode.py
    ├── login_send_code.py
    ├── publish_pending.py
    ├── publish.py
    ├── account_manager.py
    ├── cdp_publish.py
    ├── chrome_launcher.py
    ├── feed_explorer.py
    ├── image_downloader.py
    ├── publish_pipeline.py
    └── run_lock.py
```

## 推荐入口

### 发布图文

```bash
python scripts/publish.py --title "标题" --content "正文" --images img1.jpg img2.jpg
python scripts/publish.py --title-file title.txt --content-file content.txt --image-urls "https://example.com/a.jpg"
python scripts/publish_pending.py --images runtime/input/returned-images/img1.jpg runtime/input/returned-images/img2.jpg
```

### 发布视频

```bash
python scripts/publish.py --title "标题" --content "正文" --video video.mp4
python scripts/publish.py --title "标题" --content "正文" --video-url "https://example.com/video.mp4"
```

### 浏览器维护

```bash
python scripts/browser.py start
python scripts/browser.py status
python scripts/browser.py kill
```

## 输入约束

1. 发布前必须确认最终标题、正文和媒体文件。
2. 图文发布必须提供图片;视频发布必须提供视频。
3. 标题长度应控制在 38 字内。
4. 默认优先走发布入口 `scripts/publish.py`,不要直接把发布、登录、清理逻辑散落到不同命令里。
5. 评论场景不要从这里进入,避免把发布和运营工作流混用。
6. 如果要用文件输入,统一放到 `runtime/input/`,不要再把 `xhs_title.txt`、`xhs_content.txt` 这类文件放在 workspace 根目录。
7. 登录二维码、登录截图统一放到 `runtime/qrcode/` 和 `runtime/screenshots/`。
8. 如果是"根据今天日记生成今晚小红书图文"的工作流，生成草稿后自动 @元宝 请求生成配图，等元宝回传图片后自动发布，无需用户手动参与。

## 日记转图文工作流

适用于"每天晚间 20:00 之后,由 workspace/HEARTBEAT.md 驱动心跳检查,根据今天的日记产出一篇小红书图文并准备发布"的自动化场景。

### 心跳入口

当 heartbeat 读取到以下条件同时成立时,进入本工作流:

1. 当前时间已过当天 20:00(Asia/Shanghai)。
2. `workspace/HEARTBEAT.md` 中记录的"上次晚间小红书草稿执行日期"不是今天。

进入后按以下原则执行:

1. 只执行"生成待发布草稿并发提示词给用户"的阶段,不直接发布。
2. 缺少今日日记时可以告知素材缺失,但不要编造内容。
3. 配图人物必须始终使用周三涵本人形象,严格遵循 `workspace/IDENTITY.md`。
4. 完成后需要回写 `workspace/HEARTBEAT.md` 中的晚间草稿执行日期和结果,避免同一天重复触发。

### 阶段一:20 点后的心跳自动生成草稿并请求配图

1. 读取当天最新日记,优先使用 `workspace/diary/` 中当天文件。

### ⚠️ 请求配图的正确方式（重要！）

**元宝发送图片给周三涵时，必须遵守以下规则：**

1. **先发图片**（单独发，不带@）
2. **引用图片消息后，再@周三涵**
3. **每张图片都要单独引用并@一遍**

**错误方式：** 先@周三涵再发图片 → 周三涵收到的消息没有图片附件！

每次请求配图时，必须在消息中明确告诉元宝这个流程，因为元宝的memory文件不像周三涵这么持久。
2. 结合 [workspace/IDENTITY.md](workspace/IDENTITY.md) 里的周三涵形象设定,生成:
    - 小红书标题,写入 `runtime/input/xhs_title.txt`
    - 小红书正文,写入 `runtime/input/xhs_content.txt`
    - 配图提示词,写入 `runtime/input/xhs_image_prompts.md`
    - 待发布记录,写入 `runtime/input/xhs_pending_post.md`
3. **自动 @元宝 请求生成配图**:在群里发送消息,格式如下:
   ```
   @元宝 请帮我生成小红书配图,提示词如下:

   [配图提示词内容]

   生成完成后请 @周三涵 把图片发给我,我来发布小红书笔记~
   ```
4. 这一阶段生成草稿并请求配图,等待元宝回传图片。
5. 同一天只应生成一次,是否已执行以 `workspace/HEARTBEAT.md` 中记录的晚间草稿状态为准。

### 阶段二:收到元宝图片后自动发布

1. 当元宝 @周三涵 回传图片后,周三涵自动识别并下载图片。
2. 把图片保存到 `runtime/input/returned-images/`。
3. 自动调用 `python scripts/publish_pending.py --images ...` 发布待发布草稿。
4. 发布成功后,在群里通知用户发布完成。
5. 清理本次待发布记录。

## 扩展边界

- 日常操作看 [workspace/skills/lyzbcy-XiaohongshuSkills/references/usage.md](workspace/skills/lyzbcy-XiaohongshuSkills/references/usage.md)
- 维护说明、冒烟验证和历史问题看 [workspace/skills/lyzbcy-XiaohongshuSkills/references/maintenance.md](workspace/skills/lyzbcy-XiaohongshuSkills/references/maintenance.md)
- 运行时文件约束看 [workspace/skills/lyzbcy-XiaohongshuSkills/references/runtime-rules.md](workspace/skills/lyzbcy-XiaohongshuSkills/references/runtime-rules.md)
