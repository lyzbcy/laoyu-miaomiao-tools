"""Reusable UI steps for experimentally supported X/Channels/Official Account.

No account, project, tab or credential is bundled. Plan and journal stay private.
"""
import argparse, hashlib, json, time
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from browser import Browser, UIError


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def fingerprint(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read_state(path, plan):
    state = json.loads(Path(path).read_text(encoding='utf-8')) if Path(path).exists() else {}
    if state.get('plan_sha256', fingerprint(plan)) != fingerprint(plan):
        raise UIError('Plan changed: use a new journal; never reuse old submission authorization')
    return state


def mutation(path, plan, step, callback):
    state = read_state(path, plan)
    if state.get('published') or state.get(step + '_attempted'):
        raise UIError('Already attempted/published: query current object; do not repeat')
    state.update(plan_sha256=fingerprint(plan))
    state[step + '_attempted'] = True
    state[step + '_at'] = time.time()
    save(path, state)  # Persist BEFORE external mutation, including on callback failure.
    result = callback()
    state[step + '_result'] = result
    save(path, state)
    return result


def source(plan):
    p = Path(plan['video'])
    if hashlib.sha256(p.read_bytes()).hexdigest() != plan['video_sha256']:
        raise UIError('Video fingerprint changed')
    return str(p.resolve())


def x_inspect(b):
    return b.js("""(()=>{const d=[...document.querySelectorAll('[role=dialog]')].at(-1);
    if(!d)throw Error('Composer dialog missing');return JSON.stringify({
    text:d.querySelector('[role=textbox]')?.innerText,body:d.innerText,
    status:[...d.querySelectorAll('[role=status]')].map(x=>x.innerText),
    video:!!d.querySelector('video'),fileInput:!!d.querySelector('input[data-testid=fileInput]')})})()""")


def x_prepare(b, plan, journal):
    video = source(plan)
    b.wait(lambda: x_inspect(b).get('fileInput'), timeout=20)
    current = x_inspect(b)
    if current['video'] or (current.get('text') or '').strip():
        raise UIError('Composer is not empty: inspect existing object instead')
    mutation(journal, plan, 'upload', lambda: b.send('upload', {
        'selector': '[role=dialog] input[data-testid=fileInput]', 'files': [video]}))
    b.js("document.querySelector('[role=dialog] [role=textbox]').focus()")
    b.insert(plan['text'])
    return {'status': 'upload_selected', 'next': 'wait Ready, set and verify native AI disclosure; x-submit'}


def x_submit(b, plan, journal):
    source(plan)
    if not plan.get('confirmed_this_video') or plan.get('authorized_sha256') != plan['video_sha256']:
        raise UIError('Explicit authorization bound to this video fingerprint required')
    view = x_inspect(b)
    if ' '.join(view['text'].split()) != ' '.join(plan['text'].split()):
        raise UIError('Current composer copy differs')
    if not view['video'] or not any(Path(plan['video']).name in s and 'Ready' in s for s in view['status']):
        raise UIError('Current video is not Ready')
    if plan.get('ai_disclosure', True) and 'Made with AI' not in view['body']:
        raise UIError('Set native AI disclosure before submission')
    return mutation(journal, plan, 'submission', lambda: b.send('click', {
        'selector': '[role=dialog] [data-testid=tweetButton]'}))


def x_confirm(b, plan, journal):
    rows = b.js("""(()=>JSON.stringify([...document.querySelectorAll('article')].map(e=>({
    text:(()=>{const node=e.querySelector('[data-testid=tweetText]')?.cloneNode(true);if(!node)return null;node.querySelectorAll('img[alt]').forEach(i=>i.replaceWith(i.alt));node.querySelectorAll('br').forEach(i=>i.replaceWith('\\n'));return node.textContent})(),
    links:[...e.querySelectorAll('a[href*="/status/"]')].map(a=>a.href),
    video:!!e.querySelector('video'),ai:e.innerText.includes('Made with AI')}))))()""")
    norm = lambda s: ' '.join((s or '').split())
    candidates = [row for row in rows if norm(row['text']) == norm(plan['text']) and row['video']]
    if len(candidates) != 1:
        raise UIError('Unique public video not found: keep pending; never resubmit')
    row = candidates[0]
    prefix = 'https://x.com/' + plan['account'].lstrip('@') + '/status/'
    urls = [u for u in row['links'] if u.startswith(prefix) and u[len(prefix):].isdigit()]
    if len(set(urls)) != 1 or (plan.get('ai_disclosure', True) and not row['ai']):
        raise UIError('Account/status/AI identity mismatch')
    state = read_state(journal, plan)
    state.update(plan_sha256=fingerprint(plan), published=True, url=urls[0], native_id=urls[0].split('/')[-1])
    save(journal, state)
    return {'status': 'published', 'url': urls[0]}


def shadow_upload(b, plan, journal):
    video = source(plan)
    expression = "document.querySelector('wujie-app').shadowRoot.querySelector('input[type=file][accept^=video]')"
    result = b.cdp('Runtime.evaluate', expression=expression, returnByValue=False)['result']
    if not result.get('objectId'):
        raise UIError('Visible Channels upload input missing')
    node = b.cdp('DOM.describeNode', objectId=result['objectId'])['node']
    if node['nodeName'] != 'INPUT':
        raise UIError('Upload target is not INPUT')
    return mutation(journal, plan, 'upload', lambda: b.cdp('DOM.setFileInputFiles',
        backendNodeId=node['backendNodeId'], files=[video]))


def article_check(b, plan):
    view = b.js("""(()=>{const e=document.querySelector('.rich_media_content');
    if(!e)throw Error('Article editor missing');return JSON.stringify({text:e.innerText,
    videoIds:[...e.querySelectorAll('mp-common-videosnap')].map(x=>x.getAttribute('data-id'))})})()""")
    clean = lambda s: ''.join(s.replace('\u200b', '').split())
    if view['videoIds'] != [plan['native_video_id']] or clean(plan['body']) not in clean(view['text']):
        raise UIError('Body/native video mismatch: do not publish')
    return {'status': 'native_article_verified', 'video_id': view['videoIds'][0], 'mobile_playback_verified': False}


def wechat_confirm(b, plan, journal):
    """Query a known home record and its public article. Never opens a publisher."""
    state = read_state(journal, plan)
    if not state.get('submission_attempted'):
        raise UIError('No recorded submission: do not infer publication from an old article')
    view = b.js("""(()=>{const title=TITLE;return JSON.stringify({
    account_visible:document.body.innerText.includes(ACCOUNT),
    rows:[...document.querySelectorAll('a.weui-desktop-mass-appmsg__title')]
      .filter(e=>e.innerText.trim().replace(/\\s+/g,' ')===title.trim().replace(/\\s+/g,' ')).map(e=>({title:e.innerText.trim(),url:e.href,
        record:e.closest('.publish_hover_content')?.innerText||''}))})})()""".replace('TITLE', json.dumps(plan['title'])).replace('ACCOUNT', json.dumps(plan['account'])))
    if not view.get('account_visible') or len(view.get('rows', [])) != 1:
        raise UIError('Account/current article row not unique; query only')
    row = view['rows'][0]
    lines = [x.strip() for x in row['record'].splitlines()]
    if '已发表' not in lines:
        return {'status': 'under_review' if '审核中' in lines else 'pending', 'published': False, 'next': 'query_only_never_resubmit'}
    url = urlparse(row['url'])
    q = parse_qs(url.query)
    permanent = url.path.startswith('/s/') and len(url.path) > 3 or url.path == '/s' and all(k in q for k in ('__biz', 'mid', 'idx', 'sn'))
    if url.scheme != 'https' or url.netloc != 'mp.weixin.qq.com' or not permanent or 'tempkey' in q:
        raise UIError('Published row has no permanent article URL yet; query only')
    if not (plan.get('native_video_nonce') or plan.get('native_video_id')):
        raise UIError('Current native video identity required')
    b.send('attach_tab', {'tabId': plan['article_tab_id']})
    article = b.js("""JSON.stringify({url:location.href,title:document.querySelector('#activity-name')?.innerText.trim(),
    account:document.querySelector('#js_name')?.innerText.trim(),
    videos:[...document.querySelectorAll('mp-common-videosnap')].map(e=>({id:e.getAttribute('data-id'),nonce:e.getAttribute('data-nonceid')}))})""")
    if article['url'].split('#')[0] != row['url'].split('#')[0] or ' '.join((article.get('title') or '').split()) != ' '.join(plan['title'].split()) or article['account'] != plan['account'] or len(article['videos']) != 1:
        raise UIError('Public article/account/title/video differs')
    video = article['videos'][0]
    if plan.get('native_video_nonce') and video['nonce'] != str(plan['native_video_nonce']):
        raise UIError('Native video nonce differs')
    if plan.get('native_video_id') and video['id'] != plan['native_video_id']:
        raise UIError('Native video component ID differs')
    state.update(plan_sha256=fingerprint(plan), published=True, status='published', url=row['url'], native_id=plan['draft_id'])
    save(journal, state)
    return {'status': 'published', 'url': row['url'], 'native_video_verified': True, 'mobile_playback_verified': False}


def channels_order(b, plan, journal):
    # Start with the real 更改排序 dialog already open; no framework state mutation.
    code = """(()=>{const r=document.querySelector('wujie-app').shadowRoot;
    return JSON.stringify([...r.querySelectorAll('.collection-order-draggable-list .drag-feed')].map(e=>{
    const h=e.querySelector('.drag-icon-wrap').getBoundingClientRect();return {text:e.innerText,x:h.x+h.width/2,y:h.y+h.height/2}}))})()"""
    rows = b.js(code)
    labels = plan['episode_labels']
    if len(rows) != len(labels) or any(sum(label in row['text'] for row in rows) != 1 for label in labels):
        raise UIError('Collection episode identity mismatch')
    for target, label in enumerate(labels):
        rows = b.js(code)
        start = next(i for i, row in enumerate(rows) if label in row['text'])
        if start == target:
            continue
        x, y = rows[start]['x'], rows[start]['y']
        end = rows[target]['y'] - 12
        b.cdp('Input.dispatchMouseEvent', type='mouseMoved', x=x, y=y)
        b.cdp('Input.dispatchMouseEvent', type='mousePressed', x=x, y=y, button='left', clickCount=1)
        for i in range(1, 17):
            b.cdp('Input.dispatchMouseEvent', type='mouseMoved', x=x, y=y+(end-y)*i/16, buttons=1)
            time.sleep(.06)
        b.cdp('Input.dispatchMouseEvent', type='mouseReleased', x=x, y=end, button='left', clickCount=1)
        time.sleep(.3)
    rows = b.js(code)
    if not all(label in row['text'] for label, row in zip(labels, rows)):
        raise UIError('Drag did not establish requested order; not saved')
    return mutation(journal, plan, 'order_save', lambda: b.send('click', {'selector': plan['save_order_ref']}))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['x-inspect', 'x-prepare', 'x-submit', 'x-confirm', 'channels-upload', 'channels-order', 'article-check', 'wechat-confirm'])
    p.add_argument('--plan', required=True)
    p.add_argument('--journal', required=True)
    args = p.parse_args()
    plan = json.loads(Path(args.plan).read_text(encoding='utf-8'))
    read_state(args.journal, plan)
    b = Browser(plan['session'])
    b.send('attach_tab', {'tabId': plan['tab_id']})
    b.focus()
    try:
        fn = {'x-prepare': x_prepare, 'x-submit': x_submit, 'x-confirm': x_confirm, 'channels-upload': shadow_upload, 'channels-order': channels_order, 'wechat-confirm': wechat_confirm}
        result = fn[args.action](b, plan, args.journal) if args.action in fn else x_inspect(b) if args.action == 'x-inspect' else article_check(b, plan)
        print(json.dumps(result, ensure_ascii=False))
    finally:
        b.focus(False)


if __name__ == '__main__':
    main()
