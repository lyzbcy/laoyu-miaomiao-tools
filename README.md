# 捞鱼的妙妙工具 🦞

lyzbcy 系列 OpenClaw Skills 开源合集。

## 包含的 Skills

| Skill 名称 | 功能描述 |
|-----------|---------|
| `lyzbcy-diary` | AI 心情日记系统，每天自动写日记并发送给用户 |
| `lyzbcy-screenshot` | 屏幕截图工具，自动处理 Windows DPI 缩放问题 |
| `lyzbcy-video-planner` | 视频内容规划工具 |
| `lyzbcy-douyin-comment` | 抖音评论自动回复 |
| `lyzbcy-social-comment` | 抖音和小红书统一评论回复 |
| `lyzbcy-social-learning` | AI 社交学习，每天定时去论坛浏览学习 |
| `lyzbcy-task-timer` | 一次性任务提醒管理器 |
| `lyzbcy-XiaohongshuSkills` | 小红书内容发布 |

## 安装方法

将 `skills/` 目录下的文件夹复制到你的 OpenClaw skills 目录：

```bash
# 复制到 ~/.openclaw/skills/ 或 ~/.openclaw/workspace/skills/
cp -r skills/lyzbcy-* ~/.openclaw/skills/
```

或者在 OpenClaw 中使用：

```
openclaw skills install ./skills/lyzbcy-diary
```

## 隐私保护

所有涉及隐私的 skill 都已内置隐私保护规则：
- 私人行程不记录
- 感情细节不记录
- 用户明确说"隐私"的内容绝对不记录

## License

MIT
