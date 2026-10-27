#!/usr/bin/env python3
"""Offline duration/cost planning. No network, credential, upload or payment code."""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import subprocess


def number(value, name, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name}: finite number required')
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError(f'{name}: invalid value')
    return float(value)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def file_hash(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('timestamp must include timezone')
    return result.astimezone(timezone.utc)


def measure(path, audio_track=0):
    """Measure the actual to-be-uploaded audio, not the finished video's length."""
    path = Path(path).resolve(strict=True)
    if isinstance(audio_track, bool) or not isinstance(audio_track, int) or audio_track < 0:
        raise ValueError('audio_track must be a nonnegative integer')
    probe = json.loads(subprocess.run(
        ['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)],
        check=True, capture_output=True, text=True, encoding='utf-8').stdout)
    tracks = [s for s in probe['streams'] if s.get('codec_type') == 'audio']
    if audio_track >= len(tracks):
        raise ValueError(f'no selected audio track: {path.name}')
    duration = tracks[audio_track].get('duration') or probe.get('format', {}).get('duration')
    duration = number(float(duration), 'duration_seconds', positive=True)
    return {'path': str(path), 'sha256': file_hash(path), 'duration_seconds': duration,
            'audio_track': audio_track, 'measurement': 'ffprobe', 'size_bytes': path.stat().st_size}


def cache_key(item, request):
    return digest({k: request[k] for k in ('provider', 'model', 'channel', 'options')} |
                  {'sha256': item['sha256'], 'audio_track': item.get('audio_track', 0)})


def valid_cache(entry):
    try:
        return (entry.get('status') == 'success' and Path(entry['result_path']).is_file()
                and file_hash(entry['result_path']) == entry['result_sha256'])
    except (KeyError, OSError, TypeError):
        return False


def scope_matches(value, request):
    return all(value.get(k) == request[k] for k in ('provider', 'model', 'channel'))


def evaluate(request, now=None, measurements_verified=False):
    """Pure planning from a snapshot. CLI remeasures inputs; fixtures are never upload approval."""
    now = now or datetime.now(timezone.utc)
    if request.get('provider') != 'elevenlabs' or request.get('channel') != 'api':
        raise ValueError('only elevenlabs/api planning is supported')
    if request.get('model') not in ('scribe_v1', 'scribe_v2'):
        raise ValueError('unsupported model; review its billing contract first')
    if not isinstance(request.get('options'), dict):
        raise ValueError('explicit options object required')
    attempts = request.get('attempts', 1)
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1:
        raise ValueError('attempts must be an integer >= 1')
    reserve = number(request.get('safety_fraction', .1), 'safety_fraction')
    if reserve > 1:
        raise ValueError('safety_fraction must be <= 1')
    billing = request.get('billing', {})
    quantum = number(billing.get('rounding_seconds', 1), 'rounding_seconds', positive=True)
    minimum = number(billing.get('minimum_seconds_per_file', 0), 'minimum_seconds_per_file')
    cache = {e.get('key'): e for e in request.get('cache', []) if valid_cache(e)}
    seen, rows = set(), []
    inputs = request.get('inputs')
    if not isinstance(inputs, list) or not inputs:
        raise ValueError('at least one measured input required')
    for item in inputs:
        duration = number(item.get('duration_seconds'), 'duration_seconds', positive=True)
        sha = item.get('sha256', '')
        if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError('lowercase SHA256 required')
        track = item.get('audio_track', 0)
        if isinstance(track, bool) or not isinstance(track, int) or track < 0:
            raise ValueError('invalid audio_track')
        if not isinstance(item.get('path'), str) or not item['path']:
            raise ValueError('input path required')
        key = cache_key(item, request)
        disposition = 'cached' if key in cache else ('duplicate' if key in seen else 'planned')
        seen.add(key)
        estimated = 0 if disposition != 'planned' else math.ceil(max(duration, minimum) / quantum) * quantum
        rows.append({'path': item['path'], 'sha256': sha, 'audio_track': track,
                     'duration_seconds': duration, 'cache_key': key,
                     'disposition': disposition, 'estimated_seconds_per_attempt': estimated})
    input_seconds = sum(r['duration_seconds'] for r in rows)
    planned_seconds = sum(r['estimated_seconds_per_attempt'] for r in rows) * attempts
    buffered_seconds = planned_seconds * (1 + reserve)
    balance = request.get('balance') or {}
    reason, available, required, after, unit = 'missing_balance', None, None, None, balance.get('unit')
    max_age = number(request.get('max_snapshot_age_seconds', 900), 'max_snapshot_age_seconds', True)
    try:
        if not scope_matches(balance, request):
            raise ValueError('balance_model_or_channel_mismatch')
        if not balance.get('source') or not balance.get('scope'):
            raise ValueError('balance_provenance_missing')
        age = (now - timestamp(balance['queried_at'])).total_seconds()
        if age < 0 or age > max_age:
            raise ValueError('balance_snapshot_stale_or_future')
        if timestamp(balance['reset_at']) <= now:
            raise ValueError('balance_reset_passed')
        remaining = number(balance['remaining'], 'remaining')
        factor = {'seconds': 1, 'minutes': 1 / 60, 'hours': 1 / 3600}.get(unit)
        if unit == 'credits':
            conversion = balance.get('conversion', {})
            if (not scope_matches(conversion, request) or not conversion.get('source')
                    or conversion.get('options_digest') != digest(request['options'])):
                raise ValueError('credit_conversion_unverified')
            conversion_age = (now - timestamp(conversion['verified_at'])).total_seconds()
            if conversion_age < 0 or conversion_age > max_age:
                raise ValueError('credit_conversion_stale')
            factor = number(conversion['credits_per_second'], 'credits_per_second', True)
        if factor is None:
            raise ValueError('unsupported_balance_unit')
        reserved = 0
        for entry in request.get('reservations', []):
            if entry.get('scope') != balance['scope']:
                continue
            if entry.get('status') in ('reserved', 'uncertain', 'submitted'):
                if entry.get('included_in_snapshot') is True:
                    continue
                if entry.get('included_in_snapshot') is not False or entry.get('unit') != unit:
                    raise ValueError('reservation_unit_or_snapshot_unknown')
                reserved += number(entry['amount'], 'reservation_amount')
        available = max(0, remaining - reserved)
        required = buffered_seconds * factor
        after = available - required
        reason = 'sufficient' if after >= -1e-9 else 'insufficient'
    except (ValueError, KeyError, TypeError) as error:
        reason = str(error)
        available, required, after = None, None, None
    price = request.get('price_reference') or {}
    gross_usd = None
    if (scope_matches(price, request) and price.get('source') and price.get('as_of')
            and price.get('options_digest') == digest(request['options'])):
        gross_usd = buffered_seconds / 3600 * number(price.get('usd_per_hour'), 'usd_per_hour')
    binding = {'provider': request['provider'], 'model': request['model'], 'channel': request['channel'],
               'options': request['options'], 'inputs': rows, 'attempts': attempts,
               'safety_fraction': reserve, 'billing': billing, 'balance': balance,
               'reservations': request.get('reservations', []), 'price_reference': price}
    plan_digest = digest(binding)
    approval = request.get('approval') or {}
    approved = (approval.get('explicit') is True and approval.get('plan_digest') == plan_digest
                and bool(approval.get('reference')))
    if not any(r['disposition'] == 'planned' for r in rows):
        state = 'no_upload_needed'
    elif reason != 'sufficient':
        state = 'blocked_insufficient' if reason == 'insufficient' else 'blocked_unknown_balance'
    elif not measurements_verified:
        state = 'blocked_unverified_measurement'
    else:
        state = 'approved_preflight_only' if approved else 'needs_explicit_confirmation'
    unknown = 'unknown'
    quantity = lambda v: unknown if v is None else f'{v:.4f} {unit}'
    confirmation = (f"拟将 {', '.join(r['path'] for r in rows if r['disposition'] == 'planned')} 的音频上传至 "
                    f"ElevenLabs，用 {request['model']} / API 转写，选项 {canonical(request['options'])}。"
                    f"输入共 {input_seconds / 60:.3f} 分钟；去重/缓存后含 {attempts} 次尝试及 "
                    f"{reserve:.0%} 预留，预计 {buffered_seconds / 60:.3f} 分钟（{buffered_seconds / 3600:.4f} 小时）。"
                    f"当前可核实可用免费余额 {quantity(available)}，预计免费消耗 {quantity(required)}，"
                    f"预计使用后 {quantity(after)}；来源 {balance.get('source', unknown)}，"
                    f"查询 {balance.get('queried_at', unknown)}，重置 {balance.get('reset_at', unknown)}。"
                    f"余额状态 {reason}。付费不允许；不足/未知则保留本地转写。是否批准这批上传？"
                    f"计划指纹 {plan_digest}。本脚本仅预检，不执行上传或付费。")
    return {'schema_version': 1, 'state': state, 'balance_reason': reason, 'inputs': rows,
            'input_seconds': input_seconds, 'estimated_seconds': planned_seconds,
            'buffered_seconds': buffered_seconds, 'unit': unit, 'available_free': available,
            'estimated_free_usage': required, 'estimated_remaining': after,
            'gross_reference_usd': gross_usd, 'price_reference': price,
            'billing_assumptions': {'rounding_seconds': quantum, 'minimum_seconds_per_file': minimum,
                                    'attempts': attempts, 'safety_fraction': reserve},
            'measurements_verified': measurements_verified, 'approval_matches': approved,
            'plan_digest': plan_digest, 'confirmation_text': confirmation,
            'upload_implemented': False, 'upload_allowed': False, 'paid_allowed': False,
            'account_adapter': 'manual_snapshot_only; no live balance query implemented'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    m = commands.add_parser('measure')
    m.add_argument('files', nargs='+')
    m.add_argument('--audio-track', type=int, default=0)
    m.add_argument('--output', required=True)
    p = commands.add_parser('plan')
    p.add_argument('request')
    p.add_argument('--output', required=True)
    args = parser.parse_args()
    if Path(args.output).exists():
        raise FileExistsError('use a new preflight output path')
    if args.command == 'measure':
        result = {'inputs': [measure(path, args.audio_track) for path in args.files]}
    else:
        request = json.loads(Path(args.request).read_text(encoding='utf-8-sig'))
        for item in request['inputs']:
            actual = measure(item['path'], item.get('audio_track', 0))
            if (actual['sha256'] != item['sha256'] or
                    abs(actual['duration_seconds'] - item['duration_seconds']) > .02):
                raise ValueError('input changed since measurement; measure and confirm again')
        result = evaluate(request, measurements_verified=True)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(f"offline preflight written: {args.output}; no upload/payment performed")


if __name__ == '__main__':
    main()
