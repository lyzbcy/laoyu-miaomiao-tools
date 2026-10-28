---
name: lyzbcy-video-publish-assistant
description: 在已登录浏览器中准备抖音、B站、小红书和YouTube投稿，以红黄绿门禁恢复上传、核对封面和文案，按本次授权保存草稿或正式发布。
metadata:
  version: 1.3.4
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
    - scripts/xiaohongshu.py
    - scripts/bridge_check.py
    - tests/test_regression.py
    - references/regression.md
    - update.json
    - references/closeout.md
    - CONTRIBUTORS.md
---

# 多平台投稿

正式版 1.3.4（2026-10-28）；版本以frontmatter为准，源码、安装与发行版本按当前交付记录分别核对。

每天首次使用后台运行 `python scripts/update_skill.py --background`；失败沿用当前版，不中断任务。

锁定采用的成片、账号、封面和文案。用户要准备稿件时保存草稿；明确授权发布时，在稿件核验后走独立提交入口。不把一次“多平台发布”扩展到未选择的平台。用户接管的稿件保持只读，保留现场修改。

## 红黄绿门禁

| 灯 | 脚本行为 | Agent 行为 |
|---|---|---|
| 绿 | 精确字段/完成标志已匹配，写断点并继续 | 不重读整页、不截图、不重跑 |
| 黄 | 上传/处理/页面就绪尚未完成，限时退避等待 | 等待或处理别的平台；不重传。封面等待一次实际裁切验收 |
| 红 | 登录失效、对象歧义、字段不符、拒绝或用户关闭页面 | 停该平台，仅采集一份局部诊断；修复后单步续跑 |

可用 `dry-run` 仅检查本地文件与指纹，绝不上传、填表或发布。账号身份、公开范围与简介规定首句须按本次UI实际回读；无登录或安全验证时停该平台，不把历史账号当当前身份。

完成标志须绑定当前稿件。文件选入、上传受理、草稿保存、提交成功、审核通过、公开可见分别记录，后台旧作品的“公开”不能证明新稿已发布。提交尝试先入账；不明结果只能查询，不能二次点击。

## 一条执行链

1. 先读取 kimi-webbridge skill，用 `python scripts/bridge_check.py --session <本任务session>` 检查现有 Edge/Kimi 连接；只列标签，不接管、不重启daemon，不转桌面自动化。桥接就绪不代表账号已核验。本地manifest预检 → `open` → 当前账号/公开范围回读（配置标记时 `check-context`）→ `prepare`。脚本检查当前DOM是否就绪，不默认先 `inspect`；同任务复用session/run-dir和已固定的tabId，浏览器操作串行。
2. `prepare`按步骤回读关键字段，成功只输出门禁结果。封面选入后等真实画布变化，按每种比例看一次平台裁切；`review-covers`记账后继续。不要把文件选入或平台低质检测当裁切验收。
3. 保存并重开，核对标题、正文、关联标签、声明和处理状态。B站活动标签与普通标签分开：每视频最多一个活动标签；普通标签报活动专用时转活动搜索，精确匹配后确认选中；第二个活动词记录略过，不冒充已打上。
4. 小红书同名话题按已观察的 `topic_ids` 精确选择，不按热度/顺序猜；半成品话题续跑不追加重复后缀。YouTube重开等待实际列表路由和可操作语义标签，已在目标页不再点标签；保存只关闭绑定视频的上传对话框。
5. 准备模式到核验为止。正式发布先 `review-plan`，把本次用户授权绑定视频/封面/文案指纹，再 `submit --authorization`；授权不是脚本自行推断。黄灯用 `confirm`继续查询，不重传或重发。小红书 `published=true` 只算 submitted；随后 `confirm_published` 进入笔记管理的已发布筛选，按当前标题、时长、发布时间和 DOM noteId 核验；未匹配维持黄灯。旧断点缺本次时间记录时保留原证据人工核对，不补造尝试。

命令与manifest见[执行与断点](references/automation.md)。平台差异见[适配边界](references/platforms.md)。X、视频号、公众号等候选与确认策略见[扩展路由](references/expansion.md)；未实测适配的平台不算一键支持。

## 范围与证据

视频号每条成片必须单独确认；泛化批量授权不算同意。公众号、知乎、掘金共用一份文章正文，仅适配排版与视频嵌入；公众号群发需另有明确授权。账号、截图、私有稿件链接仅留项目。

结束给出逐平台账号、最终状态、实际链接与待办。普通步骤不留下整屏照片；异常截图不代表审美通过。维护时重写现有规则并同步源码、安装副本、版本和分发包，远端发版按任务授权处理。

## 运行小结与合并收尾

每次完整投稿任务结束读[统一收尾与经验贡献](references/closeout.md)，输出用户指出的问题、实际修正/重试次数、最终脚本或操作方案、逐平台结果与验收边界。由制作skill接续“可以了，去全平台发布吧”时沿用同项目 `run-summary.md`，发布阶段负责把制作与发布汇总成一条消息，只发一次清理提醒与贡献邀约；平台范围和既有授权门禁照常核对，不因“全平台”自动扩张。

新平台接入、AI碰壁原因和经验证更稳定的脚本值得沉淀时，先整理脱敏候选差异，再询问是否愿意贡献PR。本人确认署名或匿名，审核合入后登记[贡献者](CONTRIBUTORS.md)；不自动上传账号/稿件/素材，不自动修改共享skill。占用较大时实测候选旧文件，给保留项、路径与预计释放空间再询问清理；投稿/审核恢复所需文件及防重断点保留。已有答复不重复询问，清理与PR分别授权。

## 维护与回归

变更后运行随包 `python -m unittest discover -s tests -p test_regression.py -v`；完整源码回归、合成DOM与只读实桥检查见[回归与本地同步](references/regression.md)。
