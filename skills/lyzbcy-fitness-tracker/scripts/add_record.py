#!/usr/bin/env python3
"""
lyzbcy-fitness-tracker / 训练记录脚本

用法:
  python add_record.py set --exercise "卧推" --weight 60 --reps 10
  python add_record.py set --exercise "卧推" --weight 60 --reps 10 --rpe 8 --note "轻松"
  python add_record.py session_start --session push --note "今天练胸"
  python add_record.py session_end --note "练完了"
  python add_record.py bodyweight --value 72.5
  python add_record.py note --note "状态不好"

自动功能:
  - 时间戳自动生成
  - setNum 自动计算（当天同动作已有几条 +1）
  - session 自动从当天记录推断
  - muscleGroup 自动从 exercises.json 匹配
  - 字段校验：必填字段缺失会报错
"""

import argparse
import json
import os
from pathlib import Path
import math
import re
from decimal import Decimal
import runtime
import sys
from datetime import datetime, timezone, timedelta

# ── 路径配置 ──────────────────────────────────────────
# fitness 数据在此共享目录，不是 workspace 下的相对路径
FITNESS_DIR = str(runtime.workspace())
RECORDS_FILE = os.path.join(FITNESS_DIR, "records.jsonl")
CONFIG_FILE = os.path.join(FITNESS_DIR, "config.json")
EXERCISES_FILE = os.path.join(FITNESS_DIR, "exercises.json")

CST = timezone(timedelta(hours=8))


# ── 工具函数 ──────────────────────────────────────────

def now_ts():
    """返回当前时间的 ISO8601 格式"""
    return datetime.now(CST).strftime('%Y-%m-%dT%H:%M:%S+08:00')


def today_date():
    return datetime.now(CST).strftime('%Y-%m-%d')


def load_jsonl(path):
    """读取 JSONL 文件，返回列表"""
    if not os.path.exists(path):
        return []
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"⚠️ 跳过无效行: {line[:80]}...", file=sys.stderr)
    return records


def append_record(record):
    """追加一条记录到 JSONL 文件"""
    os.makedirs(os.path.dirname(RECORDS_FILE), exist_ok=True)
    with open(RECORDS_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    return record


def get_today_records(date=None):
    """获取指定日期的所有记录"""
    target = date or today_date()
    all_records = load_jsonl(RECORDS_FILE)
    return [r for r in all_records if r.get('date') == target]


def infer_session(date=None):
    """从当天记录推断 session 类型"""
    today = get_today_records(date)
    for r in reversed(today):
        if r.get('session'):
            return r['session']
    return None


def infer_setnum(exercise, date=None):
    """计算当天某动作的下一个 setNum"""
    today = get_today_records(date)
    count = 0
    for r in today:
        if r.get('action') == 'set' and r.get('exercise') == exercise:
            count += 1
    return count + 1


def load_exercises():
    """加载动作库"""
    if not os.path.exists(EXERCISES_FILE):
        return {}
    with open(EXERCISES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_muscle_group(exercise_name):
    """从动作库匹配 muscleGroup"""
    data = load_exercises()
    if 'exercises' not in data:
        return None
    for category, exercises in data['exercises'].items():
        for ex in exercises:
            if ex['name'] == exercise_name:
                return ex.get('primary')
            if exercise_name in ex.get('alias', []):
                return ex.get('primary')
    return None


# ── 记录函数 ──────────────────────────────────────────

def activity_time(date, clock):
    if not clock:
        return now_ts()
    if not re.fullmatch(r"[0-9]{2}:[0-9]{2}(?::[0-9]{2})?", clock):
        raise ValueError("--time 请用北京时间 HH:MM 或 HH:MM:SS")
    return datetime.fromisoformat(f"{date}T{clock}").replace(tzinfo=CST).isoformat(timespec="seconds")


def load_fields(value, unit, equipment=None, plate_estimates=None):
    # weight remains the normalized kg field used by existing consumers.
    if unit == "kg":
        return {"weight": value}
    weight = float(Decimal(str(value)) * Decimal("0.45359237")) if unit == "lb" else None
    fields = {"weight": weight, "reportedWeight": value, "reportedUnit": unit}
    if equipment:
        fields["equipment"] = equipment
    if unit == "plate" and equipment:
        estimate = (plate_estimates or {}).get(equipment)
        if estimate is not None:
            rate = estimate["kg_per_plate"]
            if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(rate) or rate <= 0:
                raise ValueError(f"{equipment} 的片重估算必须为有限正数")
            fields.update(
                weight=float(Decimal(str(value)) * Decimal(str(rate))),
                weightEstimated=True,
                estimateKgPerPlate=rate,
                estimateSource=estimate["source"],
            )
    return fields


def add_set(args):
    """添加一组训练记录"""
    exercise = args.exercise
    if not exercise:
        print("❌ 缺少必填参数: --exercise", file=sys.stderr)
        sys.exit(1)
    if args.weight is None:
        print("❌ 缺少必填参数: --weight", file=sys.stderr)
        sys.exit(1)
    if args.reps is None:
        print("❌ 缺少必填参数: --reps", file=sys.stderr)
        sys.exit(1)

    date = args.date or today_date()
    session = args.session or infer_session(date)
    if not session:
        print("❌ 无法推断 session，请用 --session 指定 (push/pull/legs/...)", file=sys.stderr)
        sys.exit(1)

    set_num = args.set_num or infer_setnum(exercise, date)
    muscle_group = args.muscle_group or find_muscle_group(exercise)

    plate_estimates = None
    if args.weight_unit == 'plate' and args.equipment:
        plate_estimates = runtime.config(Path(RECORDS_FILE).parent).get('plate_estimates')

    record = {
        'ts': now_ts(),
        'date': date,
        'action': 'set',
        'exercise': exercise,
        'muscleGroup': muscle_group or 'unknown',
        'session': session,
        'setNum': set_num,
        **load_fields(args.weight, args.weight_unit, args.equipment, plate_estimates),
        'reps': args.reps,
    }
    record['endTime'] = activity_time(date, args.time)
    if args.rpe is not None:
        record['rpe'] = args.rpe
    if args.note:
        record['note'] = args.note

    append_record(record)
    unit_label = "片" if args.weight_unit == "plate" else args.weight_unit
    print(f"✅ {exercise} 第{set_num}组: {args.weight:g}{unit_label}×{args.reps:g}" +
          (f" (RPE {args.rpe})" if args.rpe is not None else ""))
    return record


def add_session_start(args):
    """添加 session_start 记录"""
    date = args.date or today_date()
    session = args.session
    if not session:
        print("❌ 缺少必填参数: --session (push/pull/legs/...)", file=sys.stderr)
        sys.exit(1)

    record = {
        'ts': now_ts(),
        'date': date,
        'action': 'session_start',
        'session': session,
    }
    if args.time:
        record['endTime'] = activity_time(date, args.time)
    if args.note:
        record['note'] = args.note

    append_record(record)
    print(f"🏋️ 训练开始: {session} ({date})" +
          (f" — {args.note}" if args.note else ""))
    return record


def add_session_end(args):
    """添加 session_end 记录"""
    date = args.date or today_date()
    session = args.session or infer_session(date)
    if not session:
        print("❌ 无法推断 session，请用 --session 指定", file=sys.stderr)
        sys.exit(1)

    record = {
        'ts': now_ts(),
        'date': date,
        'action': 'session_end',
        'session': session,
    }
    if args.time:
        record['endTime'] = activity_time(date, args.time)
    if args.note:
        record['note'] = args.note

    append_record(record)
    print(f"🏁 训练结束: {session} ({date})")
    return record


def add_bodyweight(args):
    """添加体重记录"""
    if args.value is None:
        print("❌ 缺少必填参数: --value", file=sys.stderr)
        sys.exit(1)

    date = args.date or today_date()
    record = {
        'ts': now_ts(),
        'date': date,
        'action': 'bodyweight',
        'value': args.value,
        'unit': 'kg',
    }

    append_record(record)
    print(f"⚖️ 体重记录: {args.value}kg ({date})")
    return record


def add_note(args):
    """添加自由备注"""
    if not args.note:
        print("❌ 缺少必填参数: --note", file=sys.stderr)
        sys.exit(1)

    date = args.date or today_date()
    session = args.session or infer_session(date)

    record = {
        'ts': now_ts(),
        'date': date,
        'action': 'note',
    }
    if session:
        record['session'] = session
    record['note'] = args.note

    append_record(record)
    print(f"📝 备注: {args.note[:50]}")
    return record


# ── CLI ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='lyzbcy-fitness-tracker 训练记录工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--data-dir', default=FITNESS_DIR, help='训练数据目录；默认 FITNESS_HOME 或 ~/.lyzbcy-fitness')
    subparsers = parser.add_subparsers(dest='command', help='记录类型')

    # ── set ──
    p_set = subparsers.add_parser('set', help='记录一组训练')
    p_set.add_argument('--exercise', '-e', required=True, help='动作名称')
    p_set.add_argument('--weight', '-w', type=float, required=True, help='原始负重数值，单位见 --weight-unit')
    p_set.add_argument('--weight-unit', type=str.lower, choices=['kg', 'lb', 'plate'], default='kg')
    p_set.add_argument('--equipment', help='记录器械来源，如示例器械A')
    p_set.add_argument('--reps', '-r', type=float, required=True, help='次数（允许最后半次）')
    p_set.add_argument('--rpe', type=int, help='RPE 1-10')
    p_set.add_argument('--session', '-s', help='push/pull/legs/... (不填自动推断)')
    p_set.add_argument('--muscle-group', '-m', help='肌群 (不填自动匹配)')
    p_set.add_argument('--set-num', type=int, help='组号 (不填自动计算)')
    p_set.add_argument('--date', '-d', help='日期 YYYY-MM-DD (默认今天)')
    p_set.add_argument('--note', '-n', help='备注')

    # ── session_start ──
    p_start = subparsers.add_parser('session_start', help='开始训练')
    p_start.add_argument('--session', '-s', required=True, help='push/pull/legs/...')
    p_start.add_argument('--date', '-d', help='日期')
    p_start.add_argument('--note', '-n', help='备注')

    # ── session_end ──
    p_end = subparsers.add_parser('session_end', help='结束训练')
    p_end.add_argument('--session', '-s', help='push/pull/legs/...')
    p_end.add_argument('--date', '-d', help='日期')
    p_end.add_argument('--note', '-n', help='备注')

    # ── bodyweight ──
    p_bw = subparsers.add_parser('bodyweight', help='记录体重')
    p_bw.add_argument('--value', '-v', type=float, required=True, help='体重(kg)')
    p_bw.add_argument('--date', '-d', help='日期')

    # ── note ──
    p_note = subparsers.add_parser('note', help='添加备注')
    p_note.add_argument('--note', '-n', required=True, help='备注内容')
    p_note.add_argument('--session', '-s', help='session 类型')
    p_note.add_argument('--date', '-d', help='日期')

    for action_parser in (p_set, p_start, p_end):
        action_parser.add_argument('--time', help='实际训练时间（北京时间 HH:MM 或 HH:MM:SS）')

    args = parser.parse_args()
    global RECORDS_FILE, CONFIG_FILE, EXERCISES_FILE
    folder = Path(args.data_dir).expanduser().resolve()
    RECORDS_FILE, CONFIG_FILE, EXERCISES_FILE = [str(folder/n) for n in ('records.jsonl','config.json','exercises.json')]
    for name in ('weight', 'reps', 'value'):
        value = getattr(args, name, None)
        if value is not None and (not math.isfinite(value) or value < 0):
            parser.error(f'{name} 必须是有限非负数')
    if args.command == 'set' and args.rpe is not None and not 1 <= args.rpe <= 10:
        parser.error('rpe 必须在1–10之间')
    if args.command in ('session_start', 'session_end'):
        rows = get_today_records(getattr(args, 'date', None))
        last_end = max((i for i, r in enumerate(rows) if r.get('action') == 'session_end'), default=-1)
        last_activity = max((i for i, r in enumerate(rows) if r.get('action') in ['set','cardio','session_start']), default=-1)
        if args.command == 'session_end' and last_end >= 0 and last_end >= last_activity:
            print('已有收工记录，未重复追加'); return

    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        'set': add_set,
        'session_start': add_session_start,
        'session_end': add_session_end,
        'bodyweight': add_bodyweight,
        'note': add_note,
    }
    try:
        dispatch[args.command](args)
    except ValueError as error:
        parser.error(str(error))


if __name__ == '__main__':
    try:
        main()
    finally:
        try:
            from update_skill import start_background
            start_background()
        except Exception:
            pass
