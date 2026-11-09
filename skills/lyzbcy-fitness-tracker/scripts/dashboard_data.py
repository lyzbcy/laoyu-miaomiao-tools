#!/usr/bin/env python3
"""Jekyll fitness dashboard schema, shared with the production dashboard."""

import json
import os
from pathlib import Path
import runtime
from datetime import datetime, timedelta, timezone
from collections import defaultdict

TZ = timezone(timedelta(hours=8))

# ===== 动作名归一化 & 引体向上负重/辅助标注（2026-08-16）=====
# 哈克深蹲 = 正向哈克深蹲（同一动作，历史两种叫法）
EXERCISE_ALIASES = {
    "哈克深蹲": "正向哈克深蹲",
}

def normalize_exercise(name):
    return EXERCISE_ALIASES.get(name, name)

def label_pullup_pr(ex_name, weight, note):
    """引体向上家族 PR：区分 辅助/负重/自重，防止 60kg 辅助被误读为大重量"""
    if "引体" not in ex_name:
        return ex_name
    if "辅助" in (note or ""):
        return ex_name + "（辅助）"
    if weight and weight > 0:
        return ex_name + "（负重）"
    return ex_name + "（自重）"

def load_jsonl(path):
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

def parse_date(s):
    return datetime.fromisoformat(s).date() if isinstance(s, str) else s

def get_fun_comparison(volume_kg):
    """将训练量转换为生动的参照物描述。
    按总重量从高到低匹配，优先选择数量在 1-20 之间的参照物（最直观）。"""
    refs = [
        (150000, "头蓝鲸 🐋"),
        (80000,  "架空客A320 ✈️"),
        (40000,  "辆重型卡车 🚛"),
        (12000,  "辆中型巴士 🚌"),
        (6000,   "头成年非洲象 🐘"),
        (1500,   "辆家用小轿车 🚗"),
        (600,    "架三角钢琴 🎹"),
        (200,    "辆重型摩托车 🏍️"),
    ]
    # 优先选数量在 1-20 之间的，然后按重量从大到小选
    candidates = []
    for weight, desc in refs:
        count = volume_kg / weight
        if 1 <= count <= 20:
            candidates.append((count, weight, desc))
    if not candidates:
        # 没在1-20区间的，取最接近1的那个
        best = min(refs, key=lambda r: abs(volume_kg / r[0] - 1))
        count = volume_kg / best[0]
        candidates = [(count, best[0], best[1])]
    # 按数量从小到大排列（越少越震撼："举起了一架飞机" > "举起了15辆摩托车"）
    candidates.sort(key=lambda x: x[0])
    count, weight, desc = candidates[0]
    if count <= 1.2:
        return f"相当于举起了一{desc}"
    elif count < 10:
        return f"相当于举起了 {count:.1f} {desc}"
    else:
        return f"相当于举起了 {count:.0f} {desc}"

def get_nutrition_snapshot(nutrition_dir):
    """
    从营养数据中读取最近 7 天的摘要，供健身看板联动显示。
    返回 null 如果没有营养数据。
    """
    if not nutrition_dir:
        return None
    if not os.path.isdir(nutrition_dir):
        return None

    today = datetime.now(TZ).date()
    recent = []

    for fname in os.listdir(nutrition_dir):
        if not fname.endswith(".json") or not fname.startswith("20"):
            continue
        try:
            date_str = fname.replace(".json", "")
            d = datetime.fromisoformat(date_str).date()
            if not 0 <= (today - d).days <= 6:
                continue
            fpath = os.path.join(nutrition_dir, fname)
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            summary = data.get("summary", {})
            total_cal = summary.get("totalCalories", 0)
            total_protein = summary.get("totalProtein", 0)
            if total_cal > 0 or total_protein > 0:
                recent.append({
                    "date": date_str,
                    "calories": total_cal,
                    "protein": total_protein
                })
        except:
            pass

    if not recent:
        # 再捞 config 看目标
        config_path = os.path.join(nutrition_dir, "config.json")
        targets = None
        if os.path.exists(config_path):
            try:
                with open(config_path, encoding="utf-8") as f:
                    cfg = json.load(f)
                targets = {
                    "calories": cfg.get("dailyCalorieTarget", 1800),
                    "protein": cfg.get("proteinTarget", 120)
                }
            except:
                pass
        if targets:
            return {"targets": targets, "recent": []}
        return None

    # 平均
    avg_cal = round(sum(r["calories"] for r in recent) / len(recent))
    avg_protein = round(sum(r["protein"] for r in recent) / len(recent))

    # 目标
    config_path = os.path.join(nutrition_dir, "config.json")
    targets = None
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                cfg = json.load(f)
            targets = {
                "calories": cfg.get("dailyCalorieTarget", 1800),
                "protein": cfg.get("proteinTarget", 120)
            }
        except:
            pass

    return {
        "avg_calories": avg_cal,
        "avg_protein": avg_protein,
        "days": len(recent),
        "targets": targets,
        "recent": sorted(recent, key=lambda x: x["date"])
    }


def export_jekyll(folder, config=None):
    folder = Path(folder)
    config = runtime.config(folder) if config is None else config
    publish_notes = config.get("blog", {}).get("include_notes") is True
    # 加载数据
    records = load_jsonl(folder/"records.jsonl")
    # 防御：跳过缺 date 字段的脏记录（增量手写 JSONL 可能偶发漏字段）
    records = [r for r in records if r.get("date")]
    # 动作名归一化（别名合并）
    for r in records:
        if r.get("exercise"):
            r["exercise"] = normalize_exercise(r["exercise"])
    # 筛选 set 记录
    sets = [r for r in records if r.get("action") == "set"]
    sessions_starts = [r for r in records if r.get("action") == "session_start"]
    sessions_ends = [r for r in records if r.get("action") == "session_end"]

    # 按日期分组
    sessions_by_date = {}
    for r in records:
        d = r.get("date")
        if d not in sessions_by_date:
            sessions_by_date[d] = {"start": None, "end": None, "sets": [], "split": ""}
        if r.get("action") == "session_start":
            sessions_by_date[d]["start"] = r
            sessions_by_date[d]["split"] = r.get("session", "")
        elif r.get("action") == "session_end":
            sessions_by_date[d]["end"] = r
            if sessions_by_date[d]["start"] is None:
                sessions_by_date[d]["split"] = r.get("session", "")
        elif r.get("action") == "set":
            sessions_by_date[d]["sets"].append(r)

    # 每个训练日的摘要
    session_summaries = []
    for d in sorted(sessions_by_date.keys(), reverse=True):
        sess = sessions_by_date[d]
        if not sess["sets"]:
            continue
        total_sets = len(sess["sets"])
        total_volume = sum((s.get("weight") or 0) * s.get("reps", 0) for s in sess["sets"])
        exercises_done = sorted(set(s["exercise"] for s in sess["sets"]))
        # 估算时长：有 session_start 用 start→end，没有则用首组→end
        if sess["end"]:
            try:
                end_ts = datetime.fromisoformat((sess["end"].get("endTime") or sess["end"]["ts"]).replace("Z", "+00:00")).replace(tzinfo=None)
                if sess["start"]:
                    start_ts = datetime.fromisoformat((sess["start"].get("endTime") or sess["start"]["ts"]).replace("Z", "+00:00")).replace(tzinfo=None)
                elif sess["sets"]:
                    # 无 session_start 时用第一组 set 的时间戳
                    start_ts = datetime.fromisoformat((sess["sets"][0].get("endTime") or sess["sets"][0]["ts"]).replace("Z", "+00:00")).replace(tzinfo=None)
                else:
                    start_ts = None
                if start_ts:
                    duration_min = round((end_ts - start_ts).total_seconds() / 60)
                else:
                    duration_min = None
            except:
                duration_min = None
        else:
            duration_min = None

        estimated = any(x.get("weightEstimated") is True for x in sess["sets"])
        session_summaries.append({
            "date": d,
            "split": sess["split"],
            "split_label": {"push": "推日", "pull": "拉日", "legs": "腿日", "upper": "上身", "lower": "下身", "full_body": "全身", "cardio": "有氧"}.get(sess["split"], sess["split"]),
            "total_sets": total_sets,
            "total_volume": round(total_volume, 1),
            "exercises": exercises_done,
            "duration_min": duration_min,
            **({"volume_estimated": True} if estimated else {}),
            "note": (sess["start"].get("note", "") if sess["start"] else (sess["end"].get("note", "") if sess["end"] else "")) if publish_notes else ""
        })
        if estimated:
            note = session_summaries[-1]["note"]
            session_summaries[-1]["note"] = (note + " · " if note else "") + "训练量含器械片数等效估算"


    # PR 列表（从 config 提取）
    prs = []
    for muscle_group, ex_dict in config.get("personalRecords", {}).items():
        for ex_name, pr_data in ex_dict.items():
            ex_name = normalize_exercise(ex_name.replace("_", " "))
            prs.append({
                "exercise": label_pullup_pr(ex_name, pr_data.get("weight", 0), pr_data.get("note", "")),
                "muscle_group": muscle_group,
                "weight": pr_data.get("weight", 0),
                "reps": pr_data.get("reps", 0),
                "note": pr_data.get("note", "") if publish_notes else "",
                "volume": pr_data.get("weight", 0) * pr_data.get("reps", 0)
            })
    prs.sort(key=lambda x: x["volume"], reverse=True)

    # 训练频率统计
    all_dates = sorted(set(r["date"] for r in records if r.get("action") in ("session_start", "set")))
    session_count = len(session_summaries)
    if all_dates:
        first_date = parse_date(all_dates[0])
        last_date = parse_date(all_dates[-1])
        total_weeks = max(1, (last_date - first_date).days / 7)
        session_count = len(session_summaries)
        avg_per_week = round(session_count / total_weeks, 1)

        # 近4周频率
        four_weeks_ago = last_date - timedelta(days=28)
        recent_sessions = [s for s in session_summaries if parse_date(s["date"]) >= four_weeks_ago]
        recent_count = len(recent_sessions)
    else:
        avg_per_week = 0
        recent_count = 0

    # 肌肉平衡分析
    muscle_volume = defaultdict(float)
    for s in sets:
        muscle_volume[s.get("muscleGroup", "unknown")] += (s.get("weight") or 0) * s.get("reps", 0)

    muscle_labels = {
        "chest": "胸", "upper_chest": "上胸", "back": "背", "lats": "背阔",
        "mid_back": "中背", "shoulders": "肩前束", "lateral_delt": "肩中束",
        "rear_delt": "肩后束", "biceps": "肱二头肌", "triceps": "肱三头肌",
        "quads": "股四头肌", "hamstrings": "腘绳肌", "glutes": "臀",
        "calves": "小腿", "core": "核心", "inner_thigh": "大腿内侧",
        "forearms": "前臂", "brachioradialis": "肱桡肌"
    }

    muscle_balance = []
    for mg in sorted(muscle_volume.keys()):
        muscle_balance.append({
            "group": mg,
            "label": muscle_labels.get(mg, mg),
            "total_volume": round(muscle_volume[mg], 1)
        })
    muscle_balance.sort(key=lambda x: x["total_volume"], reverse=True)
    # 派生、各肌群占总训练量的百分比（看板堆叠条直接用，避免 Liquid 循环计算）
    total_muscle_volume = sum(m["total_volume"] for m in muscle_balance)
    for m in muscle_balance:
        m["percentage"] = round(m["total_volume"] * 100.0 / total_muscle_volume, 1) if total_muscle_volume > 0 else 0
    # 修正浮点累积误差（14 项 round 后可能和=99.9）：把误差吸收进最大那一项
    if muscle_balance:
        pct_sum = round(sum(m["percentage"] for m in muscle_balance), 1)
        if pct_sum != 100.0:
            muscle_balance[0]["percentage"] = round(muscle_balance[0]["percentage"] + (100.0 - pct_sum), 1)

    # 训练量趋势（周汇总）
    weekly_volume = defaultdict(float)
    weekly_sessions = defaultdict(int)
    for s in sets:
        d = parse_date(s["date"])
        # ISO week
        week_key = d.isocalendar()[:2]  # (year, week)
        weekly_volume[week_key] += (s.get("weight") or 0) * s.get("reps", 0)
        weekly_sessions[week_key] += 1

    volume_trend = []
    # 派生：标记本周（看板柱状图高亮用）
    today_iso = datetime.now(TZ).isocalendar()
    current_week_key = (today_iso[0], today_iso[1])
    for wk in sorted(weekly_volume.keys()):
        year, week = wk
        volume_trend.append({
            "week": f"{year}-W{week:02d}",
            "volume": round(weekly_volume[wk], 1),
            "sessions": weekly_sessions[wk],
            "is_current": wk == current_week_key,
            "is_latest": False  # 循环后回填最后一个为 True
        })

    # 回填：最后一个有数据的周标记为 is_latest（看板高亮最新数据用）
    if volume_trend:
        volume_trend[-1]["is_latest"] = True

    # 最喜欢的动作（按频次）
    exercise_freq = defaultdict(int)
    exercise_weight_max = defaultdict(float)
    exercise_volume = defaultdict(float)
    for s in sets:
        ex = s["exercise"]
        exercise_freq[ex] += 1
        exercise_weight_max[ex] = max(exercise_weight_max[ex], (s.get("weight") or 0))
        exercise_volume[ex] += (s.get("weight") or 0) * s.get("reps", 0)

    top_exercises = sorted(exercise_freq.items(), key=lambda x: x[1], reverse=True)
    # 每个动作的最新数据（最近日期、最高重量、最高次数等）
    exercise_metrics = []
    for ex, count in top_exercises:
        ex_sets = [s for s in sets if s["exercise"] == ex]
        ex_dates = sorted(set(s["date"] for s in ex_sets))
        # 最近的训练组
        last_date = ex_dates[-1] if ex_dates else None
        last_sets = [s for s in ex_sets if s["date"] == last_date] if last_date else []
        last_weight = max(((s.get("weight") or 0) for s in last_sets), default=0)
        last_reps = max((s.get("reps", 0) for s in last_sets), default=0)

        exercise_metrics.append({
            "name": ex,
            "total_sets": count,
            "max_weight": max(((s.get("weight") or 0) for s in ex_sets), default=0),
            "max_reps": max((s.get("reps", 0) for s in ex_sets), default=0),
            "last_date": last_date,
            "last_weight": last_weight,
            "last_reps": last_reps,
            "total_volume": round(exercise_volume[ex], 1)
        })


    # ── 有氧聚合（action: cardio / vo2max / session_summary）──
    cardios = sorted([r for r in records if r.get("action") == "cardio"], key=lambda r: r["date"])
    vo2s = [r for r in records if r.get("action") == "vo2max"]
    hist_strength = [r for r in records if r.get("action") == "session_summary"]

    cardio_by_type = defaultdict(lambda: {"count": 0, "minutes": 0.0, "kcal": 0.0, "km": 0.0})
    for c in cardios:
        t = c.get("exercise", "其他")
        cardio_by_type[t]["count"] += 1
        cardio_by_type[t]["minutes"] += c.get("durationMin", 0)
        cardio_by_type[t]["kcal"] += c.get("activeKcal", 0) or 0
        cardio_by_type[t]["km"] += c.get("distanceKm", 0) or 0
    cardio_types = [
        {"type": t, "count": v["count"], "minutes": round(v["minutes"], 1),
         "kcal": round(v["kcal"], 1), "km": round(v["km"], 2)}
        for t, v in sorted(cardio_by_type.items(), key=lambda x: -x[1]["count"])
    ]
    # 近12次有氧明细（看板用）
    cardio_recent = sorted(cardios, key=lambda x: x["date"], reverse=True)[:12]
    cardio_recent = [{
        "date": c["date"], "exercise": c.get("exercise", ""),
        "duration_min": c.get("durationMin"), "distance_km": c.get("distanceKm"),
        "avg_hr": c.get("avgHr"), "intensity": c.get("intensity"),
        "active_kcal": c.get("activeKcal"), "strokes": c.get("strokes")
    } for c in cardio_recent]
    vo2_sorted = sorted(vo2s, key=lambda x: x["date"])
    cardio_section = {
        "total_sessions": len(cardios),
        "total_minutes": round(sum(c.get("durationMin", 0) for c in cardios), 1),
        "total_kcal": round(sum(c.get("activeKcal", 0) or 0 for c in cardios), 1),
        "total_km": round(sum(c.get("distanceKm", 0) or 0 for c in cardios), 2),
        "first_date": cardios[0]["date"] if cardios else None,
        "last_date": cardios[-1]["date"] if cardios else None,
        "by_type": cardio_types,
        "recent": cardio_recent,
        "vo2max": {
            "first": vo2_sorted[0]["value"] if vo2_sorted else None,
            "latest": vo2_sorted[-1]["value"] if vo2_sorted else None,
            "latest_date": vo2_sorted[-1]["date"] if vo2_sorted else None,
            "history": [{"date": v["date"], "value": v["value"]} for v in vo2_sorted],
        },
        "history_strength_sessions": len(hist_strength),
        "history_strength_minutes": round(sum(h.get("durationMin", 0) for h in hist_strength), 1),
    }

    # ── 营养联动 ──
    nutrition_link = get_nutrition_snapshot(config.get("nutrition_dir")) if config.get("blog", {}).get("include_nutrition") is True else None

    # ── 输出 ──
    output = {
        "generated_at": max((r.get("ts", r["date"]) for r in records), default=None),
        "overview": {
            "total_sessions": session_count,
            "total_sessions_recent_4w": recent_count,
            "avg_sessions_per_week": avg_per_week,
            "total_sets": len(sets),
            "total_volume": round(sum((s.get("weight") or 0) * s.get("reps", 0) for s in sets), 1),
            "date_range": {
                "first": all_dates[0] if all_dates else None,
                "last": all_dates[-1] if all_dates else None
            },
            "preferences": config.get("preferences", {}) if config.get("blog", {}).get("include_preferences") is True else {},
            # 派生：看板 KPI 卡直接用（避免 Liquid size 过滤器链）
            "muscle_groups_count": len(muscle_volume),
            "exercises_count": len(exercise_metrics),
            "fun_fact": get_fun_comparison(round(sum((s.get("weight") or 0) * s.get("reps", 0) for s in sets), 1))
        },
        "sessions": session_summaries,
        "personal_records": prs,
        "muscle_balance": muscle_balance,
        "volume_trend": volume_trend,
        "exercises": exercise_metrics,
        "nutrition_link": nutrition_link,
        "cardio": cardio_section
    }

    return output
