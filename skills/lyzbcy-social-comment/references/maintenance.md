# lyzbcy-social-comment 维护说明

## 运行目录

- `runtime/input/`：临时输入 CSV
- `runtime/output/`：回复草稿、发送日志、执行产物

不要再把输入文件、输出文件直接放在 skill 根目录。

## 核心文件

- `config.json`：默认平台、语气、输出目录、黑名单和升级词
- `profiles/`：平台页面与会话配置
- `templates/default.json`：默认回复模板和恶意评论规则
- `templates/custom.json`：本地覆写模板

## 维护建议

1. 新增平台时，先补 `profiles/<platform>.json`
2. 新增意图时，先改 `batch_comment_drafts.py` 的规则，再补模板
3. 高风险评论保持 review-first，不要直接全自动发送
4. 日志和草稿定期从 `runtime/output/` 清理

## 规范化说明

本次整理后，不再把以下内容放在 skill 根目录：

- 输入样例 CSV
- 输出 JSON 日志
- 模板示例 Markdown
- 第三方安装残留元数据
