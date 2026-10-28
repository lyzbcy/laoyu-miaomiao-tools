"""YouTube Studio draft UI helpers; no posting API or public-publish action."""
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json,re,shutil,subprocess
from browser import UIError,digest
from prepare_upload import dimensions


def video_identity(url):
    parsed=urlparse(url or '')
    if parsed.hostname not in ('youtube.com','www.youtube.com','studio.youtube.com','youtu.be'):
        return None
    value=(parse_qs(parsed.query).get('udvid') or parse_qs(parsed.query).get('v') or [None])[0]
    match=re.search(r'/(?:shorts|video)/([\w-]{11})(?:/|$)',parsed.path)
    if match:value=match.group(1)
    if parsed.hostname=='youtu.be':value=parsed.path.strip('/')
    return value if isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9_-]{11}',value) else None


def cover_for_layout(base,covers,kind,run_dir):
    ratio='9:16' if kind=='shorts' else '16:9'
    raw=covers.get(ratio)
    if raw:
        path=(Path(base)/raw).resolve()
    elif kind=='shorts' and covers.get('3:4'):
        # Preserve the independently designed portrait poster. Do not crop text
        # or characters to fill Shorts, and do not add an image-library download.
        source=(Path(base)/covers['3:4']).resolve()
        executable=shutil.which('ffmpeg')
        if not executable:raise UIError('Shorts needs a 9:16 cover; provide covers[9:16] or install FFmpeg to pad the 3:4 poster')
        path=Path(run_dir)/('youtube-shorts-cover-'+digest(source)[:12]+'.jpg')
        if not path.is_file():
            path.parent.mkdir(parents=True,exist_ok=True)
            result=subprocess.run([executable,'-v','error','-y','-i',str(source),'-vf','scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x101c23','-frames:v','1','-q:v','2',str(path)],capture_output=True,timeout=30)
            if result.returncode:raise UIError('Shorts cover conversion failed: '+result.stderr.decode('utf-8',errors='replace')[:300])
    else:raise UIError('Provide a '+ratio+' cover for this YouTube layout')
    w,h=dimensions(path)
    a,b=map(int,ratio.split(':'))
    if w*b!=h*a:raise UIError('YouTube '+ratio+' cover has a different aspect ratio')
    return {'path':str(path),'ratio':ratio,'sha256':digest(path)}


def check_result(text):
    # Read the current upload dialog only, excluding older videos behind it.
    fragment=text[text.find('版权'):] if '版权' in text else text
    complete=('检查完毕' in fragment or ('版权' in fragment and '未发现任何问题' in fragment))
    pending=any(x in text for x in ['正在检查','正在处理','即将开始处理','检查中','处理中'])
    return {'status':'processing_pending' if pending or not complete else 'checked','copyright_text':fragment[-3000:],'publicly_published':False}


class YouTubeDraft:
    def __init__(self,publisher):self.p=publisher;self.b=publisher.b

    def context(self):
        result=self.b.js(r'''(()=>{const root=document.querySelector('ytcp-uploads-dialog');const area=root||document;const text=area.innerText||'';const links=[...area.querySelectorAll('a[href]')].map(e=>e.href);const videoUrl=links.find(x=>/^https:\/\/(?:www\.)?youtube.com\/(?:shorts\/|watch\?)/.test(x)||/^https:\/\/youtu.be\//.test(x))||null;const thumb=area.querySelector('ytcp-thumbnail-uploader');const title=area.querySelector('[contenteditable=true][aria-required=true]')?.innerText;const start=text.indexOf('AI 使用情况');const end=start>=0?text.indexOf('联合创作',start):-1;return JSON.stringify({url:location.href,draft_dialog:!!root,title,video_url:videoUrl,kind:videoUrl?.includes('/shorts/')||thumb?.hasAttribute('vertical')?'shorts':videoUrl?'video':null,saved_private:text.includes('已保存为私享视频'),saving:text.includes('正在保存'),ai_question:start>=0?text.slice(start,end>start?end:start+1200):null,text})})()''')
        actual=video_identity(result.get('video_url')) or video_identity(result.get('url'))
        if actual:result['video_id']=actual
        return result

    def remember(self,context):
        if context.get('title') and context['title'].strip()!=self.p.item['title'].strip():
            owned_default=(self.p.j.get('upload_attempted') and not self.p.j['steps'].get('text') and context['title'].strip()==self.p.local(self.p.m['video']).stem)
            if not owned_default:raise UIError('YouTube editor belongs to another title')
        old=self.p.j.get('youtube_video_id')
        if old and context.get('video_id') and old!=context['video_id']:raise UIError('YouTube draft ID differs; do not overwrite it')
        for source,dest in [('kind','youtube_kind'),('video_id','youtube_video_id'),('video_url','youtube_video_url'),('ai_question','youtube_ai_question')]:
            if context.get(source):self.p.j[dest]=context[source]
        if video_identity(context.get('url')) and 'udvid=' in context['url']:
            self.p.j['saved_edit_url']=context['url'] # Observed URL, never invented.
        self.p.persist()
        return context

    def ensure_advanced(self):
        current=self.context()
        if not current.get('draft_dialog'):
            raise UIError('YouTube is not showing an upload draft; inspect whether the user already submitted it')
        if not self.p.shown('input[aria-label="标签"]'):
            self.b.semantic('button','显示高级设置')
            self.b.wait(lambda:self.p.shown('input[aria-label="标签"]'),timeout=10)
        return self.remember(self.context())

    def inspect(self):
        context=self.ensure_advanced()
        self.p.evidence('youtube-context')
        return {k:v for k,v in context.items() if k!='text'}

    def covers(self):
        context=self.remember(self.context())
        kind=context.get('kind') or self.p.j.get('youtube_kind')
        if not kind:raise UIError('YouTube has not exposed the video/Shorts layout; inspect processing before choosing a cover')
        selected=cover_for_layout(self.p.path.parent,self.p.m['covers'],kind,self.p.root)
        previous=self.p.j.get('youtube_cover')
        if previous and previous['sha256']==selected['sha256']:
            return {'status':'already_set','cover':selected,'visual_review':self.p.j.get('cover_visual_review','pending')}
        # Persist before changing a real cover input. A timeout must not trigger
        # another selection of the video or of an uncertain cover.
        if self.p.j.get('youtube_cover_attempted'):raise UIError('YouTube cover was already attempted; inspect its actual preview before replacing it')
        self.p.j['youtube_cover_attempted']=selected;self.p.persist()
        before=self.thumbnail_state()
        self.b.upload(self.p.cfg['cover_input'],selected['path'])
        def changed():
            current=self.thumbnail_state()
            return current if current and current!=before and all(i['ready'] and i['w'] for i in current) else None
        self.b.wait(changed,timeout=10)
        self.b.js("document.querySelector('ytcp-thumbnail-uploader').scrollIntoView({block:'center',behavior:'instant'});true")
        self.p.j['youtube_cover']=selected
        self.p.evidence('cover-'+selected['ratio'].replace(':','x'))
        return {'status':'set','cover':selected,'visual_review':'pending'}

    def thumbnail_state(self):
        return self.b.js("JSON.stringify([...document.querySelectorAll('ytcp-thumbnail-uploader img')].map(e=>{const s=e.currentSrc||e.src;let h=0;for(let i=0;i<s.length;i++)h=(h*31+s.charCodeAt(i))|0;return {source_hash:h,w:e.naturalWidth,h:e.naturalHeight,ready:e.complete}}))")

    def checks(self):
        self.b.semantic('tab','检查')
        self.b.wait(lambda:'版权' in self.context()['text'],timeout=10)
        result=check_result(self.context()['text'])
        self.p.j['youtube_checks']=result;self.p.persist()
        self.p.evidence('copyright-check')
        self.b.semantic('tab','详细信息')
        self.b.wait(lambda:self.p.shown(self.p.cfg['title']),timeout=10)
        if result['status']=='processing_pending':result['retry_after_seconds']=30
        return result

    def save(self):
        def ready():
            c=self.context()
            return c if c.get('saved_private') and not c.get('saving') else None
        context=self.b.wait(ready,timeout=25)
        self.remember(context);self.p.evidence('private-autosaved')
        self.b.semantic('button','关闭',scope='ytcp-uploads-dialog',video_id=self.p.j.get('youtube_video_id'))
        self.b.wait(lambda:not self.p.shown(self.p.cfg['title']),timeout=10)
        current=self.b.state()
        self.p.j['youtube_content_url']=current['url'];self.p.persist()
        return {'status':'private_autosaved','closed':True,'kind':self.p.j.get('youtube_kind')}

    def reopen(self):
        if self.p.shown(self.p.cfg['title']):
            context=self.context()
            if not context.get('draft_dialog'):raise UIError('YouTube is showing an existing video details page, not an upload draft. Inspect publication state; do not re-upload.')
            self.remember(context)
            return
        url=self.p.j.get('saved_edit_url') or self.p.item.get('edit_url')
        expected=self.p.j.get('youtube_video_id')
        if url and expected and video_identity(url)!=expected:raise UIError('Saved YouTube edit URL points at another video')
        if url:
            self.b.send('navigate',{'url':url})
        else:
            # The general Content entry opens the regular-video list. Select
            # the observed matching tab before looking for a Shorts draft.
            desired='Shorts' if self.p.j.get('youtube_kind')=='shorts' else '视频'
            location=self.b.state()['url']
            route='/videos/short' if desired=='Shorts' else '/videos/upload'
            if route not in location:
                if '/videos/' not in location:self.b.semantic('menuitem','内容')
                def select_tab():
                    # During a SPA transition an old DOM tab may precede its AX ref.
                    if route in self.b.state()['url']:return True
                    try:self.b.semantic('tab',desired)
                    except UIError as e:
                        if 'Ambiguous/missing semantic target' in str(e):return False
                        raise
                    return True
                self.b.wait(select_tab,timeout=20)
            self.b.wait(lambda:route in self.b.state()['url'],timeout=20)
            # Titles can be text nodes with no aria-label/href. Match the row's
            # rendered title and its actual Edit draft button, not an old anchor.
            def row_ready():
                return self.b.js(r'''(()=>{const title=TITLE;const expected=EXPECTED;for(const e of document.querySelectorAll('[data-publish-draft]'))e.removeAttribute('data-publish-draft');const rows=[...document.querySelectorAll('ytcp-video-row')].filter(e=>e.innerText.split('\n').some(t=>t.trim()===title)&&e.querySelector('button[aria-label="编辑草稿"]')&&(!expected||[...e.querySelectorAll('a[href]')].some(a=>a.href.match(/\/video\/([A-Za-z0-9_-]{11})(?:\/|$)/)?.[1]===expected)));if(rows.length>1)throw Error('Matching YouTube draft not unique');if(!rows.length)return false;rows[0].setAttribute('data-publish-draft','active');return true})()'''.replace('TITLE',json.dumps(self.p.item['title'])).replace('EXPECTED',json.dumps(expected)))
            self.b.wait(row_ready,timeout=25)
            button='ytcp-video-row[data-publish-draft=active] button[aria-label="编辑草稿"]'
            self.b.send('click',{'selector':button})
        def editor_ready():
            context=self.context()
            if re.search(r'/video/[A-Za-z0-9_-]{11}/edit',context.get('url','')) and not context.get('draft_dialog'):
                raise UIError('YouTube opened an existing video details page, not a draft. Inspect actual publication state; do not re-upload.')
            return self.p.shown(self.p.cfg['title'])
        self.b.wait(editor_ready,timeout=15)
        self.remember(self.context())

    def verify_settings(self):
        context=self.remember(self.ensure_advanced())
        if not context.get('draft_dialog') or not context.get('saved_private'):raise UIError('YouTube is not showing the saved private draft; inspect actual publication state')
        values=self.b.js("JSON.stringify([...document.querySelectorAll('ytcp-text-dropdown-trigger')].map(e=>e.innerText))")
        language={'zh-Hans':'中文（简体）','zh-Hant':'中文（繁体）','en':'英语'}.get(self.p.item.get('language'),self.p.item.get('language'))
        if language and not any(t.startswith('视频语言') and language in t for t in values):raise UIError('Saved YouTube language differs')
        category=self.p.item.get('category')
        if category:
            actual=self.b.js('document.querySelector('+json.dumps(self.p.cfg['category_input'])+').innerText.trim()')
            if actual!=category:raise UIError('Saved YouTube category differs')
        return context
