# lyzbcy-XiaohongshuSkills 使用手册

## 日常发布

### 图文发布

```bash
python scripts/publish.py --title "标题" --content "正文" --images img.jpg
python scripts/publish.py --title-file runtime/input/xhs_title.txt --content-file runtime/input/xhs_content.txt --images img1.jpg img2.jpg
python scripts/publish.py --title "标题" --content "正文" --image-urls "https://example.com/img.jpg"
python scripts/publish_pending.py --images runtime/input/returned-images/img1.jpg runtime/input/returned-images/img2.jpg
```

### 视频发布

```bash
python scripts/publish.py --title "标题" --content "正文" --video video.mp4
python scripts/publish.py --title "标题" --content "正文" --video-url "https://example.com/video.mp4"
```

### 预览模式

```bash
python scripts/publish.py --title "标题" --content "正文" --images img.jpg --preview
```

## 浏览器管理

```bash
python scripts/browser.py start
python scripts/browser.py start --headless
python scripts/browser.py status
python scripts/browser.py restart
python scripts/browser.py kill
```

## 登录辅助

```bash
python scripts/home_login_qrcode.py
python scripts/login_send_code.py
```

输出位置：

- 二维码：`runtime/qrcode/xhs_login_qrcode.png`
- 登录截图：`runtime/screenshots/xhs_home_page.png`

## 多账号

```bash
python scripts/browser.py start --account work --port 9223
python scripts/publish.py --account work --port 9223 --title "标题" --content "正文" --images img.jpg
python scripts/cdp_publish.py list-accounts
python scripts/cdp_publish.py add-account work --alias "工作号"
python scripts/cdp_publish.py --account work login
```

## 话题标签

正文最后一行可写为纯标签行，发布流程会自动识别：

```text
这是正文内容。

#标签1 #标签2 #标签3
```

## 常见问题

### 提示未登录

```bash
python scripts/browser.py start
python scripts/cdp_publish.py login
```

### 浏览器异常残留

```bash
python scripts/browser.py kill
```

### WSL / UNC 路径上传失败

```bash
python scripts/publish.py --title "标题" --content "正文" --images "\\wsl.localhost\Ubuntu\home\user\a.jpg" --skip-file-check
```

## 工作流约定

1. 日常只从 `scripts/publish.py` 进入发布。
2. 登录、重启、端口切换只从 `scripts/browser.py` 进入。
3. 评论回复统一走 `lyzbcy-social-comment`，不要在这里做运营回复。
4. 临时标题、正文、二维码和截图都放到 `runtime/`，不要直接落到 `workspace/` 根目录。

## 每晚 20 点日记转图文

### 自动生成阶段

每天晚上 20 点的自动任务应完成以下产物：

- `runtime/input/xhs_title.txt`
- `runtime/input/xhs_content.txt`
- `runtime/input/xhs_image_prompts.md`
- `runtime/input/xhs_pending_post.md`

生成要求：

1. 内容来源于当天最新日记。
2. 人物形象必须是周三涵本人，参考 `workspace/IDENTITY.md`。
3. 配图提示词要和文章主题一致，不要只给泛化写真词。
4. 自动任务只发草稿和提示词给用户，不直接发布。

### 用户回图后的发布阶段

如果用户把生成好的图片发回来了，优先走：

```bash
python scripts/publish_pending.py --images runtime/input/returned-images/img1.jpg runtime/input/returned-images/img2.jpg
```

如果图片来自 URL，可改用：

```bash
python scripts/publish_pending.py --image-urls "https://example.com/1.jpg" "https://example.com/2.jpg"
```

发布前默认使用 `runtime/input/xhs_title.txt` 和 `runtime/input/xhs_content.txt`，避免回图后再重新整理文案。
