---
name: lyzbcy-task-timer
description: 一次性任务提醒管理器。当用户要求"安排任务/排期/定时提醒/帮我规划今晚"时触发。支持按50/10节奏自动排期、批量创建cron提醒、任务完成后自动清理cron，适合频繁使用的一次性工作/学习提醒场景。
---

# lyzbcy-task-timer / 任务提醒管理器

管理用户的一次性任务排期与提醒 cron 生命周期：创建 → 提醒 → 清理。

## 🎯 触发场景

- "帮我安排一下今晚的工作"
- "帮我排个计划，每50分钟休息10分钟"
- "我有几个任务要完成，帮我定个时间表"
- "提醒我做事" + 给出具体任务列表

## 📁 数据结构

```
<workspace>/
└── task-timer/
    └── sessions/
        └── <session-id>.json    # 每次排期的记录
```

### session-id 格式

`YYYY-MM-DD-HHmm`（如 `2026-05-17-2030`）

### session 记录格式

```json
{
  "id": "2026-05-17-2030",
  "createdAt": "2026-05-17T20:30:00+08:00",
  "status": "active | completed | cancelled",
  "schedule": {
    "workMinutes": 50,
    "breakMinutes": 10,
    "advanceNoticeMinutes": 5
  },
  "tasks": [
    {
      "name": "修改PPT",
      "emoji": "📊",
      "durationMinutes": 30,
      "index": 1
    }
  ],
  "timeline": [
    {
      "index": 1,
      "type": "task | break | advance_notice",
      "name": "修改PPT",
      "emoji": "📊",
      "startTime": "2026-05-17T20:12:00+08:00",
      "endTime": "2026-05-17T21:02:00+08:00",
      "cronJobId": "2645fe27-...",
      "status": "pending | fired | skipped"
    }
  ],
  "cronJobIds": [
    "2645fe27-...",
    "ed63303f-..."
  ],
  "completedAt": null
}
```

## 🔧 核心流程

### 1. 创建排期 (`create`)

**输入：** 用户提供任务列表（名称 + 预估耗时）

**处理步骤：**

1. 确认当前时间（`session_status` 获取或 `date` 命令）
2. 按 `workMinutes` / `breakMinutes` 节奏自动排时间表
3. 为每个节点生成 timeline 条目：
   - **task**: 任务开始提醒
   - **break**: 休息提醒
   - **advance_notice**: 提前 5 分钟预警（可选，默认开启）
4. 计算 ISO 时间戳
5. **串行**创建 cron 任务（`openclaw cron add`），每个 cron 都带 `--delete-after-run`
6. 记录所有 cronJobId 到 session 文件
7. 展示排期表给用户

**排期规则：**
- 首个任务：从"现在 + advanceNoticeMinutes"开始
- 工作块时长 = task.durationMinutes（如果 ≤ workMinutes 则用实际时长）
- 如果 task.durationMinutes > workMinutes，拆成多个工作块，中间插休息
- 工作块后插一个 break（10min）
- break 结束前 advanceNoticeMinutes 分钟发提前提醒

**cron 消息模板：**
```
你是一个暖心的提醒助手。请用温暖、有趣的方式提醒用户：<具体提醒内容>。
要求：(1) 不要回复HEARTBEAT_OK (2) 不要解释你是谁 (3) 直接输出提醒消息
(4) 控制在2句话以内 (5) 不要新建定时任务
```

**⚠️ cron 创建注意事项：**
- `--at` 参数必须使用 ISO 时间格式（如 `2026-05-17T18:23:13+08:00`）
- 不支持 `+55m` 这种格式，必须预先计算好 ISO 时间
- **必须串行创建**，并行会导致 gateway 连接冲突（WebSocket 被挤爆）
- 每个创建后 poll 确认成功再创建下一个
- 所有 cron 都带 `--delete-after-run`，执行后自动清理

### 2. 查看排期 (`list`)

列出当前 active 的 session 及其 timeline 状态。

```bash
# 查看所有 cron
openclaw cron list
```

### 3. 调整排期 (`adjust`)

用户反馈进度变化时：
- 任务提前完成 → 后续任务提前
- 任务需要延后 → 整体后移
- 取消某个任务 → 删除对应 cron，重排后续

**调整步骤：**
1. 读取当前 session 文件
2. 删除需要变更的 cron（`openclaw cron remove <id>`）
3. 重新计算 timeline
4. 创建新的 cron
5. 更新 session 文件

### 4. 完成清理 (`complete`)

当最后一个任务完成或用户主动结束：
1. 遍历 session 中所有 cronJobIds
2. 逐个删除未触发的 cron（`openclaw cron remove <id>`）
3. 更新 session status 为 `completed`
4. 已 `--delete-after-run` 的会自动消失，无需手动删

### 5. 清理孤儿 (`cleanup`)

定期检查是否有残留的 active session，提醒用户是否清理。

## 📋 用户交互规范

### 排期确认
创建前展示排期表给用户确认：
```
| 时间段 | 内容 | 耗时 |
|--------|------|------|
| 20:12-21:02 | 📊 修改PPT | 50min |
| 21:02-21:12 | ☕ 休息 | 10min |
```

### 进度反馈
用户随时可以说：
- "PPT做完了" → 标记完成，调整后续
- "强化学习要延后10分钟" → 整体后移
- "VR作业不做了" → 跳过，重排

### 提醒风格
- 温暖、简短、有鼓励感
- 不要啰嗦，不要解释身份
- 休息提醒要催喝水/活动
- 任务开始提醒要有冲劲

## 🔒 约束

- 所有 cron 都是**一次性**的（`--delete-after-run`）
- 不创建重复性 cron（那是日历/闹钟的活）
- session 文件保留历史记录，不自动删除
- 同一时间只维护一个 active session（新 create 前先 complete 旧的）
- 串行创建 cron，禁止并行
