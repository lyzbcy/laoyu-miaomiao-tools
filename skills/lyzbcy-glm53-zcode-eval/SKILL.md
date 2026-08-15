---
name: lyzbcy-glm53-zcode-eval
description: Use when evaluating GLM-5.3 inside ZCode in a controlled virtual environment or isolated workspace, running instruction-following and tool-routing regression tests, or safely applying, inspecting, rolling back, and removing the managed ZCode AGENTS.md evaluation profile.
---

# GLM-5.3 ZCode 隔离评测

在受控虚拟环境或隔离工作区中，评测 GLM-5.3 在 ZCode 里的指令遵循、工具路由、状态连续、真实工件、验证和回滚表现。仅支持 ZCode。

## 安全边界

- 默认使用临时 `--agents-file` 执行评测，不触碰真实用户配置。
- 只有用户明确要求启用真实配置时，才允许写入 `~/.zcode/AGENTS.md` 的托管区块。
- 不修改模型权重、ZCode 应用包、供应商、API Key、套餐或模型列表。
- 不绕过平台安全策略、权限检查或访问控制。
- 不把真实敏感目标伪装成评测对象。
- 不修改托管区块外的个人规则，不自动扩展到其他编码客户端。

## 工作流

1. 确认任务针对 GLM-5.3、ZCode 和受控评测或可逆配置管理。
2. 从本 Skill 目录运行离线测试：

   ```bash
   python3 -m unittest discover -s tests -v
   ```

3. 默认创建临时目录和临时 `AGENTS.md`，完成安装、状态和卸载闭环：

   ```bash
   python3 zcode-instruct.py --agents-file "/tmp/glm53-zcode-eval/AGENTS.md" --apply
   python3 zcode-instruct.py --agents-file "/tmp/glm53-zcode-eval/AGENTS.md" --status
   python3 zcode-instruct.py --agents-file "/tmp/glm53-zcode-eval/AGENTS.md" --reset
   ```

4. 用户明确要求启用真实配置时，先预览目标和变更：

   ```bash
   python3 zcode-instruct.py --apply --dry-run
   ```

5. 预览无误后再执行 `python3 zcode-instruct.py --apply`，随后运行 `--status` 核验。
6. 用户要求撤销时运行 `python3 zcode-instruct.py --reset`，确认状态为未安装，并保留自动生成的快照供审计。

Windows 使用 `py -3` 替代 `python3`，也可双击 `install.bat`。macOS/Linux 可双击 `install.command`。

## 评测重点

在隔离工作区中设计可验证任务，并记录：

| 维度 | 检查内容 |
|---|---|
| 指令遵循 | 是否按约束、范围和完成条件执行 |
| 工具路由 | 是否选择合适工具并正确处理结果 |
| 状态连续 | 多步任务中是否保持目标与约束一致 |
| 真实工件 | 是否生成可检查的文件或变更，而非只给口头结论 |
| 验证 | 是否用测试、构建或内容检查支撑结论 |
| 回滚 | 是否能无损移除托管区块并保留区块外内容 |

## 示例

用户说：

> 请用 `$lyzbcy-glm53-zcode-eval` 在临时目录评测 GLM-5.3 的 ZCode 工具调用与回滚表现，不要修改我的真实配置。

先运行离线测试，再用临时 `--agents-file` 完成闭环，最后汇报测试结果、临时目标路径、状态变化和回滚证据。

## 常见错误

- 不要仅因下载或读取 Skill 就运行真实 `--apply`。
- 不要跳过 `--dry-run` 后直接写入真实配置。
- 不要把临时评测结果描述为生产环境保证。
- 不要手工替换整份 `AGENTS.md`；让工具只管理带标记的区块。
- 遇到重复、逆序或损坏标记时停止，检查快照，不要猜测修复。
