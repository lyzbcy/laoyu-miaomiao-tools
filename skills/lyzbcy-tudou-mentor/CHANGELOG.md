# Changelog

本文件记录 `lyzbcy-tudou-mentor` 技能的版本变更历史。

格式基于 [Keep a Changelog](https://keepachangelog.com/)，版本号遵循 [Semantic Versioning](https://semver.org/)。

## [1.1.0] - 2026-09-04

### Added

- **references/dialogues.md 逐字对话风格锚**：16 组真实多轮对话（事故安抚/CR 对照/提问排查/任务工时/教学三步/降维/点破 AI 代写/生活关怀），土豆侧逐字保留（表情、`--`/`。。。`尾缀、确认词、错别字），每组附连发/字数/表情观察。
- **references/craft.md 前端铁律与 mentor 操作手册**：Git/分支七条铁律、发布验证链各步放行条件、CR 六项检查单（含 AI 味三个识别点）、排查七步清单（含语音升级触发）、工时与兜底模板、教学三步操作、前端具体习惯十条。
- 执行流程新增"输出前锚语气 + 建议落 craft 清单"两个强制动作，解决"语气不像、建议太虚"。

## [1.0.0] - 2026-09-03

### Added

- 首个公开发布版本。「拘灵遣将」系列第二个 persona：资深前端 mentor「土豆」。
- **渐进式披露结构**：主 SKILL.md 只保留触发、六模式路由表和输出约束；人设总纲（references/persona.md）、15 条稳定规律（references/principles.md）、分场景输出模板（references/playbook.md）、典型用语库（references/phrases.md）按模式按需加载。
- 核心人设：缓冲层定位——犯错先稳人再止损、自己顶上善后；纠错必附"为什么"并沉淀成规则；教学三步（我演示 → 带你走 → 你独立）；排查提问引导不给答案；工时学员自评 + 明示缓冲 + 兜底承诺显式说出口；碎片化短消息连发 + [捂脸]/[旺柴] 表情系统；对 AI 双轨（自己重度用、学习期学员禁用并讲清原因）。
- 固定输出 `【土豆会这样说】：` + 1~4 条碎片短句；与 lyzbcy-laotian-cosleader（严 leader 式验收）的人设差异表见 persona.md。
- 6 条 evals 用例；每天首次使用静默自更新（三源版本对齐 + 多文件整包原子更新，失败回退旧版）。
