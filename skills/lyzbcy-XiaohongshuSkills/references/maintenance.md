# lyzbcy-XiaohongshuSkills 维护说明

## 依赖与配置

- 安装依赖：`pip install -r requirements.txt`
- 账号模板：`config/accounts.json.example`
- 登录缓存：`runtime/login_status_cache.json`
- 文件输入目录：`runtime/input/`
- 二维码目录：`runtime/qrcode/`
- 截图目录：`runtime/screenshots/`

本地账号配置建议从 `config/accounts.json.example` 复制为未跟踪的 `config/accounts.json` 再使用，不要提交真实账号信息。

## 晚间自动草稿任务

- 触发方式：由 `workspace/HEARTBEAT.md` 在每小时心跳时检查；当时间已过当天 20:00（Asia/Shanghai）且当天尚未执行时触发
- 自动任务职责：读取当天日记，生成小红书标题、正文、配图提示词，并通过元宝发给用户等待回图
- 自动任务不负责直接发布；真正发布发生在用户回传图片之后
- 推荐待发布文件：`runtime/input/xhs_title.txt`、`runtime/input/xhs_content.txt`、`runtime/input/xhs_image_prompts.md`、`runtime/input/xhs_pending_post.md`
- 用户回图后的统一入口：`python scripts/publish_pending.py --images ...`
- 去重状态建议记录在 `workspace/HEARTBEAT.md`，不要再额外创建 cron 任务做同一件事

## 冒烟验证

每次改动发布链路后至少执行：

```bash
python scripts/browser.py restart
python scripts/cdp_publish.py check-login
python scripts/publish.py --preview --title "测试标题" --content "测试正文" --images test.jpg
python scripts/browser.py kill
```

如需登录辅助验证，可追加：

```bash
python scripts/home_login_qrcode.py
python scripts/login_send_code.py
python scripts/cleanup_runtime.py
```

## 维护边界

- `scripts/publish.py`：面向日常发布的封装入口
- `scripts/browser.py`：浏览器生命周期入口
- `scripts/publish_pipeline.py`：底层发布编排
- `scripts/cdp_publish.py`：底层 CDP 自动化与扩展命令

如果只是给业务同学用，优先维护 `publish.py` 和 `browser.py` 的稳定性；不要把复杂的原始命令暴露成默认入口。

## 历史问题摘要

来自既有代码审阅与维护记录，当前最值得持续关注的点：

1. 多账号与端口复用容易串号，使用多账号时尽量固定账号与端口映射。
2. 页面选择器依赖小红书创作者中心 DOM，改版后优先检查 `scripts/cdp_publish.py` 中的 `SELECTORS`、上传等待与发布按钮逻辑。
3. 内容抓取、互动、评论等底层能力存在，但不应作为本 skill 的默认业务入口。
4. 登录缓存和运行时产物应放在 `runtime/`，不要继续把临时文件散落到 skill 根目录。
5. `workspace/` 根目录不应再出现 `xhs_*` 命名的临时输入和登录辅助文件。
6. 与“今晚待发布”相关的中间产物也应继续留在 `runtime/input/`，不要散落到聊天导出目录或 workspace 根目录。

## 内部维护命令

以下命令保留给维护场景，不作为日常发布入口：

```bash
python scripts/cdp_publish.py check-login
python scripts/cdp_publish.py get-login-qrcode
python scripts/cdp_publish.py search-feeds --keyword "春招"
python scripts/cdp_publish.py get-feed-detail --feed-id FEED_ID --xsec-token TOKEN
python scripts/cdp_publish.py content-data
python scripts/home_login_qrcode.py
python scripts/login_send_code.py
python scripts/cleanup_runtime.py
```

如果要处理评论通知、评论详情或互动，优先评估是否应该放到 `lyzbcy-social-comment`，而不是继续扩张这个发布 skill 的职责。

## 已清理的非规范内容

以下内容不再作为 skill 正式结构的一部分：

- README 仓库说明
- AGENTS 仓库开发约定
- todo 临时笔记
- 根目录 `tmp/` 运行缓存
- `.git/`、`__pycache__/` 等仓库残留
