# 离线总结图模板

Python 3.10+、Pillow 11–12；Windows通过随包依赖安装tzdata。字体及七张高清重绘PNG随包提供。流程不调用任何生图服务。

在skill根目录运行，把路径替换为用户自己的目录，日期替换为这次训练日期：

```bash
python scripts/daily_poster.py prepare --records /你的私有数据目录/records.jsonl --config /你的私有数据目录/config.json --date YYYY-MM-DD --out /你的私有数据目录/posters/YYYY-MM-DD.json
python scripts/daily_poster.py catalog
python scripts/daily_poster.py render --input /你的私有数据目录/posters/YYYY-MM-DD.json --out /你的私有数据目录/posters/YYYY-MM-DD.png
python scripts/daily_poster.py check --image /你的私有数据目录/posters/YYYY-MM-DD.png
```

读取生成JSON，只修改 `copy`。事实、组数、重量、动作完整清单由脚本计算。记录变了就重新prepare；render会拒绝过期来源和被修改的facts。`--snapshot`只用于明确重现旧快照。

```json
{
  "title": "全身都安排上了",
  "day_label": "全身训练日",
  "tags": "胸 · 背 · 肩 · 腿",
  "cheer": "今天也认真练了，好好恢复",
  "stickers": {
    "hero_left": "remaster_workout_male",
    "hero_right": "remaster_workout_female",
    "today": "remaster_admire",
    "history": "remaster_surprised",
    "rest": "remaster_rest",
    "meal": "remaster_meal",
    "footer": "remaster_cheer"
  },
  "sticker_reasons": {
    "hero_left": "举臂热身，点明锻炼主题",
    "hero_right": "拿哑铃训练，呼应负重记录",
    "today": "双手点赞，肯定今日训练",
    "history": "惊讶表情表现累计训练量",
    "rest": "提醒练后休息，不推断已力竭",
    "meal": "吃饭表情提醒练后补给",
    "footer": "举拳加油，收尾鼓励继续记录"
  }
}
```

- 标题1–18字、分类1–16字、tags最多60字、cheer最多40字。使用自然语言，按实际动作判断训练日，不只照抄可能沿用错的session。不要用“全身乱活力”等硬造词。
- 七处表情按场景选择：标题workout、今日achievement、历史accumulation、恢复recovery、补给nutrition、页尾encouragement。每处写3–100字理由。随包只含七张重绘原图；可替换为用户自己有权使用的图片，并更新catalog含义。不要用期待约会/亲吻等无关图；看图能力不足时依据目录说明，不谎称已看过。
- **按主要部位完整列出全部动作与组数**，不挑前三项、不以缩小字号掩盖截断。未知肌群列“其他部位”，有氧另列；协同肌不重复计量。同动作可无损合并相同组，画布自动加高。
- 负重容量按原始记录 `weight×reps`，保留半次。自重/未知重量、自然语言更正不自动折算；不擅自补上双侧重量。统计的容量不是机械功/能量。历史截止选定日期。
- 有明确开始/结束记录才称训练起止时间；缺开始显示记录跨度，未结束显示进行中，多段训练标注含间歇。有氧按时长和结束记录推算。
- 小汽车按2吨/辆、大卡车按20吨/辆，仅作趣味类比，图上写清假设。
- `brand` 来自本地config，可修改title/watermark/account/keyword或完整cta。默认口令“健身”。随包图用到角色插图时仍保留“素材：捞鱼”署名，见ASSETS.md。

生成后看图，check通过仅代表文件与边界检查通过。输出PNG和audit不公开上传。用户收工时与博客更新一并交付PNG附件；失败报告实际状态，不重复记结束、不谎报已发。

## 动作 PR
有可比的更早训练组，且当天组在重量和次数上至少一项提高、另一项不退步，才可能标为「新 PR」。当天组与既有成绩并列，或只是在重量与次数之间取舍时，显示历史 PR。记录里只有一次出现或缺少可比口径时，保留动作明细，PR 区留空。

优先展示可由账本核实且仍处于历史最佳范围的 `personalRecords`，其余展示可比记录中重量最高的成绩，同重量取次数最多，同分取首次达成日期。比较会隔开器械标识、辅助与自重、哑铃单手与合计口径。器械片数用原始片数比较，后续修改估算系数不会制造新 PR。PR 不采用报告日之后的数据，历史框里的日期由实际训练组提供。

历史 PR 卡放在动作明细右侧，使用淡紫色底，成绩与日期分行。新 PR 在动作名旁保留橙色徽标。
