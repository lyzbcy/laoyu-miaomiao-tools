---
name: lyzbcy-video-publish-assistant
description: 在已登录浏览器中准备抖音、B站、小红书和YouTube投稿，以红黄绿门禁恢复上传、核对封面和文案，按本次授权保存草稿或正式发布。
metadata:
  version: 1.3.1
  source: https://raw.githubusercontent.com/lyzbcy/laoyu-miaomiao-tools/main/skills/lyzbcy-video-publish-assistant/SKILL.md
  files:
    - CHANGELOG.md
    - SKILL.md
    - references/automation.md
    - references/platforms.md
    - references/update.md
    - references/expansion.md
    - scripts/browser.py
    - scripts/bilibili.py
    - scripts/gates.py
    - scripts/prepare_upload.py
    - scripts/profiles.json
    - scripts/publish.py
    - scripts/update_skill.py
    - scripts/youtube.py
    - update.json
---

# 多平台投稿

每天首次使用后台运行 `python scripts/update_skill.py --background`；失败沿用当前版，不中断任务。

锁定采用的成片、账号、封面和文案。用户要准备稿件时保存草稿；明确授权发布时，在稿件核验后走独立提交入口。不把一次“多平台发布”扩展到未选择的平台。用户接管的稿件保持只读，保留现场修改。

## 红黄绿门禁

| 灯 | 脚本行为 | Agent 行为 |
|---|---|---|
| 绿 | 精确字段/完成标志已匹配，写断点并继续 | 不重读整页、不截图、不重跑 |
| 黄 | 上传/处理/页面就绪尚未完成，限时退避等待 | 等待或处理别的平台；不重传。封面等待一次实际裁切验收 |
| 红 | 登录失效、对象歧义、字段不符、拒绝或用户关闭页面 | 停该平台，仅采集一份局部诊断；修复后单步续跑 |

完成标志须绑定当前稿件。文件选入、上传受理、草稿保存、提交成功、审核通过、公开可见分别记录，后台旧作品的“公开”不能证明新稿已发布。提交尝试先入账；不明结果只能查询，不能二次点击。

## 一条执行链

1. 本地manifest预检 → `open` → `prepare`。脚本检查当前DOM是否就绪，不默认先 `inspect`；同任务复用session/run-dir，浏览器操作串行。
2. `prepare`按步骤回读关键字段，成功只输出门禁结果。封面选入后等真实画布变化，按每种比例看一次平台裁切；`review-covers`记账后继续。不要把文件选入或平台低质检测当裁切验收。
3. 保存并重开，核对标题、正文、关联标签、声明和处理状态。B站活动标签与普通标签分开：每视频最多一个活动标签；普通标签报活动专用时转活动搜索，精确匹配后确认选中；第二个活动词记录略过，不冒充已打上。
4. 准备模式到核验为止。正式发布先 `review-plan`，把本次用户授权绑定视频/封面/文案指纹，再 `submit --authorization`；授权不是脚本自行推断。黄灯用 `confirm`继续查询，不重传或重发。

命令与manifest见[执行与断点](references/automation.md)。平台差异见[适配边界](references/platforms.md)。X、视频号、公众号等候选与确认策略见[扩展路由](references/expansion.md)；未实测适配的平台不算一键支持。

## 范围与证据

视频号每条成片必须单独确认；泛化批量授权不算同意。公众号、知乎、掘金共用一份文章正文，仅适配排版与视频嵌入；公众号群发需另有明确授权。账号、截图、私有稿件链接仅留项目。

结束给出逐平台账号、最终状态、实际链接与待办。普通步骤不留下整屏照片；异常截图不代表审美通过。维护时重写现有规则并同步源码、安装副本、版本和分发包，远端发版按任务授权处理。
