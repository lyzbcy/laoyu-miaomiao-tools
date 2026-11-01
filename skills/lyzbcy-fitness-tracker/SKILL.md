---
name: lyzbcy-fitness-tracker
description: 逐组记录健身训练、查询历史与推荐训练安排；用户练完收尾时生成按部位完整列出动作的训练总结长图，并交付当前对话。普通文字模型填模板即可，无需生图额度；可选发布到用户自行配置的博客。
metadata:
  version: "1.2.0"
  files:
    - .gitignore
    - ASSETS.md
    - CHANGELOG.md
    - LICENSE
    - SKILL.md
    - assets/daily-poster/fonts/NotoSansSC[wght].ttf
    - assets/daily-poster/fonts/OFL.txt
    - assets/daily-poster/stickers.json
    - assets/daily-poster/stickers/星星布丁精选10-重绘-09-锻炼身体.png
    - assets/daily-poster/stickers/星星布丁精选12-重绘-14-锻炼身体.png
    - assets/daily-poster/stickers/星星布丁精选13-重绘-15-一起加油.png
    - assets/daily-poster/stickers/星星布丁精选2-重绘-12-佩服.png
    - assets/daily-poster/stickers/星星布丁精选9-重绘-06-吃饭.png
    - assets/daily-poster/stickers/星星布丁精选表情-重绘-19-没力气.png
    - assets/daily-poster/stickers/星星布丁精选表情-重绘-20-惊了.png
    - examples/config.example.json
    - examples/demo-records.jsonl
    - examples/exercises.example.json
    - references/challenge-rules.md
    - references/daily-poster.md
    - references/dashboard-publishing.md
    - references/data-format.md
    - references/nutrition-linkage.md
    - references/progression-algorithm.md
    - scripts/add_record.py
    - scripts/daily_poster.py
    - scripts/fitness.py
    - scripts/publish_dashboard.py
    - scripts/requirements-daily-poster.txt
    - scripts/test_daily_poster.py
    - scripts/test_runtime.py
---

# 健身记录与训练小报

每组一条 JSONL，用户报完一组就追加，训练结束时生成总结图。图包含起止时间及口径、训练日、当日与历史负重容量及趣味类比、完整分部位动作清单、高清重绘精选表情、水印和引流信息。模型只填写文案与选图理由，绘图由本地脚本完成。

## 首次使用

在本 skill 根目录执行（Windows可用 `python`，Linux/macOS按环境用 `python3`）：

```bash
python -m pip install -r scripts/requirements-daily-poster.txt
python scripts/fitness.py init --workspace /你的私有数据目录
```

`--workspace` 不填时使用环境变量 `FITNESS_HOME`，否则默认 `~/.lyzbcy-fitness`。数据目录放在 skill 与公开仓库之外；初始化不会覆盖已有记录或配置。只初始化不创建定时任务、不发送消息、不发布博客。

在本地 `config.json` 的 `brand` 设置标题、水印、公众号与口令；默认示例保留作者品牌“捞鱼 / 捞鱼的博客 / 健身”，可以替换。插图署名与授权见 [ASSETS.md](ASSETS.md)。

## 训练中

解析字段与记录口径见 [references/data-format.md](references/data-format.md)。例如：

```bash
python scripts/add_record.py --data-dir /你的私有数据目录 session_start --session pull
python scripts/add_record.py --data-dir /你的私有数据目录 set --exercise 坐姿划船 --weight 35 --reps 12
```

未知动作补充用户自己的 `exercises.json`，或显式传 `--muscle-group`；不要猜未知重量。错记时追加 note，不修改历史。半次动作可记0.5，不擅自乘左右侧或双哑铃系数。逐组记录时不自动发正式总结图。

## 每次练完的收尾

用户明确说“练完了 / 收工”才记结束；仅请求查询、预览不代表收工。

1. 记录真实 `session_end`：`python scripts/add_record.py --data-dir /你的私有数据目录 session_end`。不要因图片或博客失败重复记结束。
2. 按 [references/daily-poster.md](references/daily-poster.md) prepare，模型填标题、训练日、短句与表情理由，然后 render/check。**全部动作与训练组由脚本按主要部位列出，不能只选前三个。**
3. 执行收尾命令：`python scripts/fitness.py finish --workspace /你的私有数据目录 --date YYYY-MM-DD`。它复用新鲜文案，生成并校验 PNG；博客已明确配置启用时，同时更新博客数据。
4. 把返回 `image` 的 **PNG附件发送给当前对话用户**，并报告真实博客结果。这是每次收工的固定步骤，不用另问是否要图。仅报本地路径不等于已发图；使用当前平台实际可用的附件工具或MEDIA协议，确认工具接收成功才说已发送。

博客失败也应交付已生成图片，并如实报告发布失败；图片失败则说明原因，不能虚构图片或发送成功。该脚本不自带任何账号与群发送目标。不另发其他群，不擅自补建定时任务。用户明确要求中途预览/补发时可单独生成，未收工的图标明“训练进行中”。

## 博客与历史

博客默认关闭。明确启用自己的仓库与输出位置后才提交推送，见 [references/dashboard-publishing.md](references/dashboard-publishing.md)。这不是维护者博客的专用上传器，不会替别人改远端地址。公开数据格式为 `schema_version:1` 的聚合 `days` 列表，需要接入用户自己的页面；不假设任意既有看板能直接读取。

查询历史和个人PR时读取用户自己的数据。重量/组数推荐参考 [references/progression-algorithm.md](references/progression-algorithm.md)，结合用户身体感受，不把容量或预估值当成安全保证。营养联动仅在本地配置的数据源可用时读取近3天记录，见 [references/nutrition-linkage.md](references/nutrition-linkage.md)。没有数据就跳过，不虚构营养指标。训练前挑战规则可按需读 [references/challenge-rules.md](references/challenge-rules.md)。

## 随包验证

```bash
python -m unittest discover -s scripts -p "test_*.py"
python scripts/daily_poster.py prepare --records examples/demo-records.jsonl --date 2026-01-05 --out /私有输出目录/demo.json
python scripts/daily_poster.py render --input /私有输出目录/demo.json --out /私有输出目录/demo.png
```

示例全部虚构。截图、训练账本、配置、输出图与审计留在本地。版本与改动见 [CHANGELOG.md](CHANGELOG.md)。
