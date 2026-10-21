---
name: software-video-production
description: 制作和改版软件演示、生活情境宣传短视频，处理真实操作证据、隐私、视听表达、封面和交付复盘。不替代软件开发或漫剧制作。
metadata:
  version: 0.8.5
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
    - update.json
---

# 软件宣传视频制作

每天首次使用从本skill目录后台执行 `python scripts/update_skill.py --background`，直接继续任务；失败沿用旧版。细节见[更新机制](references/update.md)。

把真实功能拍成愿意看下去的变化。先读当前项目入口，确认采用版本、用户最新反馈和任务范围；按问题读[模块导航](docs/agent.md)，不加载全部案例。

## 制作顺序

1. **核实事件。** 看原素材的操作、声音与设备关系，标记源时间和隐私。创意情境可表现体验，功能由真实界面或明确产品依据支撑，二者不能混称真机实测。
2. **先验观看理由与兑现。** 从素材中选一种能成立的[开头机制](docs/creative.md)，把首句与首帧一起检查：看哪里、预测什么、已得什么回报、接着等什么。用实际素材比较两个0—5秒开头，选对叙事再扩展；约3秒、5秒只作观察点。参考的画面事实、创作解释与留存指标按[范例方法](docs/exemplars.md)分开，不把标题或特效数量当留人依据。
3. **决定信息由谁承载。** 能看懂的交给动作；情绪交给反应或短心声；确有解释缺口才加口播。音乐叙事片可用RPG打字和轻哔声，保持歌曲连续；讲解片按理解需要安排人声，不能用音乐填补信息缺口。见[创意](docs/creative.md)、[声音](docs/audio.md)。
4. **安排视线和运动。** 真实操作留出看清的时间。文字先可读，再用描线、流光、辉光等响应语义；人物动作有触发、停顿和结果，避免全程机械浮动或震屏。按[隐私](docs/privacy.md)复查放大与转场。
5. **分别验收成片和封面。** 技术、事实/隐私、实际视听范围、用户评价各自记录。封面负责让人想点开，另按手机缩略图与平台真实裁切验收；成片评分不能转算封面评分。见[交付](docs/delivery.md)。
6. **锁定与收尾。** 用户采用后锁定成片；发布另按任务授权处理。按[复盘与压缩](docs/evolution.md)改写已有规则、归档项目证据；清理范围以用户要求为准。

## 作者系列的可覆盖偏好

当前要求优先于历史偏好。作者系列需要人物时优先采用捞鱼/星星布丁现有素材；其他用户以自己的角色为准。素材接入见[人物复用](docs/characters.md)；精选表情、光绘和RPG是可选表达，按场景选，不要求每片凑齐。真实屏幕与操作细节保持清晰，字号以手机实际阅读判断。获取渠道、屏幕口令是否朗读、是否允许网址按当次要求，不复用旧产品指令。

## 工具与边界

复用已有Python、FFmpeg、音频与模型；丰富动效优先参考[Remotion](docs/remotion.md)，重建见[技术](docs/tech.md)。普通旁白默认Edge TTS及匹配缓存；模型识别、歌唱与TTS按真实能力命名。大型下载先说明用途和体量；模型缓存遵从当前用户的盘位与共享限制，并验证离线复用。

不因剪辑任务修改或发布软件、购买服务或发送消息。制作、保存草稿、提交审核、公开发布分别记录；用户确认与Agent独立核验分别标明。抽帧、ASR和响度不能冒充完整试听、用户审美认可或留存证据。

版本以frontmatter为准；复盘依据与范围见[lessons](docs/lessons.md)。本包不附第三方视频、人物原图、模型或作者私人项目。
