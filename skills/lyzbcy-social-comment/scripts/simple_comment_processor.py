#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版评论回复执行脚本
避免Unicode编码问题
"""
import json
import sys
from pathlib import Path

def main():
    try:
        # 读取草稿文件
        drafts_file = Path("C:/Users/24676/.openclaw/workspace/skills/lyzbcy-social-comment/runtime/output/comments.drafts.json")
        if not drafts_file.exists():
            print("没有找到评论草稿文件")
            return
        
        with open(drafts_file, 'r', encoding='utf-8') as f:
            drafts = json.load(f)
        
        print(f"找到 {len(drafts)} 条评论草稿")
        
        # 统计信息
        processed = 0
        high_priority = 0
        
        for item in drafts:
            comment = item.get('comment', '')
            intent = item.get('intent', '')
            priority = item.get('priority', 'low')
            reply = item.get('public_reply', '')
            
            if priority == 'high':
                high_priority += 1
            
            print(f"评论: {comment}")
            print(f"意图: {intent}")
            print(f"优先级: {priority}")
            print(f"回复: [回复内容]")
            print("-" * 50)
            
            processed += 1
        
        print(f"\n处理总结:")
        print(f"总评论数: {len(drafts)}")
        print(f"高优先级: {high_priority}")
        print(f"已处理: {processed}")
        
        # 保存处理日志
        log = {
            "timestamp": "2026-05-03T02:00:00Z",
            "total_comments": len(drafts),
            "high_priority": high_priority,
            "processed": processed,
            "platform": "douyin",
            "action": "heartbeat_check"
        }
        
        log_file = Path("C:/Users/24676/.openclaw/workspace/skills/lyzbcy-social-comment/runtime/output/heartbeat_check_log.json")
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
        
        print(f"检查日志已保存: {log_file}")
        
    except Exception as e:
        print(f"处理出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()