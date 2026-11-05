"""Read-only checks of saved article HTML and observed publication evidence."""
import argparse
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urldefrag


def permanent(url):
    p = urlparse(url or '')
    q = parse_qs(p.query)
    return (p.scheme == 'https' and p.netloc == 'mp.weixin.qq.com' and 'tempkey' not in q
            and (p.path.startswith('/s/') and len(p.path) > 3
                 or p.path == '/s' and all(k in q for k in ('__biz', 'mid', 'idx', 'sn'))))


def publication(observed, expected):
    def result(status, reason):
        return {'status': status, 'reason': reason, 'action': 'query_only_never_resubmit',
                'published': status == 'published', 'mobile_playback_verified': False}
    account, title = expected.get('account'), expected.get('title')
    if not account or not title or observed.get('account') != account:
        return result('blocked', 'account_or_expectation_mismatch')
    rows = [r for r in observed.get('rows', []) if r.get('title') == title]
    if len(rows) != 1:
        return result('blocked', 'current_record_not_unique')
    row = rows[0]
    if row.get('status') != '已发表':
        return result('under_review' if row.get('status') == '审核中' else 'pending', 'record_not_published')
    if not permanent(row.get('url')):
        return result('blocked', 'permanent_url_missing')
    article = observed.get('article')
    if not article:
        return result('pending', 'public_article_readback_required')
    if (article.get('title') != title or article.get('account') != account
            or urldefrag(article.get('url', ''))[0] != urldefrag(row['url'])[0]):
        return result('blocked', 'public_article_mismatch')
    checks = [('native_video_nonce', 'nonce'), ('native_video_id', 'id')]
    if any(expected.get(k) for k, _ in checks):
        videos = article.get('videos', [])
        if len(videos) != 1:
            return result('blocked', 'current_video_not_unique')
        for key, field in checks:
            if expected.get(key) and str(videos[0].get(field)) != str(expected[key]):
                return result('blocked', 'current_video_identity_mismatch')
        if expected.get('video_description'):
            norm = lambda s: ' '.join((s or '').split())
            if norm(videos[0].get('description')) != norm(expected['video_description']):
                return result('blocked', 'current_video_description_mismatch')
    report = result('published', 'record_and_public_article_match')
    report.update(url=row['url'], native_video_verified=any(expected.get(k) for k, _ in checks))
    return report


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headings = self.styled = self.tables = self.code = self.videos = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.headings += tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')
        self.styled += bool(attrs.get('style', '').strip())
        self.tables += tag == 'table'
        self.code += tag == 'code'
        self.videos += tag == 'mp-common-videosnap'


def layout(html, min_headings=0, min_styled=0):
    p = ArticleParser()
    p.feed(html)
    errors = []
    if p.headings < min_headings:
        errors.append('heading_structure_missing')
    if p.styled < min_styled:
        errors.append('inline_styles_missing')
    return {'valid': not errors, 'errors': errors, 'headings': p.headings, 'inline_styled': p.styled,
            'tables': p.tables, 'code': p.code, 'native_videos': p.videos,
            'scope': 'Saved HTML structure only; not visual quality, persistence or mobile playback.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('layout');a.add_argument('html', type=Path)
    a.add_argument('--min-headings', type=int, default=0);a.add_argument('--min-styled', type=int, default=0)
    a = sub.add_parser('publication');a.add_argument('observation', type=Path);a.add_argument('--expect', type=Path, required=True)
    args = p.parse_args()
    if args.command == 'layout':
        report = layout(args.html.read_text(encoding='utf-8-sig'), args.min_headings, args.min_styled)
    else:
        read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
        report = publication(read(args.observation), read(args.expect))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get('valid') or report.get('published') else 1


if __name__ == '__main__':
    raise SystemExit(main())
