#!/usr/bin/env python3
"""Initialize a private workspace and finish a workout with an offline summary image."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

import daily_poster as poster
import runtime

ROOT = Path(__file__).resolve().parents[1]


def workspace(value=None):
    return runtime.workspace(value)


def init(folder):
    folder.mkdir(parents=True, exist_ok=True)
    defaults = {
        'config.json': json.loads((ROOT/'examples/config.example.json').read_text(encoding='utf-8')),
        'exercises.json': json.loads((ROOT/'examples/exercises.example.json').read_text(encoding='utf-8')),
    }
    for name, value in defaults.items():
        path = folder/name
        if not path.exists():
            poster.write_json(path, value)
    (folder/'records.jsonl').touch(exist_ok=True)
    (folder/'posters').mkdir(exist_ok=True)
    return {'workspace': str(folder), 'blog_enabled': runtime.config(folder).get('blog', {}).get('enabled', False)}


def finish(folder, date, *, no_publish=False):
    records, config = folder/'records.jsonl', folder/'config.json'
    if not config.is_file():
        raise ValueError('请先 init 初始化自己的数据目录')
    rows, _ = poster.read_records(records)
    if not poster.aggregate(rows, date)['complete']:
        raise ValueError('尚无有效收工记录，不执行正式收尾')
    # Does not append session_end. The agent records a real end only after user says finished.
    cmd = [sys.executable, str(ROOT/'scripts/daily_poster.py'), 'auto', '--records', str(records),
           '--config', str(config), '--date', date, '--dir', str(folder/'posters')]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    image = folder/'posters'/f'{date}.png'
    image_error = (result.stderr.strip() or f'生成图片失败（退出码{result.returncode}）') if result.returncode else None
    image_check = None
    if not image_error:
        try:
            image_check = poster.check(image)
        except (ValueError, OSError) as e:
            image_error = str(e)
    publication = {'status': 'skipped' if no_publish else 'disabled'}
    try:
        from publish_dashboard import publish
        if not no_publish:
            publication = publish(folder)
    except (ValueError, OSError, subprocess.SubprocessError) as e:
        publication = {'status': 'failed', 'error': str(e)}
    return {'image': None if image_error else str(image), 'image_check': image_check,
            'image_error': image_error, 'blog': publication,
            'delivery': '请将 image 的 PNG 附件发送给当前对话用户，并如实报告 blog 状态；此命令不代发消息。'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    for cmd in ['init', 'finish', 'environment']:
        a = sub.add_parser(cmd)
        a.add_argument('--workspace')
        if cmd == 'finish':
            a.add_argument('--date', default=datetime.now(poster.TZ).date().isoformat())
            a.add_argument('--no-publish', action='store_true', help='仅生成图片，不执行博客Git操作')
    args = p.parse_args()
    try:
        folder = workspace(args.workspace)
        if args.command == 'init':
            result = init(folder)
        elif args.command == 'environment':
            result = runtime.environment(folder)
        else:
            result = finish(folder, args.date, no_publish=args.no_publish)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError) as e:
        p.exit(1, f'操作失败: {e}\n')


if __name__ == '__main__':
    try:
        main()
    finally:
        try:
            from update_skill import start_background
            start_background()
        except Exception:
            pass
