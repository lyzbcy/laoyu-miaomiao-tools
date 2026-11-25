---
name: lyzbcy-video-publish-assistant
description: 在已登录浏览器中准备抖音、B站、小红书和YouTube投稿，以红黄绿门禁恢复上传、核对封面和文案，按本次授权保存草稿或正式发布。
metadata:
  version: 1.3.13
  source: https://raw.githubusercontent.com/lyzbcy/laoyu-miaomiao-tools/main/skills/lyzbcy-video-publish-assistant/SKILL.md
---

# 多平台投稿

1. **锁定目标。** 确认本次平台范围、实际账号、成片、封面、文案和可见性。准备或存草稿沿用该范围，正式提交须有本次授权并绑定稿件指纹。
2. **恢复或准备。** 续跑先查同一 manifest 和 run-dir 的账本。成功步骤直接跳过。新稿用现有登录浏览器，按同一稿件完成上传、保存和字段回读。登录、身份或对象不明时停该平台，处理等待使用有界查询。[命令与断点](references/automation.md)
3. **单次提交并核验。** 点提交前记尝试。结果不明、审核中或用户已手动提交时，按本期记录只读核验，避免重复上传或提交。回执区分草稿、受理、审核、平台内发布和公众可访问。
4. **交付回执。** 逐平台报告实际状态、可验证链接和待办。接续制作时沿用同一项目及收尾账本。[收尾与恢复资料](references/closeout.md)

正式版 1.3.13（2026-11-25），GitHub 发行包 v1.63.0。源码、安装与发行版本分别核对。

## AI 生成声明

成片或图文含合成配音、生成图片或画面、合成动效时，每个平台都如实设置 AI 生成声明。视频和图文是两条投稿，各设各的，保存后回读。作者明确要求本期不声明时，先把 2026-11-25 的实测后果讲清楚；作者仍坚持，才按作者的决定执行，并把依据写进授权文件。

| 平台 | 发布时 | 发布后 |
| --- | --- | --- |
| 抖音 | 自主声明 → 内容由AI生成 | 可补，在「编辑作品」里改，每个作品最多修改 5 次 |
| 小红书 | 添加内容类型声明 → 笔记含AI合成内容 | 可补，编辑后重新进审核 |
| 微信公众号 | 发表设置里的创作来源 | 2026-11-25 实测修改页没有该控件，按发表前设置处理 |
| 微信视频号 | 发表页的视频标注 | 未核实 |
| B站、YouTube | 按 `scripts/profiles.json` 的声明配置 | 未核实 |

回执写明每个平台的声明状态。漏声明被发现时不要删除重发。

## 按任务读取

- 抖音、B站、小红书、YouTube 的声明、封面、合集和控件差异查[对应平台](references/platforms.md)。
- 未见提交回执、用户已接管或富文本有歧义时查[恢复路径](references/receipt-recovery.md)。
- 用户选择扩展平台时查[扩展路由](references/expansion.md)。多期批量查[矩阵](references/matrix.md)，跨平台串行与扫码查[运行手册](references/multiplatform-runbook.md)，游戏、活动或限时任务查[专项日志](references/game-release-log.md)。
- 每天首次使用按[静默更新](references/update.md)后台查新。维护时查[离线回归与同步](references/regression.md)。
