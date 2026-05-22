#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
贴吧浏览主脚本

每天下午1点到2点浏览贴吧机器人相关版块，学习有趣的AI讨论。
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

# 确保 Windows 控制台 UTF-8 输出
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 添加当前目录到 path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from security_check import is_safe_post, sanitize_content

# 配置
RUNTIME_DIR = Path(__file__).parent.parent / "runtime"
LEARNING_LOG_PATH = RUNTIME_DIR / "learning_log.json"
MAX_DURATION_MINUTES = 60
MAX_POSTS_PER_RUN = 20
MAX_FINDINGS_PER_RUN = 10

# 目标贴吧版块
TARGET_FORUMS = [
    "https://tieba.baidu.com/f?kw=原神",
    "https://tieba.baidu.com/f?kw=米哈游",
    "https://tieba.baidu.com/f?kw=崩坏星穹铁道",
    "https://tieba.baidu.com/f?kw=人工智能",
    "https://tieba.baidu.com/f?kw=chatgpt",
]

def load_learning_log() -> dict:
    """加载学习记录"""
    if LEARNING_LOG_PATH.exists():
        with open(LEARNING_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"records": []}

def save_learning_log(log: dict):
    """保存学习记录"""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with open(LEARNING_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def browse_with_agent_browser(url: str) -> str:
    """使用 agent-browser 浏览页面"""
    try:
        result = subprocess.run(
            ["npx", "-y", "agent-browser", "open", url],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout
    except Exception as e:
        print(f"[error] 浏览失败: {e}")
        return ""

def extract_posts_from_page(page_content: str) -> list:
    """从页面内容提取帖子列表（简化版）"""
    # 这里只是示例，实际需要解析HTML
    posts = []
    # TODO: 实现实际的帖子提取逻辑
    return posts

def run_learning_session():
    """执行学习会话"""
    start_time = time.time()
    
    print(f"[social-learning] 开始学习会话 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"[social-learning] 目标版块: {len(TARGET_FORUMS)} 个")
    
    findings = []
    posts_viewed = 0
    security_events = 0
    
    for forum_url in TARGET_FORUMS:
        # 检查时间限制
        elapsed_minutes = (time.time() - start_time) / 60
        if elapsed_minutes >= MAX_DURATION_MINUTES:
            print(f"[social-learning] 达到时间限制 ({MAX_DURATION_MINUTES}分钟)，结束会话")
            break
        
        # 检查帖子数量限制
        if posts_viewed >= MAX_POSTS_PER_RUN:
            print(f"[social-learning] 达到帖子数量限制 ({MAX_POSTS_PER_RUN})，结束会话")
            break
        
        print(f"[social-learning] 浏览: {forum_url}")
        
        # 使用 agent-browser 浏览
        # 实际实现中需要解析页面内容
        # page_content = browse_with_agent_browser(forum_url)
        # posts = extract_posts_from_page(page_content)
        
        # 模拟浏览（实际实现时替换）
        print(f"[social-learning] 浏览完成")
    
    # 记录结果
    log = load_learning_log()
    record = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "duration_minutes": round((time.time() - start_time) / 60, 1),
        "posts_viewed": posts_viewed,
        "interesting_findings": findings[:MAX_FINDINGS_PER_RUN],
        "security_events": security_events
    }
    log["records"].append(record)
    
    # 只保留最近30天的记录
    log["records"] = log["records"][-30:]
    
    save_learning_log(log)
    
    print(f"[social-learning] 会话结束 - 浏览 {posts_viewed} 帖子，发现 {len(findings)} 条有趣内容")
    
    return record

def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI社交学习")
    parser.add_argument("--dry-run", action="store_true", help="测试模式，不实际浏览")
    args = parser.parse_args()
    
    if args.dry_run:
        print("[social-learning] 测试模式")
        print(f"[social-learning] 目标版块: {TARGET_FORUMS}")
        print(f"[social-learning] 时间限制: {MAX_DURATION_MINUTES}分钟")
        print(f"[social-learning] 帖子限制: {MAX_POSTS_PER_RUN}")
        return
    
    record = run_learning_session()
    print(json.dumps(record, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
