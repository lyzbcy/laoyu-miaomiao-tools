#!/usr/bin/env python3
"""Offline fitness poster: prepare facts, edit copy/sticker IDs, render with Pillow."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import random
import tempfile
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets' / 'daily-poster'
TZ = ZoneInfo('Asia/Shanghai')
VERSION = '1.2.0'
W, H = 1440, 2160
PAPER, INK, ORANGE, TEAL = '#faf3e6', '#272b28', '#df572e', '#207c70'
CTA = '获取同款健身记录，可以关注我“捞鱼的博客”公众号，回复“健身”获取。'
DEFAULT_BRAND = {'title': '捞鱼的训练小报', 'watermark': '捞鱼',
                 'account': '捞鱼的博客', 'keyword': '健身', 'cta': CTA, 'asset_credit': '素材：捞鱼'}


def normalize_brand(value=None):
    value = value or {}
    if not isinstance(value, dict) or set(value)-set(DEFAULT_BRAND):
        raise ValueError('brand 包含不支持的字段')
    brand = {**DEFAULT_BRAND, **value}
    if 'cta' not in value and ('account' in value or 'keyword' in value):
        brand['cta'] = f"获取同款健身记录，可以关注我“{brand['account']}”公众号，回复“{brand['keyword']}”获取。"
    for k, limit in [('title', 28), ('watermark', 12), ('account', 30), ('keyword', 12), ('cta', 100), ('asset_credit', 60)]:
        if not isinstance(brand[k], str) or not 1 <= len(brand[k]) <= limit:
            raise ValueError(f'brand.{k} 长度应为1–{limit}字')
    return brand


GROUPS = {
    'chest': '胸', 'upper_chest': '胸', 'back': '背', 'lats': '背', 'mid_back': '背',
    'shoulders': '肩', 'lateral_delt': '肩', 'rear_delt': '肩', 'biceps': '二头',
    'triceps': '三头', 'quads': '腿', 'hamstrings': '腿', 'glutes': '臀',
    'calves': '小腿', 'core': '核心', 'forearms': '前臂',
}
DEFAULT_STICKERS = {'hero_left': 'remaster_workout_male', 'hero_right': 'remaster_workout_female',
                    'today': 'remaster_admire', 'history': 'remaster_surprised',
                    'rest': 'remaster_rest', 'meal': 'remaster_meal', 'footer': 'remaster_cheer'}
ROLE_CONTEXTS = {'hero_left': 'workout', 'hero_right': 'workout', 'today': 'achievement',
                 'history': 'accumulation', 'rest': 'recovery', 'meal': 'nutrition', 'footer': 'encouragement'}
BODY_PARTS = {'胸': '胸部', '背': '背部', '肩': '肩部', '二头': '二头', '三头': '三头',
              '腿': '腿部', '臀': '臀部', '小腿': '小腿', '核心': '核心', '前臂': '前臂', '其他': '其他部位'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as f:
        f.write(data)
        tmp = Path(f.name)
    tmp.replace(path)


def dec(value):
    if isinstance(value, bool):
        raise ValueError('重量/次数不能是布尔值')
    try:
        n = Decimal(str(value))
    except InvalidOperation as e:
        raise ValueError(f'不是有效数字: {value!r}') from e
    if not n.is_finite() or n < 0:
        raise ValueError(f'数字必须非负且有限: {value!r}')
    return n


def fmt(n, places=2):
    return format(Decimal(str(n)).quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP), 'f').rstrip('0').rstrip('.') if places else str(round(n))


def stamp(record):
    value = record.get('endTime') or record.get('ts')
    if not value:
        return None
    d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return (d.replace(tzinfo=TZ) if d.tzinfo is None else d.astimezone(TZ))


def read_records(path):
    data = Path(path).read_bytes()
    rows = []
    for i, line in enumerate(data.decode('utf-8-sig').splitlines(), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            if not isinstance(r, dict):
                raise ValueError('记录必须是对象')
            rows.append(r)
        except (ValueError, TypeError) as e:
            raise ValueError(f'records.jsonl 第 {i} 行无效: {e}') from e
    return rows, sha(data)


def aggregate(rows, date):
    """Read-only ledger aggregation. Never guess bodyweight, sides or free-text fixes."""
    datetime.strptime(date, '%Y-%m-%d')
    day = [r for r in rows if r.get('date') == date]
    sets = [r for r in day if r.get('action') == 'set']
    cardio = [r for r in day if r.get('action') == 'cardio']
    if not sets and not cardio:
        raise ValueError(f'{date} 没有逐组训练/有氧记录，不能生成训练总结')
    history = [r for r in rows if r.get('action') == 'set' and r.get('date', '') <= date]

    def volume(items):
        total = Decimal(0)
        uncounted = 0
        for r in items:
            reps = dec(r.get('reps', 0))
            if r.get('weight') is None or dec(r['weight']) == 0:
                uncounted += 1
            else:
                total += dec(r['weight']) * reps
        return float(total), uncounted

    today_kg, unknown = volume(sets)
    history_kg, _ = volume(history)
    times = sorted(t for r in sets + cardio if (t := stamp(r)))
    if any(t.date().isoformat() != date for t in times):
        raise ValueError('date 与北京时间时间戳不符，先核对记录')
    start_events = sorted(t for r in day if r.get('action') == 'session_start' and (t := stamp(r)))
    end_events = sorted(t for r in day if r.get('action') == 'session_end' and (t := stamp(r)))
    # End is valid only if it comes after the last reported activity; later sets mean reopened session.
    complete = bool(end_events and times and end_events[-1] >= times[-1]
                    and (not start_events or end_events[-1] >= start_events[-1]))
    start, end = (start_events[0] if start_events else (times[0] if times else None)), (end_events[-1] if complete else (times[-1] if times else None))
    exact = bool(start_events and complete)
    if start and end and end < start:
        raise ValueError('结束时间早于开始时间')
    mins = round((end - start).total_seconds() / 60) if start and end else None
    timing_basis = '训练起止记录' if exact else ('首组至收工记录跨度' if complete else '训练记录跨度 · 尚未收工')
    if len(start_events) > 1:
        timing_basis = '多段训练首尾跨度（含间歇）'
        exact = False
    if not sets and cardio and not start_events:
        # Cardio's timestamp is its end; durationMin gives the actual activity start.
        ctimes = [(stamp(r) - timedelta(minutes=float(dec(r['durationMin']))), stamp(r))
                  for r in cardio if stamp(r) and r.get('durationMin') is not None]
        if len(ctimes) == len(cardio):
            start, end = min(x[0] for x in ctimes), max(x[1] for x in ctimes)
            mins = round((end - start).total_seconds() / 60)
            timing_basis = '有氧结束时间与时长推算' if len(cardio) == 1 else '多段有氧首尾跨度（含间歇）'
            complete = True
    muscles = list(dict.fromkeys(GROUPS.get(r.get('muscleGroup'), '其他') for r in sets))
    sessions = {r.get('session') for r in sets}
    if not sets:
        label, title = '有氧训练日', '今天也动起来了'
    elif sessions == {'full_body'} or len(set(muscles) & {'胸', '背', '腿', '臀'}) >= 2:
        label, title = '全身训练日', '全身都安排上了'
    elif set(muscles) <= {'背', '二头', '前臂'}:
        label, title = '练背日', '今天认真练背了'
    elif set(muscles) <= {'胸', '肩', '三头'}:
        label, title = ('练胸日', '胸肌今天营业了') if '胸' in muscles else ('肩臂训练日', '肩臂也安排上了')
    elif set(muscles) <= {'腿', '臀', '小腿'}:
        label, title = '腿臀训练日', '腿臀今天营业了'
    else:
        label, title = '综合训练日', '今天练得很丰富'
    exercises = defaultdict(list)
    for r in sets:
        exercises[r.get('exercise', '未命名动作')].append(r)
    highlights = []
    for name, items in list(exercises.items())[:3]:
        detail = set_detail(items)
        highlights.append({'name': name, 'detail': detail})
    if not sets:
        highlights = [{'name': r.get('exercise', '有氧'), 'detail': f"{fmt(r['durationMin'])}分钟"} for r in cardio[:3]]
    note_count = sum(r.get('action') == 'note' for r in rows if r.get('date', '') <= date)
    facts = {
        'date': date, 'complete': complete, 'start': start.strftime('%H:%M') if start else None,
        'end': end.strftime('%H:%M') if end else None, 'duration_minutes': mins,
        'timing_basis': timing_basis, 'exact_timing': exact, 'today_kg': today_kg,
        'history_kg': history_kg, 'history_since': min((r['date'] for r in history), default=None),
        'sets': len(sets), 'reps': float(sum((dec(r.get('reps', 0)) for r in sets), Decimal(0))),
        'exercises': len(exercises), 'uncounted_sets': unknown, 'cardio_sessions': len(cardio),
        'muscles': muscles, 'day_label': label, 'suggested_title': title, 'highlights': highlights,
        'exercise_summaries': [{'name': name, 'detail': set_detail(items)} for name, items in exercises.items()],
        'body_groups': body_groups(sets, cardio),
        'note_count': note_count,
        'volume_basis': '逐组原始记录重量×次数；自重、未知负重不折算；自由文本更正不自动改量',
    }
    return facts


def set_detail(items):
    parts = Counter(('自重/未知负重' if x.get('weight') in (None, 0) else f"{fmt(x['weight'])}kg") + f" × {x['reps']}次" for x in items)
    detail = ' / '.join(text + (f' × {n}组' if n > 1 else '') for text, n in parts.items())
    if len(detail) > 36:
        total = sum((dec(x.get('weight') or 0) * dec(x['reps']) for x in items), Decimal(0))
        detail = f"{len(items)}组 · {fmt(sum(dec(x['reps']) for x in items))}次 · 已记录训练量{fmt(total)}kg"
    return detail


def full_set_detail(items):
    """Preserve every weight/repetition combination; equal sets may be losslessly compressed."""
    parts = Counter(('未知负重' if x.get('weight') is None else '自重' if dec(x['weight']) == 0
                     else f"{fmt(x['weight'])}kg") + f" × {fmt(x['reps'])}次" for x in items)
    return ' / '.join(text + (f' × {n}组' if n > 1 else '') for text, n in parts.items())


def body_groups(sets, cardio):
    grouped = {}
    for r in sets:
        part = BODY_PARTS.get(GROUPS.get(r.get('muscleGroup'), '其他'), '其他部位')
        g = grouped.setdefault(part, {'part': part, 'items': {}, 'sets': 0, 'kg': Decimal(0)})
        g['items'].setdefault(r.get('exercise', '未命名动作'), []).append(r)
        g['sets'] += 1
        g['kg'] += dec(r.get('weight') or 0)*dec(r['reps'])
    result = []
    for g in grouped.values():
        result.append({'part': g['part'], 'sets': g['sets'], 'kg': float(g['kg']),
                       'items': [{'name': name, 'detail': full_set_detail(items), 'sets': len(items)}
                                 for name, items in g['items'].items()]})
    if cardio:
        result.append({'part': '有氧', 'sets': 0, 'kg': 0,
                       'items': [{'name': r.get('exercise', '有氧'),
                                  'detail': fmt(r['durationMin'])+'分钟', 'sets': 0} for r in cardio]})
    return result


def make_input(records, date, brand=None):
    rows, digest = read_records(records)
    facts = aggregate(rows, date)
    return {'schema_version': 2, 'source': {'records': str(Path(records).resolve()), 'sha256': digest},
            'facts': facts, 'brand': normalize_brand(brand), 'facts_sha256': sha(json.dumps(facts, sort_keys=True, ensure_ascii=False).encode()),
            'copy': {'title': facts['suggested_title'], 'day_label': facts['day_label'],
                     'tags': ' · '.join(facts['muscles']) or '有氧 · 活动一下',
                     'cheer': '好好练，也要好好吃饭',
                     'sticker_reasons': {key: '高清重绘版，适合'+context for key, context in ROLE_CONTEXTS.items()},
                     'stickers': DEFAULT_STICKERS.copy()}}


def catalog():
    return json.loads((ASSETS / 'stickers.json').read_text(encoding='utf-8'))


def validate_input(data, allow_stale=False):
    if data.get('schema_version') != 2:
        raise ValueError('模板已升级为全量分部位版，请重新 prepare')
    facts = data['facts']
    normalize_brand(data.get('brand'))
    if data['facts_sha256'] != sha(json.dumps(facts, sort_keys=True, ensure_ascii=False).encode()):
        raise ValueError('facts 已被改动，请重新 prepare；只编辑 copy')
    if not allow_stale:
        rows, digest = read_records(data['source']['records'])
        if digest != data['source']['sha256']:
            raise ValueError('训练记录已有变化，请重新 prepare，避免生成旧数据')
        if aggregate(rows, facts['date']) != facts:
            raise ValueError('聚合结果不一致，请重新 prepare')
    copy = data['copy']
    for key, limit in [('title', 18), ('day_label', 16), ('tags', 60), ('cheer', 40)]:
        if not isinstance(copy.get(key), str) or not copy[key].strip() or len(copy[key]) > limit:
            raise ValueError(f'copy.{key} 需为1–{limit}字')
    unknown = set(copy) - {'title', 'day_label', 'tags', 'cheer', 'stickers', 'sticker_reasons'}
    if unknown:
        raise ValueError(f'未知 copy 字段: {unknown}')
    choices = catalog()
    if set(copy['stickers']) != set(DEFAULT_STICKERS):
        raise ValueError('stickers 必须含完整的七个位置')
    reasons = copy.get('sticker_reasons', {})
    for role, key in copy['stickers'].items():
        if key not in choices:
            raise ValueError(f'未知表情编号: {key}')
        asset = choices[key]
        if ROLE_CONTEXTS[role] not in asset.get('contexts', []):
            raise ValueError(f'{role} 的表情 {key} 与该位置语义不符')
        if not isinstance(reasons.get(role), str) or not 3 <= len(reasons[role]) <= 100:
            raise ValueError(f'{role} 需填写3–100字的选图理由')
        if not asset.get('remastered') and '旧版' not in reasons[role]:
            raise ValueError(f'{role} 优先选高清重绘版；选旧版需在理由明确解释旧版更贴切')
    return facts, copy


@lru_cache(maxsize=128)
def font(size, bold=False):
    f = ImageFont.truetype(str(ASSETS / 'fonts' / 'NotoSansSC[wght].ttf'), size)
    f.set_variation_by_axes([850 if bold else 500])
    return f


class Canvas:
    def __init__(self, height=H):
        self.height = height
        self.im = Image.new('RGB', (W, height), PAPER)
        self.d = ImageDraw.Draw(self.im)
        self.boxes = []
        self.stickers = []
        rng = random.Random(20261031)
        # Restrained paper flecks; deterministic, no network or generative model.
        for _ in range(round(8000*height/H)):
            x, y = rng.randrange(W), rng.randrange(height)
            self.d.point((x, y), fill=rng.choice(['#eee6d6', '#f2eadc', '#fff9f0']))

    def panel(self, box, color, radius=28, shadow=True):
        x, y, x2, y2 = box
        if shadow:
            self.d.rounded_rectangle((x+4, y+7, x2+4, y2+7), radius=radius, fill='#e8ddcc')
        self.d.rounded_rectangle(box, radius=radius, fill=color)

    def text(self, text, box, size, color=INK, bold=False, center=False, min_size=20, max_lines=1):
        """Fit by measured glyph width/height. Refuse clipping rather than silently cut text."""
        x, y, x2, y2 = box
        if not (0 <= x < x2 <= W and 0 <= y < y2 <= self.height):
            raise ValueError(f'文字区域越界: {box}')
        text = str(text)
        for s in range(size, min_size-1, -1):
            f = font(s, bold)
            lines, line = [], ''
            for ch in text:
                if ch == '\n' or (line and self.d.textlength(line+ch, font=f) > x2-x):
                    lines.append(line)
                    line = '' if ch == '\n' else ch
                else:
                    line += ch
            if line:
                lines.append(line)
            lh = math.ceil(s * 1.35)
            if len(lines) <= max_lines and len(lines)*lh <= y2-y and all(self.d.textlength(t, font=f) <= x2-x for t in lines):
                break
        else:
            raise ValueError(f'文字过长，无法放入模板: {text!r}')
        yy = y + (y2-y-len(lines)*lh)/2
        for line in lines:
            xx = x + ((x2-x-self.d.textlength(line, font=f))/2 if center else 0)
            self.d.text((xx, yy), line, font=f, fill=color, anchor='lt', stroke_width=0)
            yy += lh
        self.boxes.append({'text': text, 'box': list(box), 'font_size': s, 'lines': len(lines)})

    def sticker(self, key, box):
        p = ASSETS / catalog()[key]['file']
        im = Image.open(p).convert('RGBA')
        bounds = im.getbbox()
        if bounds:
            im = im.crop(bounds)
        im.thumbnail((box[2]-box[0], box[3]-box[1]), Image.Resampling.LANCZOS)
        pos = (box[0]+(box[2]-box[0]-im.width)//2, box[3]+0-im.height)
        self.im.paste(im, pos, im)
        self.stickers.append({'id': key, 'file': catalog()[key]['file'], 'sha256': sha(p.read_bytes()), 'box': list(box)})

    def tape(self, x, y, angle=10, color='#e9c99a'):
        tile = Image.new('RGBA', (150, 42), color)
        tile.putalpha(155)
        tile = tile.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
        self.im.paste(tile, (x, y), tile)

    def vehicle(self, x, y, truck=False, scale=1.0):
        # Simple vector-style illustrations, not external images or emoji-font dependent.
        d = self.d
        def b(x1, y1, x2, y2): return (x+x1*scale, y+y1*scale, x+x2*scale, y+y2*scale)
        if truck:
            d.rounded_rectangle(b(66, 0, 208, 76), 6, '#d3ddd5', outline=INK, width=3)
            d.rounded_rectangle(b(0, 23, 66, 86), 8, '#eb9368', outline=INK, width=3)
            d.rectangle(b(13, 31, 49, 54), fill='#9bc8d1', outline=INK, width=2)
        else:
            d.rounded_rectangle(b(22, 0, 153, 67), 28, '#a7cdd0', outline=INK, width=3)
            d.rounded_rectangle(b(0, 40, 185, 91), 18, '#a7cdd0', outline=INK, width=3)
            d.rounded_rectangle(b(42, 11, 131, 43), 8, '#f0f5e9', outline=INK, width=2)
        for wx in ([40, 163] if truck else [35, 145]):
            d.ellipse(b(wx-18, 68, wx+18, 104), fill=INK)
            d.ellipse(b(wx-8, 78, wx+8, 94), fill='#f6ebd6')

    def watermarks(self, label='捞鱼'):
        overlay = Image.new('RGBA', (W, self.height))
        tile = Image.new('RGBA', (180, 90))
        ImageDraw.Draw(tile).text((10, 3), label, font=font(min(38, max(12, 150//len(label))), True), fill=(110, 94, 69, 25))
        tile = tile.rotate(27, expand=True, resample=Image.Resampling.BICUBIC)
        count = 0
        for yy in range(0, self.height, 265):
            for xx in range(-40 + (100 if yy//265 % 2 else 0), W, 275):
                overlay.alpha_composite(tile, (xx, yy))
                count += 1
        self.im = Image.alpha_composite(self.im.convert('RGBA'), overlay).convert('RGB')
        return count


def comparison(kg, unit_kg, vehicle):
    if kg <= 0:
        return '自重/有氧未折算'
    n = Decimal(str(kg)) / unit_kg
    value = format(n.quantize(Decimal('.1'), rounding=ROUND_HALF_UP), 'f')
    if value == '0.0':
        return f'＜ 0.1 辆{vehicle}'
    return f'≈ {value} 辆{vehicle}'


def line_count(text, width, size, bold=False):
    f = font(size, bold)
    lines, line = 1, ''
    for ch in text:
        if ch == '\n' or (line and f.getlength(line+ch) > width):
            lines += 1
            line = '' if ch == '\n' else ch
        else:
            line += ch
    return lines


def plan_groups(groups):
    bottoms = [1530, 1530]
    plans = []
    for group in groups:
        col = 0 if bottoms[0] <= bottoms[1] else 1
        x, y = [48, 736][col], bottoms[col]
        cursor, items = y+122, []
        for item in group['items']:
            nh = line_count(item['name'], 588, 29, True)*40
            dh = line_count(item['detail'], 588, 25)*35
            items.append({'item': item, 'y': cursor, 'name_height': nh, 'detail_height': dh})
            cursor += nh+dh+23
        bottom = cursor+10
        plans.append({'group': group, 'x': x, 'y': y, 'bottom': bottom, 'items': items})
        bottoms[col] = bottom+28
    return plans, max(bottoms)


def render(data, out, allow_stale=False):
    facts, copy = validate_input(data, allow_stale)
    brand = normalize_brand(data.get("brand"))
    plans, list_bottom = plan_groups(facts['body_groups'])
    # A longer workout gets a longer image; no action is dropped to preserve a fixed ratio.
    recovery_y = list_bottom+20
    note_y, cta_y = recovery_y+210, recovery_y+320
    height = max(H, cta_y+210)
    if height > 30000:
        raise ValueError('当天记录过多，单图超过30000像素；请检查日期或重复导入，不截断动作')
    c = Canvas(height)
    s = copy['stickers']
    c.panel((48, 34, 605, 156), '#f8d7c3', 10)
    c.text(brand['title'], (78, 44, 585, 110), 49, bold=True)
    c.text(facts['date'].replace('-', '.'), (82, 110, 500, 146), 28)
    c.panel((838, 48, 1380, 113), TEAL, 30, False)
    c.text('今日训练 · 已收工' if facts['complete'] else '记录快照 · 训练进行中', (860, 52, 1360, 108), 32, '#fff6e8', True, True)
    c.text('一组一组记下来，每次都算数', (875, 120, 1360, 160), 25, center=True)
    c.tape(490, 20, -8)
    c.panel((250, 205, 1190, 355), '#f8c4a4', 16, False)
    c.text(copy['title'], (282, 208, 1158, 350), 104, bold=True, center=True, min_size=46)
    c.sticker(s['hero_left'], (18, 155, 292, 430))
    c.sticker(s['hero_right'], (1160, 145, 1420, 423))
    c.text(copy['day_label'], (350, 369, 1090, 421), 37, TEAL, True, True)
    c.text(copy['tags'], (265, 420, 1175, 465), 29, center=True, max_lines=1)
    c.panel((242, 492, 1198, 587), ORANGE, 45, False)
    duration = f"{facts['duration_minutes']}分钟" if facts['duration_minutes'] is not None else '时长未知'
    timeline = f"{facts['start'] or '未知'} → {facts['end'] or '未知'}  |  {duration}"
    c.text(timeline, (265, 497, 1175, 579), 49, '#fff9eb', True, True)
    c.text(facts['timing_basis'], (210, 591, 1230, 637), 27, center=True)
    # Equal parallel capacity panels, original sticker images in reserved bottom-right slots.
    for x, color, title, kg, since, comp, basis, sticker, truck in [
        (48, '#f9dfc9', '今日搬铁', facts['today_kg'], '已记录负重训练量', comparison(facts['today_kg'], Decimal(2000), '小汽车'), '按 2 吨/辆估算', s['today'], False),
        (736, '#d8eae2', '历史累计', facts['history_kg'], '自 '+(facts['history_since'] or facts['date']).replace('-', '.')+' 逐组记录以来', comparison(facts['history_kg'], Decimal(20000), '大卡车'), '按 20 吨/辆估算', s['history'], True),
    ]:
        c.panel((x, 666, x+656, 1236), color, 24)
        col = TEAL if truck else '#c74621'
        c.text(title, (x+38, 686, x+614, 755), 51, col, True)
        c.text(fmt(kg/1000)+' 吨', (x+35, 768, x+615, 920), 113, col, True, min_size=55)
        c.text(since, (x+38, 916, x+618, 965), 28, min_size=22)
        c.text(comp, (x+38, 977, x+618, 1040), 37, col, True)
        c.text(basis, (x+38, 1045, x+370, 1088), 24)
        c.vehicle(x+40, 1122, truck, .95)
        c.sticker(sticker, (x+368, 1048, x+644, 1240))
        c.tape(x+480, 648, -11)
    c.panel((130, 1273, 1310, 1373), '#f5d47e', 16)
    stats = f"{facts['exercises']} 个动作  ·  {facts['sets']} 组  ·  {fmt(facts['reps'])} 次"
    if facts['cardio_sessions']:
        stats += f"  ·  {facts['cardio_sessions']} 段有氧"
    c.text(stats, (150, 1280, 1290, 1360), 45, bold=True, center=True)
    c.text('今天练了啥 · 完整清单', (120, 1400, 1320, 1475), 48, TEAL, True, True)
    c.text('按主要训练部位归类 · 相同动作合并，全部训练组保留', (130, 1478, 1310, 1520), 25, center=True)
    for plan in plans:
        g, x, y = plan['group'], plan['x'], plan['y']
        c.panel((x, y, x+656, plan['bottom']), '#fffaf0', 20)
        c.panel((x+22, y+20, x+634, y+76), '#d8eae2', 12, False)
        c.text(g['part'], (x+40, y+22, x+610, y+73), 35, TEAL, True)
        meta = f"{len(g['items'])} 个动作 · {g['sets']} 组 · {fmt(g['kg'])} kg" if g['part'] != '有氧' else f"{len(g['items'])} 段有氧"
        c.text(meta, (x+36, y+83, x+620, y+119), 24, '#646a60')
        for i, row in enumerate(plan['items']):
            item, yy, nh, dh = row['item'], row['y'], row['name_height'], row['detail_height']
            c.text(item['name'], (x+34, yy, x+622, yy+nh), 29, bold=True, min_size=29, max_lines=100)
            c.text(item['detail'], (x+34, yy+nh, x+622, yy+nh+dh), 25, '#596054', min_size=25, max_lines=100)
            if i < len(plan['items'])-1:
                c.d.line((x+34, yy+nh+dh+10, x+622, yy+nh+dh+10), fill='#e5dece', width=1)
    c.sticker(s['rest'], (65, recovery_y, 330, recovery_y+200))
    c.sticker(s['meal'], (1110, recovery_y, 1375, recovery_y+200))
    c.text(copy['cheer'], (350, recovery_y+15, 1090, recovery_y+105), 34, TEAL, True, True, max_lines=2)
    c.text('练完记得休息 · 练后好好吃饭', (350, recovery_y+110, 1090, recovery_y+160), 26, center=True)
    c.text('训练量＝已记录重量×次数；自重及未知重量未折算。', (70, note_y, 1370, note_y+36), 23, center=True)
    c.text('按逐组原始记录统计，未结构化更正未折算；车辆仅作趣味类比。', (70, note_y+39, 1370, note_y+75), 22, center=True)
    c.panel((48, cta_y, 1392, cta_y+150), '#d4e7dc', 16)
    c.text(brand['cta'].replace('回复', '\n回复'), (90, cta_y+15, 1140, cta_y+135), 32, bold=True, min_size=26, max_lines=2)
    c.sticker(s['footer'], (1160, cta_y-30, 1378, cta_y+175))
    c.text(brand['asset_credit'], (48, cta_y+177, 1392, cta_y+207), 18, '#73736c', center=True, min_size=18)
    count = c.watermarks(brand['watermark'])  # Last compositing pass covers panels and cropped sections.
    out = Path(out)
    if out.suffix.lower() != '.png':
        raise ValueError('输出必须是 .png')
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix='.png', dir=out.parent, delete=False) as f:
        tmp = Path(f.name)
    c.im.save(tmp, format='PNG', optimize=True)
    tmp.replace(out)
    coverage = {'sets': sum(g['sets'] for g in facts['body_groups']),
                'exercises': len({i['name'] for g in facts['body_groups'] if g['part'] != '有氧' for i in g['items']}),
                'body_parts': len(facts['body_groups'])}
    if coverage['sets'] != facts['sets'] or coverage['exercises'] != facts['exercises']:
        raise ValueError('全量动作/组数覆盖检查失败')
    audit = {'renderer_version': VERSION, 'png_sha256': sha(out.read_bytes()), 'size': [W, height],
             'source': data['source'], 'facts': facts, 'copy': copy, 'cta': brand['cta'], 'brand': brand,
             'font_sha256': sha((ASSETS/'fonts'/'NotoSansSC[wght].ttf').read_bytes()),
             'watermark': {'text': brand['watermark'], 'opacity': 25, 'angle': 27, 'count': count},
             'text_layout': c.boxes, 'stickers': c.stickers, 'snapshot': allow_stale,
             'coverage': coverage, 'body_groups': facts['body_groups']}
    write_json(out.with_suffix('.audit.json'), audit)
    return audit


def check(out):
    out = Path(out)
    a = json.loads(out.with_suffix('.audit.json').read_text(encoding='utf-8'))
    brand = normalize_brand(a.get('brand'))
    if a['png_sha256'] != sha(out.read_bytes()) or a['cta'] != brand['cta'] or a['watermark']['text'] != brand['watermark'] or a['watermark']['count'] < 30:
        raise ValueError('PNG/审计/水印不一致，请重新 render')
    with Image.open(out) as im:
        if list(im.size) != a['size'] or im.width != W or not H <= im.height <= 30000:
            raise ValueError('图片尺寸错误')
    if len(a['stickers']) != 7 or not all(0 <= v['box'][0] < v['box'][2] <= W and 0 <= v['box'][1] < v['box'][3] <= a['size'][1] for v in a['text_layout']):
        raise ValueError('表情数量或文字边界异常')
    if a['coverage']['sets'] != a['facts']['sets'] or a['coverage']['exercises'] != a['facts']['exercises']:
        raise ValueError('动作清单覆盖不完整')
    return {'ok': True, 'image': str(out), 'size': a['size'], 'stickers': 7,
            'watermarks': a['watermark']['count'], 'coverage': a['coverage']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('prepare', help='从记录生成事实与可编辑文案 JSON')
    a.add_argument('--records', required=True)
    a.add_argument('--config', help='本地 config.json，读取 brand 配置')
    a.add_argument('--date', required=True)
    a.add_argument('--out', required=True)
    a = sub.add_parser('render', help='用 JSON 和原始表情离线合成 PNG')
    a.add_argument('--input', required=True)
    a.add_argument('--out', required=True)
    a.add_argument('--snapshot', action='store_true', help='明确重现历史快照；跳过当前记录一致性校验')
    a = sub.add_parser('auto', help='完训兜底：已有输入仍新鲜则保留文案，否则重新 prepare，再生成图')
    a.add_argument('--records', required=True)
    a.add_argument('--config', help='本地 config.json，读取 brand 配置')
    a.add_argument('--date', required=True)
    a.add_argument('--dir', required=True)
    a = sub.add_parser('check')
    a.add_argument('--image', required=True)
    sub.add_parser('catalog', help='列出可选表情 ID')
    args = p.parse_args()
    try:
        if args.cmd == 'prepare':
            config = json.loads(Path(args.config).read_text(encoding='utf-8')) if args.config else {}
            value = make_input(args.records, args.date, config.get('brand'))
            write_json(args.out, value)
            print(json.dumps({'input': args.out, 'facts': value['facts'], 'editable': 'copy only'}, ensure_ascii=False))
        elif args.cmd == 'render':
            value = json.loads(Path(args.input).read_text(encoding='utf-8'))
            render(value, args.out, args.snapshot)
            print(json.dumps(check(args.out), ensure_ascii=False))
        elif args.cmd == 'check':
            print(json.dumps(check(args.image), ensure_ascii=False))
        elif args.cmd == 'auto':
            folder = Path(args.dir)
            inp, out = folder / f'{args.date}.json', folder / f'{args.date}.png'
            config = json.loads(Path(args.config).read_text(encoding='utf-8')) if args.config else {}
            value = make_input(args.records, args.date, config.get('brand'))
            if not value['facts']['complete']:
                raise ValueError('尚无有效收工记录，自动完训图暂不生成；中途预览请用 prepare/render')
            if inp.exists():
                previous = json.loads(inp.read_text(encoding='utf-8'))
                if previous.get('source') == value['source'] and previous.get('facts') == value['facts'] and previous.get('brand') == value['brand']:
                    validate_input(previous)
                    value = previous
            write_json(inp, value)
            render(value, out)
            print(json.dumps(check(out), ensure_ascii=False))
        else:
            print(json.dumps(catalog(), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, OSError, TypeError) as e:
        p.exit(1, f'生成失败: {e}\n')


if __name__ == '__main__':
    main()
