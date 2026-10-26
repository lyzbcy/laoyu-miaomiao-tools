---
name: lyzbcy-shared-regression
description: 为项目创建和维护 PRD/设计稿对照与人工AI共享回归台，关联用例、真实页面、资料和检查点，分别记录人工与自动结果。适用于搭建对照台、更新设计引用、解释测试步骤和回归接管。
metadata:
  version: 0.1.0
  files:
    - SKILL.md
    - CHANGELOG.md
    - references/workflow.md
    - scripts/qa.py
    - scripts/update_skill.py
    - assets/index.html
    - assets/cases.json
    - update.json
---

# PRD 对照与共享回归

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
