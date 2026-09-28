# lyzbcy-xhs-agent

小红书 Agent 浏览器操作 skill：在用户已登录的页面上协助发布笔记、上传小工具、查看评论和逐条回复，并核对结果。

把整个文件夹放入 Agent 的 skills 目录，确保其中有 `SKILL.md`。不需要安装 Playwright、服务器定时任务或额外的 Python 依赖；浏览器连接工具由运行环境提供。本机若安装 Kimi WebBridge，可按 `SKILL.md` 和 `references/browser-workflows.md` 使用。

示例：

- “帮我把这篇图文发到小红书，发布前核对封面和小工具组件。”
- “把这个 ZIP 作为小工具新版本重传，确认部署和审核状态。”
- “看看这条笔记的新评论，先拟回复，再按我的授权逐条发出并核验。”

旧版 `lyzbcy-xhs-comment-check` 的无人值守评论自动回复脚本已从新版 skill 移除。旧发布包仍在历史 Release；这不是规避平台检测的工具。

License: MIT
