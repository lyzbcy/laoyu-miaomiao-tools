#!/usr/bin/env python3
"""主控唯一入口:节流→内存→执行(xhs_reply.py 内含登录检测)→报告→审计。
对齐 lyzbcy-douyin-comment-check 的 run-check.py 骨架。"""
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent
REPORT = BASE_DIR / "comment-check-report.md"
LOG_DIR = BASE_DIR / "logs"
TZ = ZoneInfo("Asia/Shanghai")


def now():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")


def day():
    return datetime.now(TZ).strftime("%Y-%m-%d")


def log(msg):
    try:
        LOG_DIR.mkdir(exist_ok=True)
        with (LOG_DIR / f"run-{day()}.log").open("a", encoding="utf-8") as f:
            f.write(f"[{now()}] {msg}\n")
        cutoff = datetime.now(TZ) - timedelta(days=7)
        for f in LOG_DIR.glob("run-*.log"):
            try:
                if datetime.strptime(f.stem[4:], "%Y-%m-%d") < cutoff:
                    f.unlink()
            except ValueError:
                continue
    except Exception:
        pass


def write_report(text):
    REPORT.write_text(text, encoding="utf-8")
    print(text)


def mem_available_mb():
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) // 1024
    return 99999


def xvfb(cmd):
    if os.environ.get("DISPLAY") or not shutil.which("xvfb-run"):
        return cmd
    return ["xvfb-run", "-a"] + cmd


def main():
    freq = subprocess.run([sys.executable, str(BASE_DIR / "adjust-check-freq.py")],
                          capture_output=True, text=True)
    freq_out = (freq.stdout or freq.stderr).strip()
    if freq_out.startswith("SKIP"):
        log(f"SKIP | {freq_out}")
        write_report(f"# 小红书评论检查报告\n\n## 执行时间\n{now()}\n\n## 状态\nNO_REPLY\n\n## 原因\n{freq_out}\n\n## 说明\n本次因频率限制跳过,没有执行评论采集,也没有生成任何回复。")
        return

    m = mem_available_mb()
    if m < 200:
        log(f"STOP_MEMORY | {m}MB")
        write_report(f"# 小红书评论检查报告\n\n## 执行时间\n{now()}\n\n## 状态\n已停止\n\n## 停止原因\n内存不足:可用内存 {m}MB < 200MB")
        return

    proc = subprocess.run(xvfb([sys.executable, str(BASE_DIR / "xhs_reply.py")]),
                          capture_output=True, text=True, timeout=1800, cwd=str(BASE_DIR))
    out = (proc.stdout or "").strip()
    log(f"RUN | exit={proc.returncode} | {out[:300]}")

    if "LOGIN_EXPIRED" in out:
        write_report(f"# 小红书评论检查报告\n\n## 执行时间\n{now()}\n\n## 状态\n需要人工处理\n\n## 原因\n登录态失效,小红书需要重新扫码登录。\n\n## 处理方式\n在服务器运行: cd {BASE_DIR} && xvfb-run -a python3 login_once.py\n然后把生成的 login-qr.png 发给主人扫码。\n\n## 原始输出\n{out}")
        return

    try:
        result = json.loads(out.splitlines()[-1])
    except Exception:
        result = {"status": "ERROR", "stderr": (proc.stderr or "")[:500]}
    if result.get("status") == "ERROR":
        write_report(f"# 小红书评论检查报告\n\n## 执行时间\n{now()}\n\n## 状态\n执行失败\n\n## 原因\nxhs_reply.py 输出无法解析\n\n## stderr\n{result.get('stderr', '')}")
        return

    s = result.get("stats", result)
    lines = ["# 小红书评论检查报告", "", "## 执行时间", now(), "", "## 执行结果",
             f"- 频率检查:{freq_out}",
             f"- 内存检查:通过({m}MB)",
             f"- 抓取通知:{s.get('collected', 0)} 条",
             f"- 已回过跳过:{s.get('skipped_replied', 0)} | 垃圾过滤:{s.get('skipped_spam', 0)}",
             f"- 回复成功(已核验):{s.get('replied', 0)} 条",
             f"- 已发送未核验:{s.get('unverified', 0)} 条",
             f"- 错误:{s.get('errors', 0)} 条", "", "## 回复明细"]
    plan = BASE_DIR / "comments-output" / "reply-plan.json"
    if plan.exists():
        try:
            for it in json.loads(plan.read_text(encoding="utf-8")).get("items", []):
                lines.append(f"- @{it['username']}|{it['comment'][:40]}|回复:{it['reply'][:50]}")
        except Exception:
            pass
    if not any(l.startswith("- @") for l in lines):
        lines.append("(本次无待回复评论)")
    lines += ["", "## 结论"]
    if s.get("errors", 0) == 0 and s.get("unverified", 0) == 0 and s.get("replied", 0) > 0:
        lines.append("本次评论已全部按真实结果完成回复。")
    elif s.get("replied", 0) == 0 and s.get("unverified", 0) == 0:
        lines.append("本次没有成功回复任何评论(或本来就没有新评论)。")
    else:
        lines.append("本次只完成部分回复,存在未核验/错误条目,未全部完成。")
    write_report("\n".join(lines))


if __name__ == "__main__":
    main()
