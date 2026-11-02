#!/usr/bin/env python3
"""Optional publisher: only explicit local config enables publication to a user's own repo."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from contextvars import ContextVar
import runtime

import daily_poster as poster

ROOT = Path(__file__).resolve().parents[1]
GIT_OPTIONS = ContextVar('fitness_git_options', default=())


def git(repo, *args, check=True):
    r = subprocess.run(['git', '-C', str(repo), *GIT_OPTIONS.get(), *args], capture_output=True, text=True, encoding='utf-8', timeout=90)
    if check and r.returncode:
        # Do not print raw git output: remote URLs may contain private credentials.
        raise ValueError('Git操作失败：'+args[0]+'；请在自己的仓库核对状态与认证，未修改全局配置或远端地址')
    return r.stdout.strip()


def output_path(repo, rel):
    if not isinstance(rel, str) or '\\' in rel:
        raise ValueError('博客产物路径应是仓库内的POSIX相对路径')
    parts = PurePosixPath(rel)
    if parts.is_absolute() or '..' in parts.parts or not parts.parts or any(p.lower() == '.git' for p in parts.parts):
        raise ValueError('博客产物路径不能越界或覆盖.git')
    p = repo.joinpath(*parts.parts)
    if not p.resolve().is_relative_to(repo.resolve()):
        raise ValueError('博客产物路径通过符号链接越界')
    return p


def export_data(folder, config=None):
    config = runtime.config(folder) if config is None else config
    schema = config.get("blog", {}).get("schema", "days-v1")
    if schema == "jekyll-v1":
        from dashboard_data import export_jekyll
        return export_jekyll(folder, config)
    if schema != "days-v1":
        raise ValueError("未知博客数据schema")
    rows, _ = poster.read_records(folder/'records.jsonl')
    today = datetime.now(poster.TZ).date().isoformat()
    dates = sorted({r.get('date') for r in rows if r.get('action') in ['set', 'cardio'] and r.get('date', '') <= today})
    days = []
    for date in dates:
        facts = poster.aggregate(rows, date)
        days.append({k: facts[k] for k in ['date', 'today_kg', 'sets', 'exercises', 'reps', 'day_label', 'duration_minutes', 'timing_basis', 'complete']})
    return {'schema_version': 1, 'days': days, 'volume_basis': '已记录重量×次数；自重/未知负重及未结构化更正不折算'}


def publish(folder, *, dry_run=False):
    config = runtime.config(folder)
    cfg = config.get('blog', {})
    options = ('-c', 'url.ssh://git@github.com/.insteadOf=git@github.com:') if cfg.get('github_ssh') is True else ()
    token = GIT_OPTIONS.set(options)
    try:
        return _publish(folder, config, dry_run=dry_run)
    finally:
        GIT_OPTIONS.reset(token)


def _publish(folder, config, *, dry_run=False):
    cfg = config.get('blog', {})
    if cfg.get('enabled') is not True:
        return {'status': 'disabled'}
    repo = Path(cfg.get('repo') or '').expanduser().resolve()
    if not cfg.get('repo') or not (repo/'.git').exists():
        raise ValueError('启用博客需要指定自己的Git仓库绝对路径')
    remote, branch = cfg.get('remote', 'origin'), cfg.get('branch', 'main')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', remote) or not re.fullmatch(r'[A-Za-z0-9_./-]+', branch) or branch.startswith('-') or '..' in branch:
        raise ValueError('remote/branch格式无效')
    if git(repo, 'branch', '--show-current') != branch:
        raise ValueError('仓库当前分支与配置不符；未切换或覆盖分支')
    # A clean index is required; do not include or disturb another task's staged changes.
    if git(repo, 'diff', '--cached', '--name-only'):
        raise ValueError('仓库已有暂存改动，请先自行处理；没有替你提交')
    state_path = folder/'publish-state.json'
    state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    rel = cfg.get('data_path', 'fitness/fitness.json')
    data = output_path(repo, rel)
    identity = {'repo': str(repo), 'remote': remote, 'branch': branch, 'data_path': rel,
                'remote_sha256': hashlib.sha256(git(repo, 'config', '--get', 'remote.'+remote+'.url').encode()).hexdigest()}
    head = git(repo, 'rev-parse', 'HEAD')
    pending = state.get('pending')
    if pending:
        if pending.get('identity') != identity or pending.get('commit') != head:
            raise ValueError('上次推送未完成且仓库状态已变化，请先人工核对；不盲目重推')
        if dry_run:
            return {'status': 'ready_to_retry', 'commit': head}
        git(repo, 'push', remote, 'HEAD:refs/heads/'+branch)
        poster.write_json(state_path, {'last_pushed': head})
        return {'status': 'pushed', 'commit': head, 'deployment': 'unverified', 'retry': True}
    remote_tip = git(repo, 'ls-remote', remote, 'refs/heads/'+branch).split()
    if not remote_tip or remote_tip[0] != head:
        raise ValueError('本地分支与远端未对齐，请先自行同步；不推送夹带其他本地提交的历史')
    # Do not overwrite user modifications in the configured generated file.
    if git(repo, 'status', '--porcelain', '--', rel):
        raise ValueError('博客目标文件已有本地改动，未覆盖')
    payload = json.dumps(export_data(folder, config), ensure_ascii=False, indent=2)+'\n'
    if data.is_file() and data.read_text(encoding='utf-8') == payload:
        return {'status': 'unchanged'}
    if dry_run:
        return {'status': 'ready', 'schema': cfg.get('schema', 'days-v1'), 'data_path': rel,
                'payload_sha256': hashlib.sha256(payload.encode()).hexdigest(), 'bytes': len(payload.encode())}
    data.parent.mkdir(parents=True, exist_ok=True)
    poster.write_json(data, json.loads(payload))
    # Exact path and --only ensure unrelated content never enters this commit.
    git(repo, 'add', '--', rel)
    git(repo, 'commit', '--only', '-m', 'Update workout dashboard data', '--', rel)
    poster.write_json(state_path, {'pending': {'identity': identity, 'commit': git(repo, 'rev-parse', 'HEAD')}})
    git(repo, 'push', remote, 'HEAD:refs/heads/'+branch)
    poster.write_json(state_path, {'last_pushed': git(repo, 'rev-parse', 'HEAD')})
    return {'status': 'pushed', 'commit': git(repo, 'rev-parse', 'HEAD'), 'deployment': 'unverified', 'data_path': rel}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace')
    p.add_argument('--dry-run', action='store_true', help='只读检查实际仓库和生成数据，不写文件或提交推送')
    a = p.parse_args()
    try:
        print(json.dumps(publish(runtime.workspace(a.workspace), dry_run=a.dry_run), ensure_ascii=False))
    except (ValueError, OSError, subprocess.SubprocessError) as e:
        p.exit(1, f'博客更新失败: {e}\n')


if __name__ == '__main__':
    main()
