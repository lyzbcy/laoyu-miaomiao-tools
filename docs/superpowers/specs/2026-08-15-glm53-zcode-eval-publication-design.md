# GLM-5.3 ZCode 隔离评测 Skill 发布设计

## 目标

把已完成的 GLM-5.3 ZCode 指令项目收录到公开仓库 `lyzbcy/laoyu-miaomiao-tools`，同时满足三种使用方式：

1. 人类开发者可以阅读源码、运行测试并按需启用评测配置；
2. 支持 Skill 的 AI 可以从网页识别用途、下载 ZIP 并安装；
3. 未安装 Skill 的 AI 也能从网页的纯文本摘要得到稳定的下载直链和合规边界。

## 产品定位

公开名称为 `lyzbcy-glm53-zcode-eval`，中文名为“GLM-5.3 ZCode 隔离评测工具”。

统一描述为：用于受控虚拟环境或隔离工作区中的编码代理回归评测，观察 GLM-5.3 在 ZCode 中的指令遵循、工具路由、状态连续、真实工件、验证和回滚表现，并提供可逆的用户级评测配置管理。

公开说明必须明确：

- 不修改模型权重或 ZCode 应用包；
- 不修改供应商、API Key、套餐或模型列表；
- 不绕过平台安全策略、权限检查或访问控制；
- 不把真实敏感目标伪装成测试对象；
- 默认先在临时 `AGENTS.md` 路径运行隔离测试；
- 只有用户明确要求启用时，才写入 `~/.zcode/AGENTS.md` 的托管区块；
- 安装、更新和卸载均有快照、状态、并发保护和回滚。

页面、Skill 元数据、Release 说明和源码中的定位保持一致，避免使用 `unrestricted`、`jailbreak`、`bypass`、`越狱`、`解禁` 等容易造成误判且与实际功能不符的描述。

## 仓库结构

新增目录：

```text
skills/lyzbcy-glm53-zcode-eval/
├── SKILL.md
├── agents/openai.yaml
├── LICENSE
├── VERSION
├── glm-5.3-zcode-instruct-v1.md
├── zcode-instruct.py
├── install.command
├── install.bat
└── tests/
    ├── __init__.py
    └── test_zcode_instruct.py
```

目录本身既是可审计的开源项目，也是一个可直接放入 Agent Skills 目录的 Skill。`SKILL.md` 同时承担项目说明和 AI 操作规程，不再增加重复 README。

现有未跟踪的仓库根目录 `index.html` 属于用户本地内容，本次不修改、不提交。GitHub Pages 的发布源继续使用已跟踪的 `docs/index.html`。

## Skill 工作流

AI 触发此 Skill 后：

1. 确认任务是 GLM-5.3/ZCode 的受控评测、回归测试或可逆配置管理；
2. 先运行现有 38 项离线测试；
3. 默认以临时 `--agents-file` 执行安装—状态—卸载闭环，不触碰真实 ZCode 配置；
4. 用户明确要求启用真实配置时，先运行 `--dry-run`，展示目标与变更范围，再执行 `--apply`；
5. 启用后用 `--status` 核验；用户要求撤销时运行 `--reset` 并确认托管区块已移除；
6. 不修改区块外内容，不自动扩展到其他编码客户端。

## 网页与 README

`README.md` 的 Skill 表新增一行。

`docs/index.html`：

- Skill 数量从 4 改为 5；
- 新增独立卡片，包含用途、适合/不适合、示例提示词、安装方式、源码和 ZIP 直链；
- AI 说明区增加第五个 Skill；
- `RELEASES` 增加稳定硬编码直链；
- 复制给 AI 的纯文本摘要增加完整合规说明和下载地址。

页面保留当前暗色样式和现有信息架构，不做无关重构。

## 打包与发布

发布版本使用聚合仓库下一个未占用标签 `v1.5.0`，Release 资产名为：

```text
lyzbcy-glm53-zcode-eval.zip
```

ZIP 顶层必须只有一个 `lyzbcy-glm53-zcode-eval/` 文件夹，解压后可直接放入 Agent Skills 目录。

Release 标题为“v1.5.0 · GLM-5.3 ZCode 隔离评测工具”，说明中列出定位、边界、平台、测试数量和安装方式。

## 验证

发布前：

- 用 `quick_validate.py` 验证 Skill 结构；
- 运行项目 38 项单元测试和 Python 语法检查；
- 在临时中文路径完成安装—状态—卸载冒烟测试；
- 检查 ZIP 目录结构、文件清单与无敏感信息；
- 检查 HTML 中 Skill 数量、卡片 ID、源码链接、Release 直链和 AI 摘要一致；
- 检查仓库差异不包含本地未跟踪的根 `index.html`。

发布后：

- 验证 GitHub main 分支包含 Skill；
- 验证 Release 资产返回 HTTP 200；
- 等待 GitHub Pages 更新并验证页面出现新卡片、合规说明和可用下载链接。
