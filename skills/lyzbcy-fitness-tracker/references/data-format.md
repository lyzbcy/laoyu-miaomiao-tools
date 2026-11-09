# records.jsonl 数据格式详解

> 由 SKILL.md 拆出。记录/解析训练数据时读取本文件。

每条记录 = 一次数据点（通常是一组），**追加写入**。

## 标准字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `ts` | ISO8601 | ✅ | 记录创建时间 |
| `endTime` | ISO8601 | set/bodyweight必填 | 实际训练事件时间，优先使用用户明确报告的时间 |
| `date` | YYYY-MM-DD | ✅ | 日期，方便按天过滤 |
| `action` | string | ✅ | `set` / `session_start` / `session_end` / `bodyweight` / `note` |
| `exercise` | string | set必填 | 动作名称（如"平板杠铃卧推"） |
| `muscleGroup` | string | set必填 | 主肌群 |
| `session` | string | ✅ | 当日训练类型：`push` / `pull` / `legs` / `upper` / `lower` / `full_body` / `cardio` |
| `setNum` | int | set必填 | 第几组（从1开始） |
| `weight` | number 或 null | set必填 | 可汇总的公斤重量，自重填 0，未标定片数填 null |
| `reps` | number | set必填 | 次数，可记录最后半次（如5.5） |
| `rpe` | int | 可选 | 感知疲劳度 1-10 |
| `note` | string | 可选 | 备注 |

## 肌群枚举

`chest` / `upper_chest` / `back` / `lats` / `mid_back` / `shoulders` / `lateral_delt` / `rear_delt` / `biceps` / `triceps` / `quads` / `hamstrings` / `glutes` / `calves` / `core` / `forearms`

## 示例数据

```jsonl
{"ts":"2026-06-01T15:00:00+08:00","date":"2026-06-01","action":"session_start","session":"push","note":"今天练推"}
{"ts":"2026-06-01T15:05:00+08:00","date":"2026-06-01","action":"set","exercise":"平板杠铃卧推","muscleGroup":"chest","session":"push","setNum":1,"weight":40,"reps":15,"rpe":5,"note":"热身"}
{"ts":"2026-06-01T15:08:00+08:00","date":"2026-06-01","action":"set","exercise":"平板杠铃卧推","muscleGroup":"chest","session":"push","setNum":2,"weight":60,"reps":10,"rpe":7,"note":""}
{"ts":"2026-06-01T15:12:00+08:00","date":"2026-06-01","action":"set","exercise":"平板杠铃卧推","muscleGroup":"chest","session":"push","setNum":3,"weight":60,"reps":8,"rpe":9,"note":"力竭了"}
{"ts":"2026-06-01T15:18:00+08:00","date":"2026-06-01","action":"set","exercise":"上斜哑铃卧推","muscleGroup":"upper_chest","session":"push","setNum":1,"weight":22.5,"reps":12,"rpe":7,"note":""}
{"ts":"2026-06-01T15:30:00+08:00","date":"2026-06-01","action":"session_end","session":"push","note":"练完了"}
```

## 特殊 action 类型

**session_start** — 用户说"开始练了"、"今天练胸"时插入：
```jsonl
{"ts":"...","date":"...","action":"session_start","session":"push","note":"今天练推"}
```

**session_end** — 用户说"练完了"、"收工"时插入：
```jsonl
{"ts":"...","date":"...","action":"session_end","session":"push","note":"练完了，感觉不错"}
```

**bodyweight** — 记录体重：
```jsonl
{"ts":"...","date":"...","action":"bodyweight","value":72.5,"unit":"kg"}
```

## ⏱️ endTime 与休息时间计算

有明确时间用 `--date YYYY-MM-DD --time HH:MM`，写入 `endTime`。只有实时汇报且未提供具体时间时，才用当前时间。训练结束也支持该参数。

`--weight 30 --weight-unit lb` 保存 `reportedWeight: 30`、`reportedUnit: "lb"`，按 1 lb = 0.45359237 kg 填写 `weight`。`--weight 4.5 --weight-unit plate --equipment 示例器械A` 保存片数和器械来源。没有对应估算时 `weight` 为 null。私有配置中的 `plate_estimates` 可按器械名称提供 `kg_per_plate` 和 `source`，匹配时写入估算的公斤数与 `weightEstimated`。小报保留原片数，估算公斤数和含估算的容量以“约”标识。

**休息时间公式：**
```
restSeconds = (当前组endTime - 上一组endTime) - 上一组动作的estimatedDurationSeconds
```
即：两组结束时间间隔，减去上一组动作的估时 = 休息时间。

**估时从 `exercises.json` 读取**，每个动作的 `estimatedDurationSeconds` 字段：
- 复合动作（深蹲、硬拉、卧推等）：40~55秒
- 孤立动作（弯举、侧平举、卷腹等）：25~30秒
- 热身组同样按动作估时

第一组无上组，不计算休息时间；换动作后第一组只算与上组结束时间的间隔。

## 🚨 记录规则（严格遵守）

1. **每组一条** — 用户说"卧推60做了10个"→ 追加一条 set 记录
2. **自动推断 setNum** — 查当天同一 exercise 已有几条，+1 即为当前组号
3. **自动推断 session** — 查当天 session_start 或最近的记录确定 session 类型
4. **自动推断 muscleGroup** — 从 exercises.json 匹配，找不到则根据动作名推断
5. **endTime = 实际训练时间** — 补录按用户每组给出的时刻填写，`ts` 保留录入时刻
6. **自动计算休息时间** — 查上一条 set/bodyweight 的 endTime 和估时，算出差值回复用户
7. **只追加不修改** — 从不修改已有记录，如果用户说"刚才那组记错了"→ 追加一条 note 类型记录说明

## ❌ 用户输入 → ✅ 系统解析示例

| 用户说的 | 解析为 |
|---------|--------|
| "卧推60做了10个" | exercise=平板杠铃卧推, weight=60, reps=10 |
| "刚才那组推了8个就力竭了" | reps=8, note="力竭"（setNum 自动推断） |
| "换个动作，上斜哑铃22.5" | exercise=上斜哑铃卧推, weight=22.5（reps 等用户补或问） |
| "深蹲80，5组5个" | 追加5条 set 记录，weight=80, reps=5 |
| "感觉RPE 9" | 追加 note，注明对应组及RPE；不覆盖旧行 |
| "练完了" | session_end |

## 🫀 有氧记录（action: "cardio"）

> 2026-08-23 打样定稿。首次全量导入 Apple 健康/Watch 历史数据时建立。

### 字段 schema

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `ts` | ISO8601 | ✅ | 记录创建时间（有氧结束时） |
| `date` | YYYY-MM-DD | ✅ | 日期 |
| `action` | string | ✅ | 固定 `cardio` |
| `session` | string | ✅ | 固定 `cardio` |
| `exercise` | string | ✅ | 有氧类型中文名：`游泳` / `跑步` / `骑行` / `HIIT` / `跳绳` / `爬楼` / `快走` / `篮球` / `网球` / `羽毛球` 等 |
| `durationMin` | float | ✅ | 时长（分钟），支持小数（如 37.5） |
| `distanceKm` | float | 可选 | 距离（km），跑步/骑行/快走填，游泳/跳绳/爬楼不填 |
| `avgHr` | int | 可选 | 平均心率（bpm），来自手表或手环 |
| `intensity` | string | 可选 | 强度：`低`(<110) / `中`(110-135) / `高`(>135)，可由 avgHr 自动推断，也可用户口述 RPE 换算 |
| `activeKcal` | float | 可选 | 活动消耗（kcal） |
| `strokes` | int | 可选 | 划次（仅游泳） |
| `rpe` | int | 可选 | 感知疲劳度 1-10（与力量共用） |
| `source` | string | 可选 | 数据来源：`Apple Watch 导入` / `口述` / `Keep` 等 |
| `note` | string | 可选 | 备注（如游泳可记泳池长度、配速感受） |

### 示例

```jsonl
{"ts":"2026-08-20T21:06:00+08:00","date":"2026-08-20","action":"cardio","session":"cardio","exercise":"游泳","durationMin":27,"avgHr":111,"intensity":"中","activeKcal":198.2,"strokes":401,"source":"Apple Watch 导入","note":"20:39-21:06"}
{"ts":"2026-08-23T20:44:00+08:00","date":"2026-08-23","action":"cardio","session":"cardio","exercise":"爬楼","durationMin":37,"avgHr":128,"intensity":"中","activeKcal":306.6,"source":"Apple Watch 导入"}
```

### 记录规则

1. **一次有氧一条记录**（不像力量每组一条）
2. 用户口述时尽量补齐 `durationMin`（必填）+ 至少一项质量指标（avgHr / distanceKm / activeKcal）
3. 跑步若有 distanceKm，回复时可换算配速（`配速 = durationMin / distanceKm`，格式 5'30"/km）
4. 与力量同日训练：照常追加 cardio 记录，session 仍为 `cardio`，不与力量 session 混淆

## 📋 辅助 action 类型

**session_summary** — 历史力量训练摘要（只有时长/心率/热量，无逐组明细，来自 Apple Watch 批量导入）：
```jsonl
{"ts":"2025-01-15T20:00:00+08:00","date":"2025-01-15","action":"session_summary","session":"strength","durationMin":75,"activeKcal":410.2,"avgHr":118,"source":"Apple Watch 导入"}
```

**vo2max** — 最大摄氧量（有氧能力核心指标）：
```jsonl
{"ts":"2026-08-01T12:00:00+08:00","date":"2026-08-01","action":"vo2max","value":42.5,"unit":"ml/kg/min","source":"Apple 健康导入"}
```

## 器械片数估算
用同动作、接近的用力程度和有刻度器械作对照，给目标器械建立一个等效负重参考。若对照重量为 W 公斤、次数为 R，目标器械使用 P 片完成 N 次，可按 W × (30 + R) ÷ (P × (30 + N)) 粗估公斤/片。它反映训练表现的等效重量，无法测出配重片的实物重量。器械或滑轮设置变更时应重新核对。

只在私有工作区的 `runtime.local.json` 配置 `plate_estimates`。按器械名分别设定 `kg_per_plate` 和 `source`，来源写明对照条件。录入使用同名 `--equipment`。公开模板使用示例值，实际估算参数随本机环境保存。
