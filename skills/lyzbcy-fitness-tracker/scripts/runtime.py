"""Local environment layer; never shipped with personal values or updated in place."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_object(path):
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('本地配置必须是JSON对象')
    return value


def merge(base, overlay):
    result = dict(base)
    for key, value in overlay.items():
        result[key] = merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else value
    return result


def workspace(value=None):
    # This locator has only a private data path; user preferences live outside the skill.
    locator = read_object(ROOT/'runtime.local.json') if not value and not os.environ.get('FITNESS_HOME') else {}
    return Path(value or os.environ.get('FITNESS_HOME') or locator.get('workspace') or Path.home()/'.lyzbcy-fitness').expanduser().resolve()


def config(folder, config_path=None):
    folder = Path(folder)
    return merge(read_object(Path(config_path) if config_path else folder/'config.json'), read_object(folder/'runtime.local.json'))


def environment(folder):
    cfg = config(folder)
    guidance = folder/'LOCAL.md'
    return {'workspace': str(folder), 'local_overlay': str(folder/'runtime.local.json'),
            'local_guidance': str(guidance) if guidance.is_file() else None,
            'blog_enabled': cfg.get('blog', {}).get('enabled') is True,
            'blog_schema': cfg.get('blog', {}).get('schema', 'days-v1'),
            'nutrition_dir': cfg.get('nutrition_dir')}
