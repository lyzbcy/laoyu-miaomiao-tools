# GLM-5.3 ZCode 隔离评测 Skill 发布实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已验证的 GLM-5.3 ZCode 隔离评测项目收录为可审计、可直接下载安装的 Skill，并在 `lyzbcy/laoyu-miaomiao-tools` 的 README、GitHub Pages 与 v1.5.0 Release 中发布。

**Architecture:** 以 `skills/lyzbcy-glm53-zcode-eval/` 作为源码和 Skill 的唯一事实来源，复用独立项目中已经通过 38 项测试的实现，仅新增精简的 `SKILL.md` 与 `agents/openai.yaml`。网页和 README 只引用该目录与固定 Release 资产；ZIP 保留单一顶层目录，便于 AI 直接安装。

**Tech Stack:** Python 3 标准库、`unittest`、Shell/Windows Batch 安装入口、Agent Skills Markdown/YAML、静态 HTML、GitHub Releases、GitHub Pages。

---

### Task 1: 建立 Skill 骨架并导入已验证实现

**Files:**
- Create: `skills/lyzbcy-glm53-zcode-eval/SKILL.md`
- Create: `skills/lyzbcy-glm53-zcode-eval/agents/openai.yaml`
- Create: `skills/lyzbcy-glm53-zcode-eval/LICENSE`
- Create: `skills/lyzbcy-glm53-zcode-eval/VERSION`
- Create: `skills/lyzbcy-glm53-zcode-eval/glm-5.3-zcode-instruct-v1.md`
- Create: `skills/lyzbcy-glm53-zcode-eval/zcode-instruct.py`
- Create: `skills/lyzbcy-glm53-zcode-eval/install.command`
- Create: `skills/lyzbcy-glm53-zcode-eval/install.bat`
- Create: `skills/lyzbcy-glm53-zcode-eval/tests/__init__.py`
- Create: `skills/lyzbcy-glm53-zcode-eval/tests/test_zcode_instruct.py`

- [ ] **Step 1: 运行不存在性检查，确认新 Skill 尚未实现**

Run: `test ! -e skills/lyzbcy-glm53-zcode-eval`

Expected: PASS；目录不存在。

- [ ] **Step 2: 用官方脚手架初始化 Skill**

Run:

```bash
python3 /Users/zeen/.codex/skills/.system/skill-creator/scripts/init_skill.py \
  lyzbcy-glm53-zcode-eval \
  --path skills \
  --interface 'display_name=GLM-5.3 ZCode 隔离评测' \
  --interface 'short_description=受控环境中的 ZCode 指令与工具调用回归评测' \
  --interface 'default_prompt=Use $lyzbcy-glm53-zcode-eval to run an isolated GLM-5.3 ZCode regression evaluation.'
```

Expected: 创建 `SKILL.md` 和 `agents/openai.yaml`，且默认提示明确包含 `$lyzbcy-glm53-zcode-eval`。

- [ ] **Step 3: 导入已经验证的项目文件**

从 `/Users/zeen/Documents/共享/创业/glm-5.3-instruct-zcode-v1/` 复制 `LICENSE`、`VERSION`、`glm-5.3-zcode-instruct-v1.md`、`zcode-instruct.py`、`install.command`、`install.bat` 和 `tests/` 到 Skill 目录。不得复制 `.git/`、原项目 `README.md`、缓存、构建产物或凭据。

- [ ] **Step 4: 编写最小且合规的 Skill 操作规程**

`SKILL.md` frontmatter 只保留：

```yaml
---
name: lyzbcy-glm53-zcode-eval
description: Use when evaluating GLM-5.3 inside ZCode in a controlled virtual environment or isolated workspace, running instruction-following and tool-routing regression tests, or safely applying, inspecting, rolling back, and removing the managed ZCode AGENTS.md evaluation profile.
---
```

正文必须要求：默认使用临时 `--agents-file`；真实配置只有在用户明确要求后才允许 `--dry-run` 再 `--apply`；启用后检查 `--status`；撤销时使用 `--reset`；不修改模型、应用包、供应商、凭据、套餐或模型列表；不绕过任何安全策略、权限或访问控制；不把真实敏感目标伪装成评测对象。

- [ ] **Step 5: 运行结构校验**

Run:

```bash
python3 /Users/zeen/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/lyzbcy-glm53-zcode-eval
```

Expected: `Skill is valid!`

- [ ] **Step 6: 提交 Skill 源码**

```bash
git add skills/lyzbcy-glm53-zcode-eval
git commit -m "feat: add GLM-5.3 ZCode evaluation skill"
```

### Task 2: 验证实现与可逆配置流程

**Files:**
- Test: `skills/lyzbcy-glm53-zcode-eval/tests/test_zcode_instruct.py`
- Test: `skills/lyzbcy-glm53-zcode-eval/zcode-instruct.py`

- [ ] **Step 1: 运行完整单元测试**

Run:

```bash
python3 -m unittest discover -s skills/lyzbcy-glm53-zcode-eval/tests -v
```

Expected: `Ran 38 tests` 与 `OK`。

- [ ] **Step 2: 运行 Python 语法检查**

Run:

```bash
python3 -m py_compile skills/lyzbcy-glm53-zcode-eval/zcode-instruct.py skills/lyzbcy-glm53-zcode-eval/tests/test_zcode_instruct.py
```

Expected: 退出码 0，无输出。

- [ ] **Step 3: 在临时中文路径执行安装—状态—卸载闭环**

使用 `mktemp -d` 创建临时根目录，在其中文子目录放置 `AGENTS.md`；依次运行 `--agents-file <临时路径> --apply`、`--status`、`--reset`，验证安装后托管区块存在、状态为 installed、卸载后托管区块不存在，并删除临时目录。执行前后计算 `~/.zcode/AGENTS.md` 的 SHA-256；真实文件不存在时记录为 `absent`，两次结果必须一致。

- [ ] **Step 4: 清除测试生成的缓存并确认工作区范围**

Run: `find skills/lyzbcy-glm53-zcode-eval -type d -name __pycache__ -prune -exec rm -rf {} +`

Expected: `git status --short` 只出现计划内文件和用户原有的未跟踪根 `index.html`。

### Task 3: 更新仓库索引与 AI 友好网页

**Files:**
- Modify: `README.md`
- Modify: `docs/index.html`

- [ ] **Step 1: 添加发布前的内容断言并确认失败**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
readme = Path('README.md').read_text()
page = Path('docs/index.html').read_text()
assert 'lyzbcy-glm53-zcode-eval' in readme
assert '收录的 Skills（5 个）' in page
assert page.count('lyzbcy-glm53-zcode-eval.zip') >= 3
PY
```

Expected: FAIL，因为第五个 Skill 尚未写入索引。

- [ ] **Step 2: 更新 README Skill 表**

新增 `lyzbcy-glm53-zcode-eval` 行，描述为“在受控虚拟环境或隔离工作区中评测 GLM-5.3 在 ZCode 里的指令遵循、工具路由、状态连续、工件验证和回滚能力”，下载链接指向 v1.5.0 Release 页面或资产直链。

- [ ] **Step 3: 更新 GitHub Pages 页面**

将数量改为 5；新增 `id="glm53-zcode-eval"` 卡片，包含用途、适合/不适合、示例提示词、默认隔离执行说明、明确合规边界、源码链接及 `v1.5.0/lyzbcy-glm53-zcode-eval.zip` 直链。同步更新“给 AI 的说明”、硬编码 `RELEASES`、按钮赋值以及复制给 AI 的纯文本摘要。

- [ ] **Step 4: 运行内容断言并确认通过**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
readme = Path('README.md').read_text()
page = Path('docs/index.html').read_text()
required = [
    'lyzbcy-glm53-zcode-eval',
    '收录的 Skills（5 个）',
    'id="glm53-zcode-eval"',
    '不修改模型权重或 ZCode 应用包',
    '不绕过平台安全策略、权限检查或访问控制',
    'releases/download/v1.5.0/lyzbcy-glm53-zcode-eval.zip',
]
assert 'lyzbcy-glm53-zcode-eval' in readme
for text in required:
    assert text in page, text
assert page.count('lyzbcy-glm53-zcode-eval.zip') >= 3
PY
```

Expected: PASS。

- [ ] **Step 5: 提交索引与网页**

```bash
git add README.md docs/index.html
git commit -m "docs: publish GLM-5.3 ZCode evaluation skill"
```

### Task 4: 打包并执行发布前审计

**Files:**
- Package source: `skills/lyzbcy-glm53-zcode-eval/`
- Create outside repository: `/tmp/lyzbcy-glm53-zcode-eval.zip`

- [ ] **Step 1: 创建单顶层目录 ZIP**

从 `skills/` 目录运行 `zip -r`，排除 `__pycache__`、`*.pyc`、`.DS_Store` 与隐藏 Git 内容，输出到临时目录，避免将二进制发布资产提交到源码仓库。

- [ ] **Step 2: 审计 ZIP 文件清单**

Run: `unzip -Z1 <zip路径>`

Expected: 所有条目都以 `lyzbcy-glm53-zcode-eval/` 开头；仅包含设计列出的 10 个文件/目录；不存在第二个顶层目录、缓存、`.git` 或原项目 README。

- [ ] **Step 3: 扫描敏感信息与误导性措辞**

对 Skill 源码和 ZIP 解压内容搜索 `ghp_`、`github_pat_`、`api[_-]?key`、`token`、`password` 以及设计明确避免的误导性词汇。测试中的通用字段名可人工判定，实际凭据模式必须为零命中；公开说明不得出现设计禁止的定位用词。

- [ ] **Step 4: 运行完整发布前验证**

重新执行 quick validation、38 项测试、语法检查、HTML 断言与 `git diff --check`。随后用 `git status --short` 确认根目录 `index.html` 仍为未跟踪且未进入任何提交。

### Task 5: 推送、创建 v1.5.0 Release 并验证线上结果

**Files:**
- Push: committed `main`
- Release asset: `/tmp/lyzbcy-glm53-zcode-eval.zip`

- [ ] **Step 1: 推送 main**

Run: `git push origin main`

Expected: 远端 `main` 更新到本地发布提交。

- [ ] **Step 2: 创建并推送标签**

Run:

```bash
git tag -a v1.5.0 -m "GLM-5.3 ZCode isolated evaluation skill v1.5.0"
git push origin v1.5.0
```

Expected: 远端出现 `v1.5.0` 标签。

- [ ] **Step 3: 通过 GitHub API 创建 Release 并上传 ZIP**

从 `/Users/zeen/.agents/skills/lyzbcy-git/credentials/github-token` 读取令牌到进程变量，禁止打印或写入仓库。Release 标题使用 `v1.5.0 · GLM-5.3 ZCode 隔离评测工具`；正文说明受控环境定位、默认临时配置、合规边界、仅支持 ZCode、38 项测试和安装方式；上传 `lyzbcy-glm53-zcode-eval.zip`。

- [ ] **Step 4: 验证 GitHub 源码、Release 资产和 Pages**

检查 GitHub API 返回的 tag、asset 名称与资产大小；请求 main 分支 Skill 目录和 Release 资产，必须返回 HTTP 200。轮询 GitHub Pages（每次不超过 60 秒，总计不超过 10 分钟），直到页面正文包含 `lyzbcy-glm53-zcode-eval`、合规说明和 v1.5.0 资产直链。

- [ ] **Step 5: 最终工作区核验**

Run: `git status --short --branch && git log -5 --oneline --decorate`

Expected: `main` 与 `origin/main` 同步；唯一额外状态为用户原有的未跟踪 `index.html`；`v1.5.0` 指向发布提交。
