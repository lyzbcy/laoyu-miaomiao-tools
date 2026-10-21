"""Small, pure gates shared by browser execution and offline evidence replay."""
import hashlib,json,re

def normalized(value,platform=None):
    value=(value or '').replace('\u200b','')
    if platform=='douyin':
        # Douyin serializes paragraph separators as a leading *, observed on reopen.
        value=re.sub(r'(^|\n)\*',r'\1',value)
    return ' '.join(value.split())

def light(stage,passed=False,pending=False,reason='',**proof):
    return dict(stage=stage,light='green' if passed else 'yellow' if pending else 'red',reason=reason,proof=proof)

def publication_signal(platform,state,expected_title,owned_attempt=False,video_id=None):
    """Success in another row / a hidden upload dialog must never prove publication."""
    text=state.get('text','');url=state.get('url','')
    if platform=='youtube':
        published=state.get('published_dialog_text','')
        if expected_title in published and '发布于' in published and (not video_id or video_id in published):
            return light('submit',True,status='published',video_id=video_id)
        row=state.get('matching_row_text','')
        if expected_title in row and '公开' in row and '草稿' not in row and (not video_id or state.get('matching_row_video_id')==video_id):
            return light('submit',True,status='public',video_id=video_id)
    elif platform=='douyin' and owned_attempt and '发布成功' in text and '/content/manage' in url:
        return light('submit',True,status='submitted')
    elif platform=='bilibili' and owned_attempt and '稿件投递成功' in text:
        return light('submit',True,status='submitted')
    elif platform=='xiaohongshu' and owned_attempt and '/publish/success' in url and '发布成功' in text:
        return light('submit',True,status='submitted')
    if state.get('error') or any(t in text for t in ['发布失败','投稿失败','未通过验证']):
        return light('submit',reason='platform_rejected',message=state.get('error'))
    return light('submit',pending=True,reason='no_bound_success_marker')

def review_fingerprint(manifest,platform,cover_hashes):
    record={'video_sha256':manifest.get('video_sha256'),'platform':platform,'content':manifest['platforms'][platform],'covers':cover_hashes}
    return hashlib.sha256(json.dumps(record,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def authorize(receipt,platform,fingerprint):
    if not isinstance(receipt,dict) or receipt.get('approved') is not True:
        raise ValueError('Explicit publication authorization receipt required')
    item=receipt.get('platforms',{}).get(platform,{})
    if item.get('review_fingerprint')!=fingerprint or item.get('visibility')!='public':
        raise ValueError('Authorization does not match this platform/content/cover/video')
    if platform=='wechat_channels' and item.get('confirmed_this_video') is not True:
        raise ValueError('WeChat Channels requires separate confirmation for this exact video')
    if platform=='wechat_official' and item.get('mass_send') is True and item.get('mass_send_confirmed') is not True:
        raise ValueError('Official Account mass send requires separate explicit authorization')
    return light('authorization',True,platform=platform)

def activity_plan(topics,activity_topics=None,blocked=()):
    explicit=activity_topics or []
    if isinstance(explicit,str):explicit=[explicit]
    if len(explicit)>1:raise ValueError('Bilibili allows at most one activity topic per video')
    blocked=set(blocked)
    candidates=explicit or [t for t in topics if t in blocked][:1]
    selected=candidates[0] if candidates else None
    return {'ordinary':[t for t in topics if t not in blocked and t!=selected],
            'activity':selected,'omitted':[t for t in topics if t in blocked and t!=selected]}
