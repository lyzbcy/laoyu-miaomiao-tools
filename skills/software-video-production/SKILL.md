---
name: software-video-production
description: 制作和改版软件演示、生活情境宣传及知识讲解短视频，处理真实操作证据、隐私、视听表达、教学样片、封面和交付复盘。不替代软件开发或漫剧制作。
metadata:
  version: 0.14.26
  source: https://raw.githubusercontent.com/lyzbcy/laoyu-miaomiao-tools/main/skills/software-video-production/SKILL.md
---

# 软件宣传视频制作

先读项目入口、采用版本和最新要求。局部改版只回到受影响阶段，复用已确认的表达和素材。

1. **建立证据。** 核实原素材能证明的事件，区分实录与示意。保留源文件和源时间映射，敏感画面按[隐私处理](docs/privacy.md)后再变换或输出。
2. **先验表达，再批量制作。** 确定观众为何看、能看到什么结果。方案未定时，用实际素材做一段能检验关键表达的有声样片，再锁定剪辑、字幕、动效和声音。完整新片走[制作流程与证据账本](docs/workflow.md)。
3. **验收最终产物。** 核对本次约定、事实、隐私和实际声画。需要封面时与成片分别验收。记录实际检查范围，用户采用后锁定对应版本。[导出与验收](docs/delivery.md)
4. **交付或续接投稿。** 交成片及必要重建资料。收到本次发布指令后，将已采用成片、封面、文案和同一项目账本交给 `lyzbcy-video-publish-assistant`。[交接与收尾](docs/run-summary.md)

## 按任务读取

- 改剪辑或同步字幕读[剪辑与时间映射](docs/editing.md)。配音、选曲或混音读[声音](docs/audio.md)，用户已选声音优先复用匹配缓存。普通中文旁白默认哈基米风格的曼波音色；`scripts/narrate.py` 是历史 Milora 适配，试用接口曾观察到下架并需月包，不代表当前可用，生成前先核实服务、音色和费用；下架或需付费即停，不自动购买、换声或部署本地模型。详见[默认中文配音](docs/audio.md#默认中文配音跨电脑)。用创作台画布/剪辑/打标或识别本机工具链版本时读[创作台](docs/creator-studio.md)，不复制旧画布副本进项目。
- 需要教学、系列回顾或高级动效时，再选[教学样片](docs/teaching-review.md)、[系列](docs/series.md)或[镜头案例](docs/advanced-cases.md)。研究玻璃材质、参考片动效或 MEP 时读[玻璃动效与代码式剪辑](docs/reference-motion.md)。
- 找其他实现、案例或复盘方法时查[模块索引](docs/agent.md)。已有规则覆盖的问题修执行，单片参数留项目。
- 每天首次使用按[静默更新](references/update.md)后台查新。
