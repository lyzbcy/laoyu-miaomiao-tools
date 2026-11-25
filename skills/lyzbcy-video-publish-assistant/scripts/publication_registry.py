"""Export confirmed publication identities for a separate analytics collector."""
import datetime
import json
from pathlib import Path


def record(root, manifest, platform, gate, journal):
    status=gate.get('proof',{}).get('status')
    if gate.get('light')!='green' or status not in ('submitted','published','public'):
        return None
    content_id=manifest.get('content_id') or 'video-'+manifest['video_sha256'][:16]
    item=manifest['platforms'][platform]
    account=item.get('account_label')
    publication_id=item.get('publication_id') or content_id+':'+platform
    proof=gate.get('proof',{})
    native=proof.get('note_id') or proof.get('video_id') or journal.get('youtube_video_id') or journal.get('xiaohongshu_note_id')
    row=dict(id=publication_id,content_id=content_id,platform=platform,account_label=account,
        format='video',native_id=native,url=proof.get('url'),published_at=proof.get('published_at'),
        status='published' if status in ('published','public') else 'submitted',
        collection=item.get('collection'),activity=item.get('activity'),source_title=None)
    path=Path(root)/'publication-registry.json'
    data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schema':1,'contents':[],'publications':[],'snapshots':[]}
    data['contents']=[c for c in data['contents'] if c['id']!=content_id]+[dict(id=content_id,title=manifest.get('content_title') or item['title'],series=manifest.get('series'),cover=None)]
    old=next((p for p in data['publications'] if p['id']==publication_id),None)
    if old:
        if old.get('account_label') and account and old['account_label']!=account:
            raise ValueError('Another account requires an explicit publication_id')
        if old.get('native_id') and native and old['native_id']!=native:
            raise ValueError('Another native post requires an explicit publication_id')
        row['account_label']=account or old.get('account_label')
        # A later weak submission marker cannot erase a confirmed ID or status.
        for key in ('native_id','url','published_at'):
            row[key]=row[key] or old.get(key)
        if old['status']=='published':row['status']='published'
    data['publications']=[p for p in data['publications'] if p['id']!=publication_id]+[row]
    data['updated_at']=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)
    return row
