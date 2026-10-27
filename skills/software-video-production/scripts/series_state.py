"""Prepare a private, evidence-bound previous-episode shot. Does not log in or publish."""
import argparse,base64,hashlib,json,re
from datetime import date,datetime
from pathlib import Path

LABELS={'views':'播放量','likes':'点赞量','favorites':'收藏量','comments':'评论量','followers':'涨粉量'}

def day_number(epoch,episode):
    days=(date.fromisoformat(episode)-date.fromisoformat(epoch)).days+1
    if days<1: raise ValueError('episode precedes first publication')
    return days

def metric_value(raw):
    # Keep rounded displays; never turn a missing field into zero.
    if not isinstance(raw,str): raise ValueError('metric must preserve original display text')
    raw=raw.strip()
    if re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+)',raw): return {'value':int(raw.replace(',','')),'display':raw,'approximate':False}
    m=re.fullmatch(r'(\d+(?:\.\d+)?)(万|亿)',raw)
    if not m: raise ValueError('unsupported metric display')
    return {'value':float(m[1])*(10000 if m[2]=='万' else 100000000),'display':raw,'approximate':True}

def prepare(profile,snapshot,episode_date,base):
    day_number(profile['epochDate'],episode_date)
    if profile.get('timezone')!='Asia/Shanghai': raise ValueError('explicit series timezone required')
    episodes=[x for x in profile['episodes'] if x.get('workflow')=='software-video-production' and x.get('published') is True]
    if not episodes: raise ValueError('no verified previous workflow episode')
    for ep in episodes:
        if datetime.fromisoformat(ep['publishedAt']).utcoffset() is None: raise ValueError('publication timestamp requires timezone')
    previous=max(episodes,key=lambda x:datetime.fromisoformat(x['publishedAt']))
    if snapshot['itemId']!=previous['itemId']: raise ValueError('snapshot is not the latest verified workflow episode')
    expected='https://creator.douyin.com/creator-micro/work-management/work-detail/'+previous['itemId']
    if snapshot['sourceUrl'].split('?')[0]!=expected: raise ValueError('per-work source URL does not match episode')
    stamp=datetime.fromisoformat(snapshot['snapshotAt'].replace('Z','+00:00'))
    if stamp.utcoffset() is None: raise ValueError('snapshot needs timezone')
    if stamp<datetime.fromisoformat(previous['publishedAt']): raise ValueError('snapshot predates publication')
    if snapshot.get('period')!='cumulative' or snapshot.get('approved') is not True: raise ValueError('review cumulative per-work source before prepare')
    cover=(base/snapshot['coverPath']).resolve()
    data=cover.read_bytes()
    if hashlib.sha256(data).hexdigest()!=snapshot['coverSha256']: raise ValueError('cover hash differs')
    if not data.startswith(b'\x89PNG\r\n\x1a\n') or snapshot.get('coverApproved') is not True: raise ValueError('approved PNG cover required')
    metrics={}
    for key,entry in snapshot['metrics'].items():
        if key not in LABELS or entry.get('sourceLabel')!=LABELS[key]: raise ValueError('metric label mismatch: '+key)
        metrics[key]=metric_value(entry['raw'])
    if not metrics: raise ValueError('no per-work metrics')
    return {'id':'previous_episode','recipe':'previous_episode','frames':180,'title':'上期数据','synthetic':False,'visualStyle':profile.get('visualStyle','cupertino'),
        'series':{'enabled':True,'epochDate':profile['epochDate'],'episodeDate':episode_date,'timezone':profile['timezone'],'position':'upper-center'},
        'previous':{'title':previous['title'],'itemId':previous['itemId'],'sourceUrl':snapshot['sourceUrl'],'snapshotAt':snapshot['snapshotAt'],'approved':True,'metrics':metrics},
        'image':'data:image/png;base64,'+base64.b64encode(data).decode(),'privacyApproved':True}

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--profile',type=Path,required=True);a.add_argument('--snapshot',type=Path,required=True);a.add_argument('--episode-date',required=True);a.add_argument('--output',type=Path,required=True)
    args=a.parse_args()
    shot=prepare(json.loads(args.profile.read_text(encoding='utf-8-sig')),json.loads(args.snapshot.read_text(encoding='utf-8-sig')),args.episode_date,args.snapshot.parent)
    if args.output.exists(): raise ValueError('use a new output path')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(shot,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'ok':True,'output':str(args.output),'day':day_number(shot['series']['epochDate'],args.episode_date),'metrics':list(shot['previous']['metrics'])},ensure_ascii=False))

if __name__=='__main__': main()
