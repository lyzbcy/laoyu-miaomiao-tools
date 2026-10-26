---
name: lyzbcy-shared-regression
description: 为项目创建和维护 PRD/设计稿对照与人工AI共享回归台，关联用例、真实页面、资料和检查点，分别记录人工与自动结果。适用于搭建对照台、更新设计引用、解释测试步骤和回归接管。
metadata:
  version: 0.1.2
  files:
    - SKILL.md
    - CHANGELOG.md
    - references/workflow.md
    - references/build.md
    - scripts/qa.py
    - scripts/update_skill.py
    - assets/index.html
    - assets/cases.json
    - update.json
---

# PRD 对照与共享回归

## 核心体验与完成标准

对照台优先解决四件事，执行记录是配套能力：

1. **找准对应设计图**：按当前用例、实际入口和界面状态选图，保留版本与来源；切换用例同步切图，不能统一落到整节或主列表。
2. **独立 PRD 窗口**：复用或新开独立窗口，支持系统级强制置顶/取消置顶；按当前用例定位并蓝选准确的原文正文。新标签页、抢焦点、CSS 浮层或选中目录不能替代这些能力。
3. **辅助演示**：按当前用例提供可执行的逐步/自动演示，展示当前步骤，支持停止和必要的草稿/临时状态恢复；不能只有文字步骤，也不能将演示完成当业务通过。
4. **本地服务就绪与预载**：启动依赖经过实际HTTP/连接验证；当前页面稳定后有界预载后续设计图和适合的本地只读页。预载可关闭、可失效、可复用，不能重复启动服务或反复销毁iframe。

**构建或改版之前先读 [构建约束与已知问题](references/build.md)**，落实初始化、入口/资料映射、身份与版本恢复、PRD窗口、演示和预载生命周期，再补记录与自动化。已有平台优先复用，避免重新踩坑。

能力缺失明确列待补，不用HTTP冒烟或结果表单代替。当前随包模板仅提供手动引用选择、链接打开、结果记录和HTTP检查；尚未通用化精准选图、独立PRD窗口置顶/正文蓝选、辅助演示和业务页预载适配器。0.1.1–0.1.2校正指导与构建验收，不宣称模板已实现这些能力。

每天首次使用先执行 `python <skill目录>/scripts/update_skill.py --background`。后台按日检查远端版本，校验完整文件集后更新；失败保留旧版，不打断当前任务。项目数据留在 skill 目录外，不受更新影响。

## 开始使用

需要 Python 3.10+，基础版只用标准库。使用绝对路径运行脚本，以下 `<项目回归目录>` 是用户项目中的独立 QA 目录。

```text
python <skill目录>/scripts/qa.py --project <项目回归目录> init
python <skill目录>/scripts/qa.py --project <项目回归目录> list
python <skill目录>/scripts/qa.py --project <项目回归目录> serve --port 5182
```

`init` 创建合成示例用例和本地页面，不覆盖已有文件。浏览器打开命令显示的本机地址。把示例 `cases.json` 换成当前项目真实用例、真实页面入口、PRD和设计引用；先与用户确认本次范围，再创建批次。端口被占用时选择空闲端口，不替换现有服务。

```text
python <skill目录>/scripts/qa.py --project <项目回归目录> create --build 实际被测版本
python <skill目录>/scripts/qa.py --project <项目回归目录> run 批次ID --ids 用例ID
python <skill目录>/scripts/qa.py --project <项目回归目录> summary 批次ID
python <skill目录>/scripts/qa.py --project <项目回归目录> summary 批次ID --case 用例ID
```

首版自动执行只覆盖显式配置的 HTTP GET 状态码和正文片段检查；默认合成示例无自动检查。浏览器交互、持久化回读、权限矩阵和视觉验收由人工或另行适配的浏览器执行器完成。不要把 HTTP 冒烟通过说成业务或设计验收通过。

## 工作规则

- 先读选中用例和摘要，失败再展开相关证据；不反复加载全量PRD、截图与日志。
- 每条预期拆成检查点；未覆盖显示 pending/partial，缺前置记 blocked，不猜测通过。合成样例只验证工具自身。
- 人工、AI代理与自动结果分别追加；不同执行者的失败/通过分歧保留 conflict。AI代理不冒充真人。
- 批次冻结用例版本；定义变化标 stale，新建批次。保留历史，不改旧数据库成绩，也不将辅助演示自动记为通过。
- 项目路径、账号、真实用例和证据由使用者本地配置；不把公司PRD、设计图、登录信息或个人数据传到公共仓库。此工具仅监听回环地址，无跨电脑共享、登录同步或内置账号能力。

维护映射、接入已有平台、制定人工步骤或扩展自动化时，读 [工作流与数据格式](references/workflow.md)。已有成熟回归台优先复用数据和适配器，不为使用本 skill 强制重建。
