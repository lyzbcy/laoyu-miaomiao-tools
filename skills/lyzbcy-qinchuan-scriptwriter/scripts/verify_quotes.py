# -*- coding: utf-8 -*-
"""
勤川 skill 例句验真 + 样张统计脚本
用法：
  1) 例句验真：python verify_quotes.py quote "文件名.md" "例句片段"   （在研究剧本原文中逐字检索）
  2) 样张统计：python verify_quotes.py stat "样张.md"                  （统计△行/台词行比例与净字数）
基准：SKILL.md 量化基准 —— 集均 934-1491 字，△:台词 ≈ 1.2-1.5:1
"""
import re
import sys
import os

LIB = r"E:\共享\工作\微盛\AI漫剧\AI漫剧学习\研究剧本"


def verify_quote(filename, needle):
    path = os.path.join(LIB, filename)
    if not os.path.exists(path):
        print("FILE_NOT_FOUND:", path)
        return False
    with open(path, encoding="utf-8") as f:
        content = f.read()
    ok = needle in content
    print(("PASS" if ok else "FAIL"), "|", filename, "|", needle[:40])
    return ok


def stat_episode(filename):
    started = False
    lines = []
    for line in open(filename, encoding="utf-8"):
        s = line.strip()
        if s == "第一集" or (re.match(r"^第[一二三四五六七八九十百\d]+集$", s) and not started):
            started = True
            continue
        if started and (s.startswith("（第") and s.endswith("完）")):
            break
        if started and s:
            lines.append(s)
    delta = [l for l in lines if l.startswith("△")]
    dialog = [l for l in lines if re.match(r"^[\u4e00-\u9fa5A-Za-z]+（?.*?[）)]?：", l) and not l.startswith(("场", "人物"))]
    body = [l for l in lines if not l.startswith(("场", "人物："))]
    n_d, n_t = len(delta), len(dialog)
    chars = sum(len(x) for x in body)
    ratio = n_d / n_t if n_t else 0
    print(f"△行:{n_d}  台词行:{n_t}  比例:{ratio:.2f}:1  净字数:{chars}")
    print(f"基准校验: 字数{'PASS' if 934 <= chars <= 1491 else 'FAIL'}(934-1491)  比例{'PASS' if 1.2 <= ratio <= 1.5 else 'WARN'}(1.2-1.5)")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "quote":
        sys.exit(0 if verify_quote(sys.argv[2], sys.argv[3]) else 1)
    elif mode == "stat":
        stat_episode(sys.argv[2])
    else:
        print(__doc__)
