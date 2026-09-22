# Changelog

## [1.0.0] 2026-09-22

首发（从综测实战工作流固化）。

- `scripts/qq.py`：grab / whoami / send / group / send-file / poll / history / save / restore 九个子命令，配置自动发现（onebot11_*.json → host/port/token/QQ），环境变量可覆盖。
- 三段式流程（借号 → 收发 → 还号）写进 SKILL.md，还号后登录按钮留给用户，禁止自动化点击。
- 坑点固化：健康检查 stub 假成功（登录判据只认 `data.user_id`、发送判据只认 `data.message_id`）、路径风格 API、`lastestMsg` 字段名、非好友 history 不可见、file_id 必须完整、图片下载带 UA。
