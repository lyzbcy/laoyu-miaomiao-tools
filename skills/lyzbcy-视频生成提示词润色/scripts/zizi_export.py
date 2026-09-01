#!/usr/bin/env python3
"""字字动画分镜导出工具：把字字动画里生成的分镜，按润色 skill 的标准格式导出到集文件夹。

数据源：字字动画（Electron 应用）的本机任务库 task_records.db，
        「推理」任务的 output_text 里就是完整分镜（_::~OUTPUT_START::~_ ... _::~OUTPUT_END::~_）。

用法：
  python zizi_export.py --list                     # 只列出可导出的分镜
  python zizi_export.py                            # 交互：列表 → 选编号 → 选目标文件夹 → 导出
  python zizi_export.py --sel 1,3-5 --out "...\契约一条龙\39" --start 1

导出格式（与 契约一条龙/38/1.md 同构）：
  【分镜总时长：Xs】 首行（按各镜头时长自动求和）
  场景/角色/物品/风格 头部 + ::~FIELD::- 分隔 + 逐镜头排版（镜头N 与 情绪： 各自独立成行）

说明：只读数据库，不动字字动画本身；同名文件存在时跳过不覆盖（--force 可覆盖）。
"""
import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

MARK_START = "_::~OUTPUT_START::~_"
MARK_END = "_::~OUTPUT_END::~_"
MARK_FIELD = "_::~FIELD::~_"
FIELD_LINE = "::~FIELD::~"


def default_db() -> str:
    appdata = os.environ.get("APPDATA", "")
    return os.path.join(appdata, "zizidonghua", "task_records.db")


def open_db(path: str) -> sqlite3.Connection:
    """优先只读打开（应用在运行也安全）；失败则把 db+wal 复制到临时目录再开。"""
    try:
        return sqlite3.connect("file:" + path.replace("\\", "/") + "?mode=ro", uri=True)
    except sqlite3.Error:
        tmp_dir = Path(tempfile.mkdtemp(prefix="zizi_db_"))
        for suffix in ("", "-wal", "-shm"):
            src = path + suffix
            if os.path.exists(src):
                shutil.copy2(src, tmp_dir / (Path(path).name + suffix))
        return sqlite3.connect(str(tmp_dir / Path(path).name))


def parse_output(raw: str):
    """从推理任务 output_text 提取分镜；不是分镜输出则返回 None。"""
    if MARK_START not in raw or MARK_END not in raw:
        return None
    core = raw.split(MARK_START, 1)[1].split(MARK_END, 1)[0].strip()
    m = re.search(r"场景：([^@（(，,\n]+)", core)
    scene = m.group(1).strip() if m else "（未命名场景）"
    body = core.split(MARK_FIELD, 1)[1] if MARK_FIELD in core else core
    shot_nums = re.findall(r"镜头(\d+)：", body)
    durs = re.findall(r"镜头\d+：(?:【[^】]*】)?\s*(\d+(?:\.\d+)?)s", body)
    total = sum(float(d) for d in durs)
    first_shot = re.search(r"(镜头1：[^\n]{0,40})", core)
    preview = first_shot.group(1) if first_shot else ""
    return {"scene": scene, "n_shots": len(shot_nums), "total": total, "core": core,
            "preview": preview, "duration_fmt": fmt_seconds(total)}


def fmt_seconds(total: float) -> str:
    return f"{int(total)}s" if float(total).is_integer() else f"{total}s"


def to_markdown(rec: dict) -> str:
    """raw 分镜 → 标准 md：总时长首行 + 头部/字段独立成行 + 镜头块之间空行。"""
    text = rec["core"].replace(MARK_FIELD, "\n\x00FIELD\x00\n")
    text = re.sub(r"(?=(?:场景|角色|物品|风格|站位锚点)：)", "\n", text)
    text = re.sub(r"(?=镜头\d+：)", "\n", text)
    text = re.sub(r"(?=情绪：[^；】\n]*?\d{1,3}%)", "\n", text)  # 跳过配音指令内层的“；情绪：”
    text = re.sub(r"(?=片段蒙太奇说明：)", "\n", text)
    text = text.replace("（no srt", "\n（no srt")

    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]

    out: list[str] = [f"【分镜总时长：{rec['duration_fmt']}】"]
    for ln in lines:
        if ln == "\x00FIELD\x00":
            out.append(FIELD_LINE)
            continue
        if re.match(r"镜头\d+：", ln) or ln.startswith(("片段蒙太奇说明", "（no srt")):
            if out and out[-1] != FIELD_LINE:
                out.append("")  # 镜头块之间空一行
        out.append(ln)
    return "\n".join(out) + "\n"


def collect(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute(
        "SELECT task_id, start_time, payload FROM task_records "
        "WHERE kind='llm' AND status='success' ORDER BY start_time"
    ).fetchall()
    seen, records = set(), []
    for task_id, start_time, payload in rows:
        try:
            out_text = json.loads(payload).get("output_text", "")
        except Exception:
            continue
        rec = parse_output(out_text)
        if not rec or rec["n_shots"] == 0:  # 0 镜头的是剧本转换等中间产物，不是分镜
            continue
        key = rec["core"]
        if key in seen:  # 同一内容多次生成/重试，只留最新
            continue
        seen.add(key)
        rec.update(task_id=task_id, start_time=start_time)
        records.append(rec)
    records.sort(key=lambda r: r["start_time"], reverse=True)  # 新的排前面
    return records


def parse_selection(text: str, n: int) -> list[int]:
    text = text.strip().lower()
    if not text or text in ("all", "a", "全部"):
        return list(range(1, n + 1))
    picks = set()
    for part in text.replace("，", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            picks.update(range(int(a), int(b) + 1))
        else:
            picks.add(int(part))
    bad = [p for p in picks if not 1 <= p <= n]
    if bad:
        sys.exit(f"编号超出范围：{bad}（可选 1~{n}）")
    return sorted(picks)


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="字字动画分镜导出（润色 skill 标准格式）")
    ap.add_argument("--db", default=default_db(), help="task_records.db 路径（默认 %%APPDATA%%\\zizidonghua）")
    ap.add_argument("--list", action="store_true", help="只列出可导出的分镜，不导出")
    ap.add_argument("--sel", default=None, help="要导出的编号，如 1,3-5（不填=交互选择/全部）")
    ap.add_argument("--out", default=None, help="目标文件夹（默认 ./zizi_export）")
    ap.add_argument("--start", type=int, default=1, help="起始文件序号（默认 1 → 01.md）")
    ap.add_argument("--force", action="store_true", help="同名文件已存在时覆盖")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        sys.exit(f"找不到字字动画任务库：{args.db}\n（可用 --db 手动指定 task_records.db 路径）")

    records = collect(open_db(args.db))
    if not records:
        sys.exit("任务库里没有可导出的分镜（需要字字动画里生成过分镜）")

    print(f"共 {len(records)} 条可导出的分镜（新的在前）：\n")
    print(f"{'#':>3}  {'生成时间':<16}  {'场景':<12} {'镜头':>3} {'时长':>5}  预览")
    for i, r in enumerate(records, 1):
        print(f"{i:>3}  {r['start_time']:<16}  {r['scene']:<12} {r['n_shots']:>3} {r['duration_fmt']:>5}  {r['preview'][:38]}")

    if args.list:
        return

    if args.sel is not None:
        picks = parse_selection(args.sel, len(records))
    else:
        picks = parse_selection(input("\n选择要导出的分镜（如 1,3-5；回车=全部）："), len(records))
    chosen = [records[p - 1] for p in picks]

    out_dir = Path(args.out or input("导出到哪个文件夹？（回车=当前目录下 zizi_export）：").strip() or "zizi_export")
    out_dir.mkdir(parents=True, exist_ok=True)

    written, skipped = [], []
    for offset, rec in enumerate(chosen):
        idx = args.start + offset
        name = f"{idx:02d}.md" if idx < 100 else f"{idx:03d}.md"
        target = out_dir / name
        if target.exists() and not args.force:
            skipped.append(name)
            continue
        target.write_text(to_markdown(rec), encoding="utf-8")
        written.append(f"{name} ← {rec['scene']}（{rec['n_shots']}镜/{rec['duration_fmt']}）")

    print(f"\n导出完成 → {out_dir.resolve()}")
    for w in written:
        print(f"  ✔ {w}")
    for s in skipped:
        print(f"  ↷ 已跳过（已存在，--force 可覆盖）：{s}")


if __name__ == "__main__":
    main()
