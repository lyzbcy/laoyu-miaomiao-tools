# GLM-5.3 ZCode Skill 明确同意门控实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `lyzbcy-glm53-zcode-eval` 只有在用户把“请使用 LYZBCY 虚拟环境测试”作为明确启用指令时才能运行，并在网页和下载包中同步说明潜在表现影响与询问机制。

**Architecture:** 使用平台元数据、Skill 正文硬门槛和公开介绍三层防护。命令行安装器保持不变，因为对话授权由调用 Skill 的 AI 判断；发布新的聚合版本 `v1.5.1`，保留 `v1.5.0` 供审计。

**Tech Stack:** Agent Skills Markdown/YAML、Python `unittest`、静态 HTML、GitHub Releases、GitHub Pages。

---

### Task 1: 先写明确同意门控测试

**Files:**
- Modify: `skills/lyzbcy-glm53-zcode-eval/tests/test_zcode_instruct.py`
- Test: `skills/lyzbcy-glm53-zcode-eval/SKILL.md`
- Test: `skills/lyzbcy-glm53-zcode-eval/agents/openai.yaml`

- [ ] 在 `PackagingTests` 新增 `test_skill_requires_explicit_activation_phrase`，读取 `SKILL.md` 并断言存在唯一口令、缺少口令时不得执行命令、仅引用口令不算授权以及授权不跨任务延续。
- [ ] 新增 `test_skill_disables_implicit_invocation`，读取 `agents/openai.yaml` 并断言 `allow_implicit_invocation: false`。
- [ ] 运行两项新测试，预期因当前 Skill 没有这些门控而失败。

### Task 2: 实现 Skill 和元数据门控

**Files:**
- Modify: `skills/lyzbcy-glm53-zcode-eval/SKILL.md`
- Modify: `skills/lyzbcy-glm53-zcode-eval/agents/openai.yaml`

- [ ] 将 frontmatter description 改为只在当前用户明确发出唯一口令时使用。
- [ ] 在正文最前加入硬门槛：没有有效口令时立即停止，不运行测试、安装器或配置命令；需要时先警告潜在表现影响并询问，要求用户明确回复唯一口令。
- [ ] 明确排除引用、讨论、近义表达、Skill 名称、`$skill` 和历史授权；授权仅限当前任务。
- [ ] 在 `openai.yaml` 加入 `policy.allow_implicit_invocation: false`，并把默认提示改为只解释门控和询问，不直接启用。
- [ ] 运行新测试、完整测试与 `quick_validate.py`，预期 40 项测试全部通过且 Skill 有效。

### Task 3: 更新 README 与介绍页

**Files:**
- Modify: `README.md`
- Modify: `docs/index.html`

- [ ] 先运行内容断言，确认页面尚无唯一口令、潜在表现影响、询问机制和 `v1.5.1` 链接，因此失败。
- [ ] 更新 README 表格描述和下载直链，明确“默认关闭，仅凭唯一口令启用”。
- [ ] 更新网页卡片、示例 prompt、安装说明、AI 说明区和复制摘要，写清楚潜在表现影响、精确口令、引用不算授权、AI 必须先询问。
- [ ] 将所有 GLM-5.3 Skill 下载链接从 `v1.5.0` 更新为 `v1.5.1`。
- [ ] 运行内容断言和内联 JavaScript 语法检查，预期全部通过。

### Task 4: 完整验证与打包

**Files:**
- Package source: `skills/lyzbcy-glm53-zcode-eval/`
- Create outside repository: temporary `lyzbcy-glm53-zcode-eval.zip`

- [ ] 运行 40 项单元测试、Python 语法检查、官方 Skill 校验和 HTML 断言。
- [ ] 在临时中文路径运行安装—状态—卸载闭环，并验证真实 `~/.zcode/AGENTS.md` 摘要前后一致。
- [ ] 打包单一顶层目录 ZIP，精确核对 10 个文件、源码逐字节一致、无缓存、无凭据和无误导性定位用词。
- [ ] 确认工作区唯一无关状态仍是用户原有的未跟踪根 `index.html`。

### Task 5: 发布 v1.5.1 并验证线上结果

**Files:**
- Push: committed `main`
- Release asset: temporary `lyzbcy-glm53-zcode-eval.zip`

- [ ] 提交 Skill、测试、README 和网页修改，推送 `main`。
- [ ] 创建并推送 `v1.5.1` 标签。
- [ ] 使用本机 lyzbcy GitHub 凭据创建 Release，说明默认关闭、潜在表现影响、唯一口令、询问机制和 40 项测试；上传 ZIP，绝不打印凭据。
- [ ] 验证 GitHub 源码、Release 元数据、ZIP HTTP 200 与 SHA-256，并等待 Pages 出现唯一口令、询问机制和 `v1.5.1` 直链。
- [ ] 确认本地 `main`、远端 `main` 与 `v1.5.1` 指向同一提交，保留用户未跟踪的 `index.html`。
