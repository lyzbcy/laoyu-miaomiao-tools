# lyzbcy-XiaohongshuSkills 运行文件约束

## 目的

避免使用小红书发布 skill 时，把临时输入、二维码、截图、登录辅助脚本散落到 `workspace/` 根目录。

## 固定落点

- 标题/正文输入文件：`runtime/input/`
- 待发布配图提示词和待发布说明：`runtime/input/`
- 用户回传图片暂存：`runtime/input/returned-images/`
- 登录二维码图片：`runtime/qrcode/`
- 登录截图：`runtime/screenshots/`
- 登录缓存：`runtime/login_status_cache.json`

## 明确禁止

以下文件不应继续直接出现在 `workspace/` 根目录：

- `xhs_title.txt`
- `xhs_content.txt`
- `xhs_login_qrcode.png`
- `xhs_home_login.py`
- `xhs_login_helper.py`

## 推荐做法

### 文件输入

```text
runtime/input/xhs_title.txt
runtime/input/xhs_content.txt
runtime/input/xhs_image_prompts.md
runtime/input/xhs_pending_post.md
runtime/input/returned-images/
```

### 登录辅助

```bash
python scripts/home_login_qrcode.py
python scripts/login_send_code.py
```

### 周期清理

```bash
python scripts/cleanup_runtime.py
```

该脚本会清理旧二维码、旧截图和陈旧输入文件，但不会删除登录缓存。
