"""Xiaohongshu observed DOM helpers; explicit identity beats popularity."""
import datetime,json,re
from browser import UIError
from gates import light


def choose_topic(candidates,tag,topic_id=None):
    rows=[x for x in candidates if x.get('name','').strip().lstrip('#').strip()==tag]
    if topic_id is not None:rows=[x for x in rows if x.get('id')==topic_id]
    if len(rows)!=1:
        raise UIError('Topic missing or ambiguous; configure topic_ids: '+json.dumps(candidates,ensure_ascii=False))
    return rows[0]


def needs_topic_suffix(text,tag):
    return not text.rstrip().endswith('#'+tag)


def apply_topics(p):
    result=[];b=p.b;editor=p.cfg['editor']
    for tag in p.item.get('topics',[]):
        def linked():return '#'+tag+'[话题]#' in b.js('document.querySelector('+json.dumps(editor)+').innerText')
        if linked():result.append({'tag':tag,'existing':True});continue
        text=b.js('document.querySelector('+json.dumps(editor)+').innerText')
        b.focus();b.end(editor)
        if needs_topic_suffix(text,tag):b.insert(' #'+tag)
        def candidates():return b.js(TOPIC_ROWS.replace('SELECTOR',json.dumps(p.cfg['topic_candidates'])))
        rows=b.wait(candidates,timeout=12)
        row=choose_topic(rows,tag,p.item.get('topic_ids',{}).get(tag))
        # Re-read coordinates and identity immediately before clicking.
        row=choose_topic(candidates(),tag,row.get('id'))
        b.point(row['x'],row['y']);b.wait(linked,timeout=5)
        result.append({'tag':tag,'topic_id':row.get('id'),'entity_verified':True})
    return result


TOPIC_ROWS=r"""(()=>{return JSON.stringify([...document.querySelectorAll(SELECTOR)].filter(e=>e.getClientRects().length&&!e.closest('[contenteditable=true]')).map(e=>{const r=e.getBoundingClientRect();let data={};try{data=JSON.parse(e.closest('[data-impression]')?.getAttribute('data-impression')||'{}')}catch{}return {name:e.innerText,id:data.tagTarget?.value?.tagId||null,x:r.x+r.width/2,y:r.y+r.height/2}}))})()"""


def published_gate(state,title,started,duration,now=None,expected_note_id=None):
    # Minute-precision UI times: no older minute, no future minute, one exact row.
    try:
        actual_start=datetime.datetime.fromisoformat(started)
        start=actual_start.replace(second=0,microsecond=0)
        current=now or datetime.datetime.now().astimezone()
        rows=state.get('rows',[])
        if state.get('active_tab')!='已发布' or len(rows)!=1:raise ValueError()
        row=rows[0];stamp=datetime.datetime.fromisoformat(row.get('published_at','')).replace(tzinfo=start.tzinfo)
        if not (start<=stamp<=current):raise ValueError()
        if row.get('title')!=title or not row.get('note_id') or row.get('channel')!='published':raise ValueError()
        if not re.fullmatch(r'[a-fA-F0-9]{24}',row['note_id']):raise ValueError()
        if not duration or abs(float(row['duration'])-float(duration))>1:raise ValueError()
        if expected_note_id and row['note_id']!=expected_note_id:raise ValueError()
        if stamp==start and not expected_note_id:
            return light('confirm-published',pending=True,reason='minute_precision_requires_bound_note_id')
        return light('confirm-published',True,status='published',note_id=row['note_id'],published_at=row['published_at'])
    except (ValueError,TypeError,KeyError):
        return light('confirm-published',pending=True,reason='no_unique_fresh_published_row')


PUBLISHED_ROWS=r"""(()=>{const title=TITLE;const roots=[...document.querySelectorAll('.note-card')].filter(e=>e.getClientRects().length&&e.querySelector('.note-card__title')?.innerText.trim()===title);return JSON.stringify({active_tab:document.querySelector('.tab-item--active')?.innerText.trim(),rows:roots.map(e=>{let d={};try{d=JSON.parse(e.getAttribute('data-impression')||'{}')}catch{}const t=e.innerText;const duration=t.match(/(?:^|\n)(\d+):(\d{2})(?:\n|$)/);return {title:e.querySelector('.note-card__title').innerText.trim(),note_id:d.noteTarget?.value?.noteId,channel:d.index?.value?.channelTabName,published_at:t.match(/\d{4}-\d{2}-\d{2} \d{2}:\d{2}/)?.[0],duration:duration?Number(duration[1])*60+Number(duration[2]):null}})})})()"""


def confirm_published(p):
    if not p.j.get('submission_attempted') or not p.j.get('submission_started_at'):
        raise UIError('A timestamped owned submission is required; query only, never submit again')
    if '/note-manager' not in p.b.state()['url']:
        p.b.tap(text='笔记管理')
        p.b.wait(lambda:'/note-manager' in p.b.state()['url'],timeout=20)
    # This is a filter, not a publication action. The active state is read back below.
    p.b.tap(text='已发布')
    state=p.b.js(PUBLISHED_ROWS.replace('TITLE',json.dumps(p.item['title'])))
    result=published_gate(state,p.item['title'],p.j['submission_started_at'],p.j.get('video_duration'),expected_note_id=p.j.get('xiaohongshu_note_id'))
    return {'gate':result,'observation':state}


# Read only an actual public link on the current owned submission receipt.
RECEIPT_ID=r"""(()=>{if(location.hostname!=='creator.xiaohongshu.com'||!((location.pathname==='/publish/publish'&&new URL(location.href).searchParams.get('published')==='true')||location.pathname==='/publish/success'))return null;const ids=[...new Set([...document.querySelectorAll('a[href]')].filter(e=>e.getClientRects().length).map(e=>{const u=new URL(e.href);return ['www.xiaohongshu.com','xiaohongshu.com'].includes(u.hostname)?u.pathname.match(/^\/(?:explore|discovery\/item)\/([a-fA-F0-9]{24})(?:\/|$)/)?.[1]:null}).filter(Boolean))];return ids.length===1?ids[0]:null})()"""
