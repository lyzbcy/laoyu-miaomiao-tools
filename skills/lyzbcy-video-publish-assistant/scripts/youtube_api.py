"""Official YouTube resumable PRIVATE upload. No public-publication action."""
import argparse
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE='https://www.googleapis.com'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def trusted(url):
    u=urllib.parse.urlsplit(url)
    if u.scheme!='https' or u.hostname not in ('www.googleapis.com','youtube.googleapis.com') or u.username or u.password or u.port not in (None,443):
        raise ValueError('Untrusted upload session host')
    return url


def http(method,url,headers,data=None):
    trusted(url)
    request=urllib.request.Request(url,data=data,headers=headers,method=method)
    try:
        with urllib.request.build_opener(NoRedirect()).open(request,timeout=90) as r:return r.status,dict(r.headers),r.read()
    except urllib.error.HTTPError as e:
        if e.code==308:return 308,dict(e.headers),b''
        raise RuntimeError('YouTube API HTTP '+str(e.code)+'; reconcile this session before retrying') from None
    except urllib.error.URLError:
        raise RuntimeError('Network interrupted; resume the saved session, do not start another upload') from None


def fingerprint(file,title,channel):
    h=hashlib.sha256()
    with Path(file).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return {'video_sha256':h.hexdigest(),'size':Path(file).stat().st_size,'title':title,'channel_id':channel}


def save(path,state):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(state),encoding='utf-8');os.chmod(tmp,0o600);tmp.replace(path)


def offset(headers,total):
    value=headers.get('Range') or headers.get('range')
    if not value:return 0
    match=re.fullmatch(r'bytes=0-(\d+)',value)
    if not match or int(match[1])>=total:raise ValueError('Invalid acknowledged upload range')
    return int(match[1])+1


def upload(file,title,channel,state_file,token,request=http,chunk_size=32*1024*1024):
    if chunk_size<=0 or chunk_size%(256*1024):raise ValueError('Chunk size must be a multiple of 256KiB')
    expected=fingerprint(file,title,channel)
    if not expected['size']:raise ValueError('Empty video file')
    auth={'Authorization':'Bearer '+token}
    code,_,body=request('GET',BASE+'/youtube/v3/channels?part=id&mine=true',auth)
    if code!=200 or [x['id'] for x in json.loads(body).get('items',[])]!=[channel]:raise ValueError('OAuth account/channel differs')
    path=Path(state_file)
    state=json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
    if state:
        if state.get('identity')!=expected:raise ValueError('Saved session belongs to another file/title/channel')
        if state.get('video_id'):return {'status':'uploaded_private','video_id':state['video_id']}
        if not state.get('session_url'):raise ValueError('Previous session creation result unknown; reconcile manually')
    else:
        state={'identity':expected,'phase':'initializing'}
        path.parent.mkdir(parents=True,exist_ok=True)
        descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(descriptor,'w',encoding='utf-8') as stream:json.dump(state,stream)
        metadata={'snippet':{'title':title,'categoryId':'27'},'status':{'privacyStatus':'private','selfDeclaredMadeForKids':False,'containsSyntheticMedia':True}}
        code,headers,_=request('POST',BASE+'/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status',dict(auth,**{'Content-Type':'application/json; charset=UTF-8','X-Upload-Content-Length':str(expected['size']),'X-Upload-Content-Type':'video/mp4'}),json.dumps(metadata).encode())
        if code!=200:raise ValueError('Session not accepted')
        state['session_url']=trusted(headers.get('Location') or headers.get('location') or '')
        state['phase']='uploading';save(path,state)
    url=trusted(state['session_url']);total=expected['size']
    # Probe first, including after a failed final PUT; never retransmit blindly.
    code,headers,body=request('PUT',url,dict(auth,**{'Content-Length':'0','Content-Range':'bytes */'+str(total)}),b'')
    while code==308:
        start=offset(headers,total)
        with Path(file).open('rb') as stream:stream.seek(start);chunk=stream.read(chunk_size)
        if not chunk:raise ValueError('No bytes remain but server did not return completion')
        code,headers,body=request('PUT',url,dict(auth,**{'Content-Type':'video/mp4','Content-Length':str(len(chunk)),'Content-Range':f'bytes {start}-{start+len(chunk)-1}/{total}'}),chunk)
        if code==308 and offset(headers,total)<=start:raise ValueError('Server made no upload progress; stop and resume later')
    if code not in (200,201):raise ValueError('Upload completion not confirmed')
    video=json.loads(body)
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}',video.get('id','')):raise ValueError('Invalid completion video ID')
    if video.get('status',{}).get('privacyStatus')!='private':raise ValueError('Completion privacy is not confirmed private')
    state.update(video_id=video['id'],phase='uploaded_private');save(path,state)
    return {'status':'uploaded_private','video_id':video['id']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('video');p.add_argument('--title',required=True);p.add_argument('--channel-id',required=True)
    p.add_argument('--state',required=True,help='Private local state, outside public repository')
    p.add_argument('--token-env',default='YOUTUBE_ACCESS_TOKEN');p.add_argument('--execute-private-upload',action='store_true')
    a=p.parse_args();identity=fingerprint(a.video,a.title,a.channel_id);token=os.environ.get(a.token_env)
    if not a.execute_private_upload:print(json.dumps({'mode':'preflight_only','oauth_token_available':bool(token),'identity':identity,'public_publish_supported':False}));return
    if not token:raise ValueError('OAuth access token missing; no network request made')
    print(json.dumps(upload(a.video,a.title,a.channel_id,a.state,token)))


if __name__=='__main__':main()
