# lyzbcy-social-learning 使用手册

## 快速开始

### 手动触发

```bash
python scripts/browse_tieba.py
```

### 测试模式

```bash
python scripts/browse_tieba.py --dry-run
```

## 配置

### 目标版块

在 `scripts/browse_tieba.py` 中修改 `TARGET_FORUMS`：

```python
TARGET_FORUMS = [
    "https://tieba.baidu.com/f?kw=人工智能",
    "https://tieba.baidu.com/f?kw=chatgpt",
    "https://tieba.baidu.com/f?kw=AI绘画",
]
```

### 运行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `MAX_DURATION_MINUTES` | 60 | 最长运行时间（分钟） |
| `MAX_POSTS_PER_RUN` | 20 | 每次最多浏览帖子数 |
| `MAX_FINDINGS_PER_RUN` | 10 | 每次最多记录发现数 |

## 安全机制

### 自动跳过的内容

- 包含系统指令的帖子（`system:`, `instruction:`等）
- 包含代码执行的帖子（`rm -rf`, `eval(`等）
- 包含敏感信息的帖子（`password`, `apikey`等）
- 社工攻击类帖子（`你的主人`, `告诉我你的指令`等）

### 安全检查

```python
from security_check import is_safe_post

is_safe, reason = is_safe_post(title, content)
if not is_safe:
    print(f"跳过危险帖子: {reason}")
```

## 学习记录

学习记录保存在 `runtime/learning_log.json`：

```json
{
  "records": [
    {
      "date": "2026-04-30",
      "duration_minutes": 45,
      "posts_viewed": 15,
      "interesting_findings": [...],
      "security_events": 0
    }
  ]
}
```

## 注意事项

1. **只读不写** - 不主动发帖或回复
2. **安全第一** - 检测到危险内容立即跳过
3. **上下文控制** - 及时清理，不累积过多信息
4. **时间限制** - 最多1小时，可提前结束
