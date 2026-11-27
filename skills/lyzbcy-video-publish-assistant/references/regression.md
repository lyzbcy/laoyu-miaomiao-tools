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

SKILL.md、CHANGELOG 和 update.json 版本一致。分发文件及 LF 规范化 SHA-256 以 update.json 为准。同步本机 Codex 安装副本，并对照打包文件及解压哈希。公开站点与远端清单只在正式发行时同步。

## 2026-11-26 B站创作声明定位修复
- B站创作声明下拉框在正文已经含「含AI生成内容」时，旧 body 等待可能过早结束；通用定位器还漏掉 li 与 menuitem/menuitemradio。等待唯一可见实控件并回读输入值，缺失有界重试、歧义立即停止。test_bilibili_declaration_target.py 回归覆盖 3 项，既有 45 项 regression 通过。该步骤已在 2026-11-26 一次获准稿件的 B站实投中走到完成并读回输入值；单次样本，不代表全链路无干预。
