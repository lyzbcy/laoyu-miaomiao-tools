---
name: software-video-production
description: 制作和改版软件演示、生活情境宣传短视频，处理真实操作证据、隐私、视听表达、封面和交付复盘。不替代软件开发或漫剧制作。
metadata:
  version: 0.11.3
  source: https://raw.githubusercontent.com/lyzbcy/laoyu-miaomiao-tools/main/skills/software-video-production/SKILL.md
  files:
    - CHANGELOG.md
    - SKILL.md
    - agents/openai.yaml
    - docs/agent.md
    - docs/audio.md
    - docs/characters.md
    - docs/creative.md
    - docs/delivery.md
    - docs/evolution.md
    - docs/exemplars.md
    - docs/lessons.md
    - docs/music-generation.md
    - docs/privacy.md
    - docs/remotion.md
    - docs/tech.md
    - docs/workflow.md
    - references/update.md
    - scripts/media_check.py
    - scripts/update_skill.py
    - assets/shot-recipes.json
    - docs/cloud-transcription.md
    - docs/editing.md
    - references/tool-workflow.md
    - scripts/cut_review.py
    - scripts/edit_plan.py
    - scripts/transcription_preflight.py
    - scripts/fixtures/edit-project.json
    - scripts/fixtures/transcription-request.json
    - scripts/tests/test_offline_workflow.py
    - assets/remotion-software/entry.jsx
    - docs/integration.md
    - scripts/render_shots.cjs
    - scripts/render_edl.py
    - scripts/produce.py
    - scripts/SyntheticSpeech.cs
    - scripts/local_transcribe.py
    - scripts/tests/test_render_integration.py
    - assets/upstream-entry.tsx
    - assets/upstream-pins.json
    - docs/upstream.md
    - scripts/verify_upstream.py
    - scripts/render_upstream_shots.cjs
    - scripts/upstream_native.py
    - scripts/produce_upstream.py
    - scripts/tests/test_upstream_gate.py
    - update.json
---

# 软件宣传视频制作

每天首次使用从本skill目录后台执行 `python scripts/update_skill.py --background`，直接继续任务；失败沿用旧版。细节见[更新机制](references/update.md)。

把真实功能拍成愿意看下去的变化。先读当前项目入口，确认采用版本、用户最新反馈和任务范围；按问题读[模块导航](docs/agent.md)，不加载全部案例。用户要求严格流程时，开工先回报实际读取的 SKILL.md 路径、版本与本次执行链；未读取就明确说明。分镜/剪辑、字幕音频、动效、时间线与渲染验收逐项登记实际产物和检查范围，不适用或受阻写具体原因。仅调用 Remotion、FFmpeg 或媒体检查不能证明执行了整套工作流。

## 制作顺序

1. **核实事件与源时间。** 看原素材的操作、声音与设备关系，登记源清单、哈希、时间边界与隐私；有语音且需按词剪辑或同步字幕时核对字级边界。创意情境与真机证据分别标明；需要删口头词/停顿或重组镜头时按[可回滚剪辑与语义分镜](docs/editing.md)保存候选理由、EDL和剪后字幕映射，不直接改原片。
2. **先验观看理由与兑现。** 从素材中选一种能成立的[开头机制](docs/creative.md)，把首句与首帧一起检查：看哪里、预测什么、已得什么回报、接着等什么。用实际素材比较两个0—5秒开头，选对叙事再扩展；约3秒、5秒只作观察点。参考的画面事实、创作解释与留存指标按[范例方法](docs/exemplars.md)分开，不把标题或特效数量当留人依据。
3. **决定信息由谁承载。** 能看懂的交给动作；情绪交给反应或短心声；确有解释缺口才加口播。音乐叙事片可用RPG打字和轻哔声，保持歌曲连续；讲解片按理解需要安排人声，不能用音乐填补信息缺口。见[创意](docs/creative.md)、[声音](docs/audio.md)。
4. **安排视线和运动。** 真实操作留出看清的时间，按[镜头配方](docs/editing.md)选前后对比、局部放大或步骤递进，再选择单一主渲染/必要局部叠层。文字可读、动作有触发和落定；实心栅格隐私派生物先于动效，按[隐私](docs/privacy.md)复查放大、转场和每个切点。
5. **分别验收成片和封面。** 技术、事实/隐私、实际视听范围、用户评价各自记录。封面负责让人想点开，另按手机缩略图与平台真实裁切验收；成片评分不能转算封面评分。见[交付](docs/delivery.md)。
6. **锁定与收尾。** 用户采用后锁定成片；发布另按任务授权处理。按[复盘与压缩](docs/evolution.md)改写已有规则、归档项目证据；清理范围以用户要求为准。

## 可运行入口

先按素材与要求选择路径，并核对依赖是否可用：[自研镜头与EDL](docs/integration.md)适合其支持的镜头和剪辑；[原版上游接入](docs/upstream.md)使用固定版本的部分shotcraft组件及video-use助手。两个demo都是合成素材技术验收，不能代替真实成片；上游一键验收入口仅接受合成fixture。无语音或已有校正字幕时不强制转写；需要按词剪辑、生成或对齐字幕时，才选择适用的转写与校对。用户指定原版时不得默默改用自研替代，缺失组件先说明。记录实际路径和未执行项。

## 人物与系列偏好

当前要求优先于历史偏好。人物和开屏采用用户已授权的素材，系列偏好读取当前项目的约定，不把某个系列的偏好扩展到其他项目。素材接入见[人物复用](docs/characters.md)；精选表情、光绘和RPG按场景选，不要求每片凑齐。真实屏幕与操作细节保持清晰，字号以手机实际阅读判断。获取渠道、屏幕口令是否朗读、是否允许网址按当次要求，不复用旧产品指令。

## 工具与边界

复用已有Python、FFmpeg、音频与模型；丰富动效优先参考[Remotion](docs/remotion.md)，重建见[技术](docs/tech.md)。普通旁白默认Edge TTS及匹配缓存；模型识别、歌唱与TTS按真实能力命名。云转写先按[免费用量准入](docs/cloud-transcription.md)测输入时长、核实当前余额、显示消耗与剩余并取得这批上传的明确批准；余额未知/不足不自动付费，离线预检不执行上传。大型下载先说明用途和体量；模型缓存遵从当前用户的盘位与共享限制，并验证离线复用。

不因剪辑任务修改或发布软件、购买服务或发送消息。制作、保存草稿、提交审核、公开发布分别记录；用户确认与Agent独立核验分别标明。抽帧、ASR和响度不能冒充完整试听、用户审美认可或留存证据。

版本以frontmatter为准；复盘依据与范围见[lessons](docs/lessons.md)。本包不附第三方视频、人物原图、模型或作者私人项目。
