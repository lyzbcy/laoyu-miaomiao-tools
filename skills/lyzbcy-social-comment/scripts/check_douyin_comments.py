#!/usr/bin/env python3
"""
抖音评论检查和回复生成脚本
用于定时检查新评论、私信、@消息并生成回复
"""
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 获取脚本所在目录
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent

# 模拟评论数据（实际使用时应该从抖音API获取）
MOCK_COMMENTS = [
    {
        "id": "comment_001",
        "content": "这个工具真的有用吗？",
        "type": "comment",
        "author": "用户A",
        "video_id": "video_001",
        "timestamp": datetime.now() - timedelta(minutes=15),
        "replied": False
    },
    {
        "id": "comment_002", 
        "content": "多少钱？想了解一下",
        "type": "comment",
        "author": "用户B",
        "video_id": "video_002",
        "timestamp": datetime.now() - timedelta(minutes=30),
        "replied": False
    },
    {
        "id": "dm_001",
        "content": "你好，请问这个怎么购买？",
        "type": "private_message",
        "author": "用户C",
        "video_id": None,
        "timestamp": datetime.now() - timedelta(hours=1),
        "replied": False
    },
    {
        "id": "mention_001",
        "content": "@周三涵 这个教程在哪里可以看到完整版？",
        "type": "mention",
        "author": "用户D",
        "video_id": "video_003",
        "timestamp": datetime.now() - timedelta(hours=2),
        "replied": False
    }
]

# 意图检测规则
INTENT_RULES = [
    ("buying_intent", [r"多少钱", r"怎么卖", r"怎么买", r"私信", r"能做吗", r"报名", r"下单", r"联系方式", r"购买"]),
    ("price_objection", [r"太贵", r"贵", r"便宜点", r"最低", r"不值", r"割韭菜", r"不值这个价"]),
    ("skepticism", [r"真的假的", r"真吗", r"骗人", r"智商税", r"吹牛", r"有用吗", r"靠谱吗"]),
    ("support", [r"收不到", r"打不开", r"不能用", r"没反应", r"怎么进去", r"售后", r"退款"]),
    ("engagement", [r"求更", r"第二集", r"继续更", r"想学", r"教程", r"蹲", r"收藏了", r"催更"]),
    ("inquiry", [r"怎么", r"可以吗", r"适合", r"啥", r"是什么", r"如何", r"能不能"]),
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

def generate_reply(comment: dict) -> dict:
    """生成回复内容"""
    intent = detect_intent(comment["content"])
    template = REPLY_TEMPLATES.get(intent, REPLY_TEMPLATES["inquiry"])
    
    # 生成回复内容
    if comment["type"] == "private_message" or comment["type"] == "mention":
        # 私信和@消息使用DM回复
        reply_content = template["dm"] if template["dm"] else template["public"]
    else:
        # 普通评论使用公开回复
        reply_content = template["public"]
    
    # 格式化回复
    formatted_reply = f"回复: {reply_content}\n\n——来自周三涵"
    
    return {
        "original_comment": comment["content"],
        "intent": intent,
        "priority": PRIORITY.get(intent, "medium"),
        "reply_content": formatted_reply,
        "reply_type": "dm" if comment["type"] in ["private_message", "mention"] else "public",
        "author": comment["author"],
        "comment_id": comment["id"]
    }

def check_new_comments() -> list:
    """检查新评论（模拟）"""
    # 在实际使用中，这里应该调用抖音API检查新评论
    # 现在使用模拟数据
    new_comments = [c for c in MOCK_COMMENTS if not c.get("replied", False)]
    
    # 标记为已处理（模拟）
    for comment in new_comments:
        comment["replied"] = True
    
    return new_comments

def generate_notification(replies: list) -> str:
    """生成通知内容"""
    if not replies:
        return "[抖音] 检查完成：暂无新评论需要回复"
    
    notification_lines = ["[抖音] 评论检查完成，发现需要回复的内容："]
    
    for reply in replies:
        type_label = {
            "comment": "评论",
            "private_message": "私信", 
            "mention": "@"
        }.get(reply["reply_type"], "消息")
        
        notification_lines.append(f"\n[{type_label}] {reply['author']}: {reply['original_comment']}")
        notification_lines.append(f"   意图: {reply['intent']}")
        notification_lines.append(f"   回复: {reply['reply_content']}")
    
    notification_lines.append(f"\n共处理 {len(replies)} 条消息")
    
    return "\n".join(notification_lines)

def save_replies(replies: list):
    """保存回复记录"""
    output_dir = SKILL_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"douyin_replies_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(replies, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"[OK] 回复记录已保存: {output_file}")

def main():
    """主函数"""
    print(f"[时间] 开始检查抖音新评论... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查新评论
    new_comments = check_new_comments()
    
    if not new_comments:
        print("[完成] 没有发现新评论")
        return
    
    print(f"[发现] 发现 {len(new_comments)} 条新消息")
    
    # 生成回复
    replies = []
    for comment in new_comments:
        reply = generate_reply(comment)
        replies.append(reply)
        print(f"[回复] 生成回复给 {comment['author']}: {reply['intent']}")
    
    # 保存回复记录
    save_replies(replies)
    
    # 生成通知
    notification = generate_notification(replies)
    print("\n" + "="*50)
    print(notification)
    print("="*50)
    
    # 在实际使用中，这里应该发送通知给用户
    # 现在只是打印到控制台
    print(f"\n[通知] 请查看上述回复内容，确认后可手动发送")

if __name__ == '__main__':
    main()