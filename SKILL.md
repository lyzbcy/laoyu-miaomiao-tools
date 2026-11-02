# 项目开发入口

## 项目一句话
捞鱼妙妙工具提供可分发的个人Agent技能；各skill独立维护与发行。

## 技术栈
Python标准库、Kimi WebBridge/Curl、Node合成DOM回放；各skill独立版本及SHA清单。

## 目录地图
`skills/lyzbcy-video-publish-assistant/SKILL.md`是发布入口；`tests/`为源码回归，`scripts/package_skill.py`为校验打包；`docs/`为公开站点（正式发行时同步）；本地验证证据独立保存，不随公开包发布。

## 开发流程
先读目标skill及渐进文档，工作副本改动；基线/增量/完整回归通过后同步版本、变更记录、hash清单与本机Codex安装。包解压再验hash，回退在另一个副本验证。

## 红线
实站回归只读，不重复投稿；不确定最终点击只查询，不重传。账号凭证、用户投稿素材及截图不进入公开包。遵守本次授权的平台和指纹门禁。普通开发不自动公开发行。

## 当前状态

2026-11-02：制作skill正式版0.14.12、发布skill正式版1.3.8，双下载包统一发行标签v1.53.0；网站版本2026.11.02-5。源码、更新清单及包按文件哈希核验，当前本机使用副本同步。发行前运行两skill随包离线回归、源码回归和打包/站点一致性检查；本机证据留项目，不进入公开包。实站不重复真实投稿。

## QQ skill 维护入口

`skills/lyzbcy-qq-napcat-messenger/SKILL.md`和`references/runtime.md`说明Node/注入启动链、本机配置与还号。正式版1.1.1，发行包v1.48.0。回归：`python -m unittest discover -s tests -p test_qq_runtime.py -v`。真实收发已完成的消息只回读，不重复发；账号、token、runtime.local.json和启动日志不得进入Git/ZIP。
