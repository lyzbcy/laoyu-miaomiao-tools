#!/usr/bin/env python3
"""
处理实际抖音评论数据并生成回复
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# 设置UTF-8编码
sys.stdout.reconfigure(encoding='utf-8')

# 获取脚本所在目录
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent

# 意图检测规则
INTENT_RULES = [
    ("buying_intent", [r"多少钱", r"怎么卖", r"怎么买", r"私信", r"能做吗", r"报名", r"下单", r"联系方式", r"购买", r"处吗"]),
    ("price_objection", [r"太贵", r"贵", r"便宜点", r"最低", r"不值", r"割韭菜", r"不值这个价"]),
    ("skepticism", [r"真的假的", r"真吗", r"骗人", r"智商税", r"吹牛", r"有用吗", r"靠谱吗", r"还以为"]),
    ("support", [r"收不到", r"打不开", r"不能用", r"没反应", r"怎么进去", r"售后", r"退款"]),
    ("engagement", [r"求更", r"第二集", r"继续更", r"想学", r"教程", r"蹲", r"收藏了", r"催更", r"等我一会"]),
    ("inquiry", [r"怎么", r"可以吗", r"适合", r"啥", r"是什么", r"如何", r"能不能", r"在哪里"]),
]

# 优先级映射
PRIORITY = {
    "buying_intent": "high",
    "support": "high",
    "price_objection": "medium",
    "skepticism": "medium",
    "inquiry": "high",
    "engagement": "medium",
    "noise": "low",
}

# 回复模板
REPLY_TEMPLATES = {
    "buying_intent": {
        "public": "可以的，这类我这边有现成思路，想看适合你的版本可以私信我。",
        "dm": "您好！关于购买详情，我可以为您提供更具体的方案，请告诉我您的具体需求。"
    },
    "support": {
        "public": "收到，感谢您的反馈。请私信我具体情况，我会尽快帮您解决。",
        "dm": "您好！请详细描述您遇到的问题，我会全力帮您解决。"
    },
    "price_objection": {
        "public": "理解您的考虑，这个价格是基于服务质量和效果来制定的，性价比很高。",
        "dm": "您好！我可以为您详细介绍价值所在，或者根据您的需求定制更合适的方案。"
    },
    "skepticism": {
        "public": "理解您的疑虑，很多用户一开始也有类似想法，实际使用后效果都很不错。",
        "dm": "您好！我可以为您提供更多成功案例和详细说明，消除您的顾虑。"
    },
    "inquiry": {
        "public": "感谢您的咨询！这个工具确实很适合您的情况，我可以详细介绍。",
        "dm": "您好！关于您的问题，我可以为您提供详细的解答和个性化建议。"
    },
    "engagement": {
        "public": "感谢关注！我会持续更新更多实用内容，敬请期待！",
        "dm": "您好！感谢您的支持，我会根据大家的需求安排后续内容。"
    },
    "noise": {
        "public": "感谢您的关注！",
        "dm": ""
    }
}

def detect_intent(text: str) -> str:
    """检测评论意图"""
    t = text.strip().lower()
    for intent, pats in INTENT_RULES:
        for p in pats:
            if re.search(p, t, flags=re.I):
                return intent
    if len(t) <= 2:
        return "noise"
    return "inquiry"

def generate_reply(comment_text: str, username: str, intent: str = None) -> dict:
    """生成回复内容"""
    # 如果没有提供意图，则自动检测
    if not intent:
        intent = detect_intent(comment_text)
    
    template = REPLY_TEMPLATES.get(intent, REPLY_TEMPLATES["inquiry"])
    
    # 判断是否需要私信回复
    needs_dm = any(keyword in comment_text.lower() for keyword in ["私信", "处", "联系方式", "购买", "怎么买"])
    
    # 生成回复内容
    if needs_dm:
        # 使用DM回复
        reply_content = template["dm"] if template["dm"] else template["public"]
        reply_type = "dm"
    else:
        # 使用公开回复
        reply_content = template["public"]
        reply_type = "public"
    
    # 格式化回复 - 使用要求的格式
    formatted_reply = f"🦞 {reply_content}\n\n——来自周三涵"
    
    return {
        "original_comment": comment_text,
        "username": username,
        "intent": intent,
        "priority": PRIORITY.get(intent, "medium"),
        "reply_content": formatted_reply,
        "reply_type": reply_type,
        "timestamp": datetime.now().isoformat()
    }

def process_actual_comments():
    """处理实际的评论数据"""
    # 读取评论数据
    input_file = SKILL_DIR / "runtime" / "input" / "comments_for_reply.json"
    
    if not input_file.exists():
        print(f"[错误] 找不到评论数据文件: {input_file}")
        return []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    comments = data.get("comments", [])
    print(f"[发现] 找到 {len(comments)} 条评论需要处理")
    
    # 处理每条评论
    replies = []
    for i, comment in enumerate(comments):
        username = comment.get("username", f"用户{i+1}")
        comment_text = comment.get("commentText", "")
        intent = comment.get("intent")  # 使用已有的意图或自动检测
        
        if not comment_text:
            print(f"[跳过] 用户 {username} 的评论为空")
            continue
        
        print(f"[处理] 处理评论: {username} - {comment_text[:30]}...")
        
        reply = generate_reply(comment_text, username, intent)
        replies.append(reply)
        
        print(f"[生成] 回复类型: {reply['reply_type']}, 意图: {reply['intent']}")
    
    # 保存回复记录
    output_dir = SKILL_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"actual_comments_replies_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "source_file": str(input_file),
            "processed_at": datetime.now().isoformat(),
            "total_comments": len(comments),
            "replies_generated": len(replies),
            "replies": replies
        }, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"[OK] 回复记录已保存: {output_file}")
    
    return replies

def generate_notification(replies: list) -> str:
    """生成通知内容"""
    if not replies:
        return "[抖音] 检查完成：暂无新评论需要回复"
    
    notification_lines = ["[抖音] 评论检查完成，生成回复内容："]
    
    for i, reply in enumerate(replies, 1):
        type_label = "私信" if reply["reply_type"] == "dm" else "公开回复"
        
        notification_lines.append(f"\n{i}. [{type_label}] {reply['username']}: {reply['original_comment']}")
        notification_lines.append(f"   意图: {reply['intent']}")
        notification_lines.append(f"   回复: {reply['reply_content']}")
    
    notification_lines.append(f"\n共处理 {len(replies)} 条评论")
    
    return "\n".join(notification_lines)

def main():
    """主函数"""
    print(f"[时间] 开始处理实际抖音评论... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 处理实际评论
    replies = process_actual_comments()
    
    # 生成通知
    notification = generate_notification(replies)
    print("\n" + "="*60)
    print(notification)
    print("="*60)
    
    # 保存通知到文件
    output_dir = SKILL_DIR / "output"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    notification_file = output_dir / f"notification_{timestamp}.txt"
    
    with open(notification_file, 'w', encoding='utf-8') as f:
        f.write(notification)
    
    print(f"[通知] 内容已保存到: {notification_file}")

if __name__ == '__main__':
    main()