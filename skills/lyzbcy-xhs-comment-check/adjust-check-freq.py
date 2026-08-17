#!/usr/bin/env python3
"""频率节流:距上次完整运行 <12h 输出 SKIP:<详情>;否则输出 OK 并更新时间戳。
注:时间戳在检查通过时即写入,防止采集失败也反复触发;由 run-check.py 统一裁决。"""
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

STAMP = Path(__file__).resolve().parent / "comments-output" / ".last-run"
INTERVAL = timedelta(hours=12)
TZ = ZoneInfo("Asia/Shanghai")


def main():
    if STAMP.exists():
        try:
            last = datetime.fromisoformat(STAMP.read_text().strip())
            elapsed = datetime.now(TZ) - last
            if elapsed < INTERVAL:
                remain = (INTERVAL - elapsed).total_seconds() / 3600
                print(f"SKIP: 距上次检查仅 {elapsed.total_seconds() / 3600:.1f}h,需间隔 12h,剩余 {remain:.1f}h")
                return
        except ValueError:
            pass
    STAMP.parent.mkdir(parents=True, exist_ok=True)
    STAMP.write_text(datetime.now(TZ).isoformat())
    print("OK: 频率检查通过")


if __name__ == "__main__":
    main()
