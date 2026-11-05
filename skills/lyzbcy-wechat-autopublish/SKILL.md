---
name: lyzbcy-wechat-autopublish
description: 准备、排版、保存与发表微信公众号图文，处理官方API、已登录浏览器、管理员验证、视频号引用和发表回读；支持明确授权的定时任务。不保证免扫码，不把发表与群发混为一谈。
metadata:
  version: 1.1.0
  files:
    - CHANGELOG.md
    - SKILL.md
    - article.example.json
    - body.html
    - config.example.json
    - cover.png
    - references/api-reference.md
    - references/article-layout.md
    - references/browser-playbook.md
    - references/content-sources.md
    - references/deep-water-cgi.md
    - references/iphone-mirroring.md
    - scripts/article_review.py
    - scripts/click.swift
    - scripts/iphone_coords.json
    - scripts/publish_browser.py
    - scripts/publish_iphone.py
    - scripts/wechat_api.py
    - tests/test_article_review.py
    - tests/test_wechat_api.py
    - version.json
    - update.json
  source: https://raw.githubusercontent.com/lyzbcy/laoyu-miaomiao-tools/main/skills/lyzbcy-wechat-autopublish/SKILL.md
---

# 微信公众号图文运营

沿用用户对本篇或明确批次的授权，完成可读正文、封面、保存与发表验证。不承诺“100%零人工”或始终免扫码；登录、管理员验证和审核以实际平台状态为准。

## 选择通路

| 通路 | 使用条件 | 入口 |
|---|---|---|
| 官方API | 已有有效配置且当前账号具备相应权限 | scripts/wechat_api.py、[API参考](references/api-reference.md) |
| 已登录浏览器 | 富文本编辑、视频号引用、API无权限或用户选择 | [浏览器操作与恢复](references/browser-playbook.md) |
| 已配置手机镜像 | 用户明确选择且已有相应设备和配对 | [历史镜像路径](references/iphone-mirroring.md)，不保证免验证 |

浏览器路线优先复用当前环境的连接工具与用户登录态，不为此强制创建AppSecret或安装第二套浏览器。独立部署才按需使用Playwright。API返回草稿已创建时沿该ID恢复，不再运行建稿链。需要内容源时才读[适配器](references/content-sources.md)。

## 一篇文章的顺序

1. **恢复对象与脱敏。** 读项目授权、正文/封面指纹、草稿ID和提交账本；已尝试提交只查询。用户接管的稿件保持只读，不新建同名替代。内部业务、凭据、内网链接与私人资料先脱敏。
2. **沿用本次授权。** 用户明确批准本篇/批次直接发表或免再审时继续，不重复确认。授权缺失则先完成可审的标题、摘要、封面和正文再询问；相似历史稿的同意不扩展到新对象。
3. **制作图文。** 按[排版与原生视频](references/article-layout.md)组织导读、分节、重点、代码/对照和收尾。公众号使用内联样式。封面、作者、摘要、AI来源、合集分别核对；需要配套视频时引用本期视频号，不用上期或占位视频。
4. **保存并重开同稿。** 检查正文完整、标题层级、代码/表格、重点样式、真实裁切及视频组件ID/nonce。本地预览、编辑器持久化和公开页面分别验收。
5. **发表与群发分开。** 未明确授权群发时关闭原生“群发通知”，本次最终弹窗读回关闭状态及“未开启群发通知”。重开弹窗重新核对；另有群发授权时绑定本篇、账号与时间，不依据旧配额描述保证当前次数。
6. **单次提交。** 最终外部点击/API submit前登记attempt、时间与指纹。管理员微信验证保留同一稿件与窗口交用户完成；登录成功不等于本篇发表验证完成。二维码空白/过期先辨明现场，不让用户扫空白裁图。
7. **只读确认终态。** 用户说“已验证/已发表”后先查原稿记录，不再点发表。审核中维持待查；已发表后取得永久公众链接，核对账号、标题及本期原生视频。后台已发表、公众组件一致和手机完整播放分别记录。

## 现有API脚本

配置依次取`--config`绝对路径、`WECHAT_AUTOUPLOAD_CONFIG`、skill目录config.json。复制config.example.json建立私人配置，权限及IP白名单以当次结果核实。

```bash
python scripts/wechat_api.py token --config /private/config.json
python scripts/wechat_api.py publish --article /private/article.json --config /private/config.json --dry-run
python scripts/wechat_api.py publish --article /private/article.json --config /private/config.json --draft-only
python scripts/wechat_api.py publish --article /private/article.json --config /private/config.json
python scripts/wechat_api.py status --config /private/config.json --publish-id EXISTING_ID
```

干跑不触网但校验配置与素材，不代表实账号发表成功。auto返回draft-ready-browser时草稿已经入箱，继续原稿。publish_browser.py及镜像脚本为历史部署适配，不保证当前DOM、群发开关与验证码流程适用，不盲跑固定点击序列。

## 可重复检查与记录

`python scripts/article_review.py layout BODY.html --min-headings 2 --min-styled 5`检查保存HTML的结构，不证明美观或手机可读。

`python scripts/article_review.py publication OBSERVATION.json --expect PLAN.json`核对已经从当前UI取得的账号、唯一发表记录、永久链接及本期视频。只读本地文件，不登录、不提交、不把“已验证”直接升格为公开成功。输入见[恢复手册](references/browser-playbook.md)。

记录操作起止、实际等待、稿件ID、提交attempt、失败原因与证据路径。截图用于排版/裁切和异常诊断，不要求每次普通点击都截全屏。未知结果只查，验证码交用户。

仅在用户要求时创建定时任务，使用当前环境的调度工具，提示词写清账号、内容源、每篇/批次授权与是否群发。无人值守配置的真实支持先核实，不擅自开启auto_confirm。

config.json、登录态、请求头、二维码、真实账号/稿件ID、后台原始DOM和素材留项目私有目录，不进Git/ZIP。只为测试脚本不真实发测试文；离线测试用fake server。发布前核对版本、文件白名单、SHA与脱敏结果。
