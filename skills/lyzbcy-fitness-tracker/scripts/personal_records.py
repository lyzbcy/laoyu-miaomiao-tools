"""Comparable, dated strength PRs derived from recorded sets."""
from datetime import date
from decimal import Decimal, InvalidOperation
import re

ALIASES = {
    '双头绳三头下压': '双头绳绳索三头下压',
    '双头绳面拉': '双头绳绳索面拉',
    '哑铃二头弯举': '哑铃弯举',
}
LB_KG = Decimal('0.45359237')
NUMBER = r'(\d+(?:\.\d+)?)'
HAND_LOAD = re.compile(r'(?:左右(?:手)?各|双手各|每(?:只|手)|单(?:边|只|手))\s*' + NUMBER + r'\s*(kg|lb|公斤|磅)?', re.I)
SINGLE_LOAD = re.compile(NUMBER + r'\s*(kg|lb|公斤|磅)\s*单(?:边|只|手)', re.I)


def number(value):
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        return None
    return result if result.is_finite() and result >= 0 else None


def kilograms(value, unit):
    return value * LB_KG if unit.lower() in {'lb', '磅'} else value


def format_number(value):
    return format(value.normalize(), 'f')


def hand_load(row, weight, unit, note):
    """Normalize only documented dumbbell loads; the ledger may store a pair total."""
    scope = row.get('loadScope')
    if scope == 'total':
        return weight / 2, unit, '每手'
    if scope == 'per_hand':
        return weight, unit, '每手'
    if re.search('左手|右手', note) and not re.search('左右|两手|双手', note):
        return weight, unit, '左手' if '左手' in note else '右手'
    match = HAND_LOAD.search(note) or SINGLE_LOAD.search(note)
    if match:
        value = Decimal(match[1])
        load_unit = (match[2] or unit).lower()
        kg = kilograms(value, load_unit)
        raw_kg = kilograms(weight, unit)
        # Older records round a pound conversion to one decimal or a whole kg.
        if min(abs(raw_kg - kg), abs(raw_kg - 2 * kg)) <= Decimal('0.2'):
            return value, 'lb' if load_unit in {'lb', '磅'} else 'kg', '每手'
    if re.search('单边|单只|单手', note) and not match:
        return weight, unit, '每手'
    return None


def candidate(row):
    name = row.get('exercise')
    if not name:
        return None
    reps = number(row.get('reps'))
    if reps is None or reps <= 0:
        return None
    try:
        achieved = date.fromisoformat(row.get('date', '')).isoformat()
    except (TypeError, ValueError):
        return None
    unit = row.get('reportedUnit', 'kg')
    weight = number(row.get('reportedWeight') if unit in {'lb', 'plate'} else row.get('weight'))
    equipment = row.get('equipment') or ''
    if weight is None or unit not in {'kg', 'lb', 'plate'} or (unit == 'plate' and not equipment):
        return None
    if row.get('weightEstimated') and unit != 'plate':
        return None
    note = row.get('note') or ''
    load = kilograms(weight, unit)
    mode = 'plate' if unit == 'plate' else 'load'
    prefix = ''
    if '引体' in name and ('辅助' in name or '辅助' in note):
        if weight == 0 or unit == 'plate':
            return None
        mode, load, prefix = 'assisted', -load, '辅助 '
    elif weight == 0:
        if not any(word in name + note for word in ('自重', '引体', '俯卧撑', '双杠臂屈伸')) or '未知' in note:
            return None
        mode = 'bodyweight'
    elif '哑铃' in name and unit != 'plate':
        hand = hand_load(row, weight, unit, note)
        if hand is None:
            return None
        weight, unit, prefix = hand
        load, mode = kilograms(weight, unit), prefix
        prefix += ' '
    canonical_name = ALIASES.get(name, name)
    if mode == 'bodyweight' and name in {'引体向上', '自重引体向上'}:
        variant = re.search('宽距|窄距|对握|反手|单手|单臂|悬空', note)
        canonical_name = f'自重引体向上（{variant[0]}）' if variant else '自重引体向上'
    suffix = '片' if unit == 'plate' else ' lb' if unit == 'lb' else ' kg'
    label = '自重' if mode == 'bodyweight' else prefix + format_number(weight) + suffix
    return {
        'key': (canonical_name, equipment, mode),
        'date': achieved, 'score': (load, reps),
        'detail': f'{label} × {format_number(reps)}次', 'row': row,
    }


def at_least(a, b):
    return a['score'][0] >= b['score'][0] and a['score'][1] >= b['score'][1]


def better(a, b):
    return at_least(a, b) and a['score'] != b['score']


def preferred_history(frontier, configured):
    # Older config entries may lack a date. Use them only when the actual set
    # supplies one and confirms the same recorded load and reps.
    matching = []
    for item in frontier:
        for record in configured:
            if (number(record.get('weight')), number(record.get('reps'))) != (
                number(item['row'].get('weight')), number(item['row'].get('reps'))
            ):
                continue
            if record.get('date') and record['date'] != item['date']:
                continue
            matching.append(item)
            break
    return sorted(matching or frontier, key=lambda x: x['date'])[0] if matching else max(
        sorted(frontier, key=lambda x: x['date']), key=lambda x: x['score']
    )


def summaries(today_sets, history, report_date, personal_records=None):
    prior = {}
    for row in history:
        if row.get('date', '') >= report_date:
            continue
        if entry := candidate(row):
            prior.setdefault(entry['key'], []).append(entry)

    configured = {}
    for group in (personal_records or {}).values():
        if not isinstance(group, dict):
            continue
        for name, record in group.items():
            if isinstance(record, dict):
                configured.setdefault(ALIASES.get(name, name), []).append(record)

    today = {}
    for row in today_sets:
        today.setdefault(row.get('exercise'), []).append(candidate(row))

    result = {}
    for name, entries in today.items():
        if any(entry is None for entry in entries):
            continue
        keys = {entry['key'] for entry in entries}
        if len(keys) != 1:
            continue
        key = keys.pop()
        previous = prior.get(key, [])
        if not previous:
            continue
        frontier = [a for a in previous if not any(better(b, a) for b in previous)]
        new = [
            a for a in entries
            if not any(at_least(b, a) for b in frontier) and any(better(a, b) for b in frontier)
        ]
        best = max(new, key=lambda x: x['score']) if new else preferred_history(frontier, configured.get(key[0], []))
        result[name] = {'new': bool(new), 'detail': best['detail'], 'date': best['date']}
    return result
