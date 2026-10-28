# 项目开发入口

## 项目一句话
捞鱼妙妙工具提供可分发的个人Agent技能；本次维护多平台视频发布skill。

## 技术栈
Python标准库、Kimi WebBridge/Curl、Node合成DOM回放；各skill独立版本及SHA清单。

## 目录地图
`skills/lyzbcy-video-publish-assistant/SKILL.md`是发布入口；`tests/`为源码回归，`scripts/package_skill.py`为校验打包；`docs/`为公开站点（正式发行时同步）；本地验证证据独立保存，不随公开包发布。

## 开发流程
先读目标skill及渐进文档，工作副本改动；基线/增量/完整回归通过后同步版本、变更记录、hash清单与本机Codex安装。包解压再验hash，回退在另一个副本验证。

## 红线
实站回归只读，不重复投稿；不确定最终点击只查询，不重传。账号凭证、用户投稿素材及截图不进入公开包。遵守本次授权的平台和指纹门禁。普通开发不自动公开发行。

## 当前状态
投稿助手正式版1.3.3（2026-10-28），下载发行标签v1.39.0；源码、安装副本及ZIP文件清单一致。官网版本2026.10.28-1；对应CHANGELOG和在线update.json同步。回归执行 `python -m unittest discover -s tests -v`，打包执行 `python scripts/package_skill.py lyzbcy-video-publish-assistant`。实桥检查只读，不重复真实投稿。
