# lyzbcy-social-comment 使用手册

## 草稿生成

```bash
python scripts/batch_comment_drafts.py runtime/input/comments.csv
python scripts/batch_comment_drafts.py runtime/input/comments.csv runtime/output/drafts.json
```

CSV 列：

```csv
comment,video_topic,intent_hint,priority_hint,notes
多少钱？,AI工具教程,,,
真的有用吗？,AI工具教程,,,
```

## 浏览器执行

```bash
python scripts/browser_reply_runner.py runtime/output/drafts.json --dry-run
python scripts/browser_reply_runner.py runtime/output/drafts.json
```

## 典型流程

1. 把待处理评论整理进 `runtime/input/comments.csv`
2. 运行 `batch_comment_drafts.py` 生成草稿
3. 先用 `browser_reply_runner.py --dry-run` 检查
4. 确认后再正式发送

## 心跳场景

心跳时优先检查新评论并生成草稿；没有新评论时保持静默，不要输出示例内容。

## 交叉边界

- 小红书内容发布：走 `lyzbcy-XiaohongshuSkills`
- 评论回复：走本 skill
