# 回归与本地同步

## 六项变更

- `Browser.curl`：仅IP loopback/localhost设置curl `--noproxy *`；不改环境变量，远端不绕过代理。
- `choose_topic/apply_topics`：同名候选有歧义即列ID；显式topic_ids消歧；已关联话题跳过，半成品不重复追加。
- `YouTubeDraft.reopen`：DOM出现不等于AX可点，等路由再读草稿；已在目标路由跳过点击。已有ID只匹配同ID行，不重新上传。
- `publication_signal/confirm_published`：owned published=true只算提交，列表终态单独核验tab/title/duration/time/noteId；黄灯只查询；与提交同一分钟的记录须匹配本次回执noteId，否则黄灯。
- `Browser.semantic(scope,video_id)`：上传对话框必须唯一可见，同视频公开链接绑定，作用域内按钮仍须唯一；不退回全局第一个。
- `bridge_check.py`：现有Edge/Kimi优先，只读检查；连接不等于账号身份。

## 命令

随包独立离线回归：`python -m unittest discover -s tests -p test_regression.py -v`。
源码项目：`python -m unittest discover -s tests -v`，`python scripts/package_skill.py lyzbcy-video-publish-assistant --check`。
Node用于合成DOM重放；Python stdlib + curl用于失效代理的本机HTTP stub测试。只有 `bridge_check.py` 使用实桥，只列标签、不修改平台。

## 发布与同步

SKILL.md、CHANGELOG、update.json版本一致；update.json所有文件LF规范化SHA256重算。同步本机Codex安装目录并逐文件比对，候选ZIP解压再比对。1.3.3按本次明确授权正式发行：官网卡片、下载链接、AI摘要、更新日志及version.json同步；下载包、源码及在线更新清单逐文件验hash。普通开发不自动公开发行。

可复用维护提示词：

```text
先读项目SKILL.md及发布skill；只在工作副本修复，先跑基线。复现代理/话题歧义/SPA竞态/终态/对话框作用域/桥接入口六类回归，保留不重复上传和授权门禁。同步代码、文档、开发版本及本机安装副本并比较哈希；不自动公开发行，不为回归重复真实投稿。保存差异、原哈希及可验证回退回执。
```
