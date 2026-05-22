#!/usr/bin/env python3
"""
评论批量处理脚本
支持：意图分类、回复生成、配置文件、多模板
"""
import csv, json, re, sys
from pathlib import Path

# 获取脚本所在目录
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent

# 默认意图规则
DEFAULT_INTENT_RULES = [
    ("buying_intent", [r"多少钱", r"怎么卖", r"怎么买", r"私信", r"能做吗", r"报名", r"下单", r"联系方式", r"购买"]),
    ("price_objection", [r"太贵", r"贵", r"便宜点", r"最低", r"不值", r"割韭菜", r"不值这个价"]),
    ("skepticism", [r"真的假的", r"真吗", r"骗人", r"智商税", r"吹牛", r"有用吗", r"靠谱吗"]),
    ("support", [r"收不到", r"打不开", r"不能用", r"没反应", r"怎么进去", r"售后", r"退款"]),
    ("engagement", [r"求更", r"第二集", r"继续更", r"想学", r"教程", r"蹲", r"收藏了", r"催更"]),
    ("inquiry", [r"怎么", r"可以吗", r"适合", r"啥", r"是什么", r"如何", r"能不能"]),
]

# 优先级映射
DEFAULT_PRIORITY = {
    "buying_intent": "high",
    "support": "high",
    "price_objection": "medium",
    "skepticism": "medium",
    "inquiry": "high",
    "engagement": "medium",
    "noise": "low",
}


def load_config() -> dict:
    """加载配置文件"""
    config_path = SKILL_DIR / "config.json"
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {"defaultVoice": "professional", "outputDir": "./output"}


def load_templates() -> dict:
    """加载回复模板（合并默认和自定义）"""
    default_path = SKILL_DIR / "templates" / "default.json"
    custom_path = SKILL_DIR / "templates" / "custom.json"

    templates = {}
    if default_path.exists():
        templates = json.loads(default_path.read_text(encoding="utf-8"))

    if custom_path.exists():
        custom = json.loads(custom_path.read_text(encoding="utf-8"))
        # 合并自定义模板（覆盖默认）
        for key, value in custom.items():
            if not key.startswith("_"):
                templates[key] = value

    return templates


def detect_intent(text: str, rules: list = None) -> str:
    """检测评论意图"""
    if rules is None:
        rules = DEFAULT_INTENT_RULES

    t = text.strip().lower()
    for intent, pats in rules:
        for p in pats:
            if re.search(p, t, flags=re.I):
                return intent
    if len(t) <= 2:
        return "noise"
    return "inquiry"


def get_reply(intent: str, templates: dict, voice: str = "professional") -> tuple:
    """获取回复内容"""
    prefix = templates.get("prefix", "🦞 ")
    suffix = templates.get("suffix", "\n\n——来自周三涵")
    
    voices = templates.get("voices", templates)
    voice_templates = voices.get(voice, voices.get("professional", {}))

    intent_templates = voice_templates.get(intent, {})
    public_raw = intent_templates.get("public", "收到，感谢关注。")
    dm_raw = intent_templates.get("dm", "")

    # 添加前缀和后缀
    public = f"{prefix}{public_raw}{suffix}"
    dm = f"{prefix}{dm_raw}{suffix}" if dm_raw else ""

    return public, dm


def suggested_action(intent: str) -> str:
    """建议的操作"""
    if intent in {"buying_intent", "support"}:
        return "public_reply_plus_dm"
    if intent in {"price_objection", "skepticism"}:
        return "public_reply_review"
    if intent == "engagement":
        return "public_reply"
    if intent == "noise":
        return "skip_or_hide"
    return "public_reply"


def main():
    if len(sys.argv) < 2:
        print("用法: batch_comment_drafts.py <comments.csv> [output.json]")
        print("\nCSV 格式:")
        print("  comment,video_topic,intent_hint,priority_hint,notes")
        sys.exit(1)

    # 加载配置
    config = load_config()
    templates = load_templates()
    voice = config.get("defaultVoice", "professional")

    # 输入输出路径
    inp = Path(sys.argv[1])
    out_dir = SKILL_DIR / config.get("outputDir", "output")
    out_dir.mkdir(parents=True, exist_ok=True)

    if len(sys.argv) > 2:
        out = Path(sys.argv[2])
    else:
        out = out_dir / f"{inp.stem}.drafts.json"

    # 处理评论
    rows = []
    with inp.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            comment = (row.get('comment') or '').strip()
            topic = (row.get('video_topic') or '').strip()
            if not comment:
                continue

            # 检测或使用提供的意图
            intent = (row.get('intent_hint') or '').strip() or detect_intent(comment)
            priority = (row.get('priority_hint') or '').strip() or DEFAULT_PRIORITY.get(intent, 'medium')

            # 获取回复
            public, dm = get_reply(intent, templates, voice)

            rows.append({
                'comment': comment,
                'video_topic': topic,
                'intent': intent,
                'priority': priority,
                'suggested_action': suggested_action(intent),
                'public_reply': public,
                'dm_follow_up': dm,
                'notes': row.get('notes') or ''
            })

    # 输出
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"[OK] 生成 {len(rows)} 条回复草稿")
    print(f"[OK] 输出文件: {out}")

    # 统计
    intents = {}
    for r in rows:
        intents[r['intent']] = intents.get(r['intent'], 0) + 1

    print("\n意图分布:")
    for intent, count in sorted(intents.items(), key=lambda x: -x[1]):
        print(f"  {intent}: {count}")


if __name__ == '__main__':
    main()
