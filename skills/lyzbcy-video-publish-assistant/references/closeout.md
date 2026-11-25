# 投稿回执与收尾

在同一项目的 `run-summary.md` 追加结果。已有制作段保留，发布阶段合并一次交付。回执包含采用的成片与封面、实际核验、逐平台账号/目标/状态/作品链接、各平台 AI 声明状态、待办和必要的恢复记录。制作历史未知就省略版数。

尚待审核或结果不明时给阶段回执，记 `closeout_status: partial` 并保留断点。目标达成或用户接受未决项后，才记 `summary_sent`。沿用 `closeout_owner` 和已收到的答复，续发只追加本轮结果。

## 旧版本多或占用大时，主动提醒清理

只盘点本项目，复用 `cleanup-plan.md`。替代版本至少 3 个、候选约 2 GiB 或有实际磁盘压力时，给用户一次可审清单，列实际路径、占用、保留项和预计释放量。保护最终稿、源素材、仍被引用的重建依赖、授权、回执和恢复断点。

按已授权清单核对解析后的路径与依赖，再处理并回读保留项和实测结果。回收站、同盘归档与永久删除分开记录。共享目录的删除会同步。旧片清理与贡献是独立授权。

## 经验贡献

仅当有明确可迁移条件、验证证据和现有规则未覆盖的价值时才准备草案。单片做法留项目。制作与发布共用 `.contribution-tmp/<run-id>/contribution-draft.md` 及创建清单，草案只留脱敏复现、适用范围、验证和候选改动。

最终交付或本轮结束经用户确认后，才就草案和署名询问一次。取得同意后按范围在贡献分支提交 PR，证据及署名范围仅限获准内容。用对应 skill 的 `CONTRIBUTORS.md` 记录获准署名或匿名，以合入为准。没有权限时交可审补丁。用户未答复则保持待定。

用户答复后按创建清单清理本次专属临时文件，执行前核对解析后的路径及目录边界。提交失败先保留可复用的补丁和失败回执。保存实际 PR、最终交付、原工程和凭证文件。

## 持久化收尾检查

独立投稿用 `python scripts/closeout.py init LEDGER` 创建 `closeout.json`。接续制作时只恢复原账本。恢复先 `python scripts/closeout.py status LEDGER`，结束前 `python scripts/closeout.py audit LEDGER`。待办与证据变化按实际修正，账本命令不执行删除、归档或提交 PR。

用 `python scripts/closeout.py record LEDGER --task TASK --status STATUS --evidence FILE` 登记决策和证据。归档核验以 `files` 中的路径和 SHA-256 为准，清理证据记录实际 `deleted` 路径。PR 的 `submitted` 状态需独立授权与实际 PR 链接（`--url`）。无回流价值可记 `not_valuable` / `not_needed`，未答复的清理保留 `awaiting_consent`。
