#!/usr/bin/env python3
"""Prepare drafts; submit only with a separately bound user-authorization receipt."""
from pathlib import Path
import argparse,datetime,json,re,shutil,sys,time
from browser import Browser,UIError,digest
from prepare_upload import check
from youtube import YouTubeDraft
from gates import light,normalized,publication_signal,review_fingerprint,authorize,activity_plan,validate_context,description_matches
from bilibili import BilibiliTopics
from xiaohongshu import apply_topics,confirm_published,RECEIPT_ID

HERE=Path(__file__).resolve().parent
PROFILES=json.loads((HERE/'profiles.json').read_text(encoding='utf-8'))
STEPS=['upload','text','declaration','topics','settings','covers','save','reopen','verify']

def steps_for(platform):
    result=list(STEPS)
    if platform=='youtube':result.insert(result.index('save'),'checks')
    return result

def normal(s):return ' '.join((s or '').replace('\u200b','').split())
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)

class Publisher:
    def __init__(self,manifest,platform,run_dir,session,endpoint,profiles=None):
        self.path=Path(manifest).resolve();self.m=json.loads(self.path.read_text(encoding='utf-8-sig'))
        self.p=platform;self.cfg=dict(PROFILES[platform]);self.cfg.update((profiles or {}).get(platform,{}))
        self.item=self.m['platforms'][platform];self.root=Path(run_dir).resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.b=Browser(session,endpoint);self.file=self.root/(platform+'-state.json')
        self.hash=digest(self.local(self.m['video']))
        if self.m.get('video_sha256') and self.hash!=self.m['video_sha256']:raise UIError('Locked video hash differs')
        self.copy_hash=__import__('hashlib').sha256(json.dumps(self.item,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        self.j=json.loads(self.file.read_text(encoding='utf-8')) if self.file.exists() else {'platform':platform,'session':session,'video_sha256':self.hash,'steps':{}}
        if self.j['session']!=session or self.j['video_sha256']!=self.hash:raise UIError('Run directory belongs to a different session/video; choose another run directory')
        if self.j.get('copy_sha256') not in [None,self.copy_hash]:
            self.j['previous_copy_sha256']=self.j['copy_sha256'];self.j['steps']={k:v for k,v in self.j['steps'].items() if k=='upload'}
        self.j['copy_sha256']=self.copy_hash

    def local(self,s):return (self.path.parent/s).resolve()
    def persist(self):write(self.file,self.j)
    def evidence(self,label):
        detailed=label in ['inspect','verified'] or label.startswith('error-')
        v=self.b.state() if detailed else self.b.signals()
        write(self.root/(self.p+'-'+label+'.json'),v)
        # Green steps log proofs. Pixels are useful only for cover crops and
        # exceptional UI; never screenshot every successful text/settings step.
        if label=='inspect' or label.startswith(('error-','cover-')):
            self.b.screenshot(self.root/(self.p+'-'+label+'.jpg'))
            self.j['screenshots']=self.j.get('screenshots',0)+1
        return v
    def select(self):
        # A task may inspect another tab on the same host. Never pick a draft by hostname alone.
        if self.j.get('tab_id'):
            result=self.b.send('attach_tab',{'tabId':self.j['tab_id']})
        else:
            result=self.b.select(self.cfg['url']);self.j['tab_id']=result['tabId'];self.persist()
        from urllib.parse import urlparse
        if urlparse(result.get('url','')).hostname!=urlparse(self.cfg['url']).hostname:
            raise UIError('Pinned draft tab moved to another host; inspect, do not reuse it')
        return result
    def shown(self,selector):return self.b.js("!![...document.querySelectorAll("+json.dumps(selector)+")].find(e=>e.getClientRects().length)")
    def body(self):return self.b.js('document.body.innerText')
    def one_visible(self,selector):
        # Add an ephemeral DOM locator to an observed UI control, no hidden app state.
        marker='data-video-publish-control'
        self.b.js("(()=>{document.querySelectorAll('["+marker+"]').forEach(e=>e.removeAttribute('"+marker+"'));const es=[...document.querySelectorAll("+json.dumps(selector)+")].filter(e=>e.getClientRects().length);if(es.length!==1)throw Error('Visible control count '+es.length);es[0].setAttribute('"+marker+"','active');return true})()")
        return '['+marker+'=active]'
    def tap(self,text):return self.b.tap(text=text)

    def run(self,step):
        try:
            self.select();self.b.focus()
            if self.j.get('human_takeover') and step not in ['inspect','context','checks','confirm','confirm_published']:
                raise UIError('User owns current edits; read only until explicitly released')
            current=self.b.signals()
            if step not in ['inspect','confirm','confirm_published','submit'] and ('published=true' in current['url'] or current.get('publication_hint')):
                raise UIError('Possible manual publication detected. Inspect matching title/duration; do not create another draft')
            if self.p=='youtube' and step in ['text','declaration','topics','settings','covers','save','checks']:
                if not YouTubeDraft(self).context().get('draft_dialog'):
                    raise UIError('YouTube is not showing an upload draft; inspect whether the user already submitted it')
            result=getattr(self,step)()
            status='pending' if isinstance(result,dict) and (result.get('status')=='processing_pending' or result.get('light')=='yellow') else 'failed' if isinstance(result,dict) and result.get('light')=='red' else 'done'
            self.j['steps'][step]={'status':status,'at':datetime.datetime.now().isoformat(timespec='seconds'),'result':result}
            self.j['gate']=light(step,status=='done',status=='pending',reason=result.get('reason','await_processing') if status=='pending' else 'postcondition_passed' if status=='done' else 'platform_rejected')
            self.j['last_error']=None;self.persist();return result
        except Exception as e:
            self.j['last_error']={'step':step,'error':str(e),'at':datetime.datetime.now().isoformat(timespec='seconds')};self.persist()
            self.j['gate']=light(step,reason=str(e));self.persist()
            try:self.evidence('error-'+step)
            except Exception:pass
            raise
        finally:
            try:self.b.focus(False)
            except UIError:pass # The user may have closed the task tab.

    def inspect(self):return self.evidence('inspect')

    def context(self):
        if self.p!='youtube':raise UIError('The context step is for YouTube Studio')
        return YouTubeDraft(self).inspect()

    def checks(self):
        if self.p!='youtube':raise UIError('The checks step is for YouTube Studio')
        return YouTubeDraft(self).checks()

    def review_covers(self,path):
        if not path or not path.is_file():raise UIError('Supply the actual preview screenshot after visually inspecting it')
        fingerprint=digest(path)
        evidence=self.root/(self.p+'-cover-review-'+fingerprint[:12]+path.suffix.lower())
        if evidence.resolve()!=path.resolve():shutil.copyfile(path,evidence)
        self.j['cover_visual_review']='passed'
        self.j['cover_review_evidence']={'path':str(evidence.resolve()),'sha256':fingerprint}
        self.persist();return self.j['cover_review_evidence']

    def upload(self):
        if self.shown(self.cfg['title']):
            current=self.b.js('(()=>{const e=document.querySelector('+json.dumps(self.cfg['title'])+');return e.value||e.innerText})()')
            stem=self.local(self.m['video']).stem
            if current!=self.item['title'] and normal(current).replace(' ','_')!=normal(stem).replace(' ','_') and not self.j.get('upload_attempted'):
                raise UIError('An existing editor contains another title; do not overwrite an unrelated draft')
            return {'status':'editor_already_open','retransmitted':False}
        if self.j.get('upload_attempted'):raise UIError('An upload was already attempted; inspect progress or reopen the saved draft before any new upload')
        if self.p=='youtube' and not self.b.js("document.querySelector('input[name=Filedata]')!==null"):
            self.b.tap(selector='ytcp-icon-button[aria-label="上传视频"]')
            self.b.wait(lambda:self.b.js("document.querySelector('input[name=Filedata]')!==null"))
        self.b.wait(lambda:self.b.js('document.querySelectorAll('+json.dumps(self.cfg['video_input'])+').length===1'),timeout=15)
        self.j['upload_attempted']=True;self.persist() # Before mutation: an uncertain response must not cause a duplicate.
        self.b.upload(self.cfg['video_input'],self.local(self.m['video']))
        try:self.b.wait(lambda:self.shown(self.cfg['title']),timeout=35)
        except UIError:raise UIError('File selected; upload/editor not yet confirmed. Run inspect, do not re-upload')
        return {'status':'editor_open','completion_requires_page_readback':True}

    def text(self):
        result={}
        for field in ['title','description']:
            selector=self.one_visible(self.cfg['title' if field=='title' else 'editor'])
            result[field]=self.b.edit(selector,self.item[field])
        return result

    def topics(self):
        tags=self.item.get('topics',[]);result=[]
        if self.p=='bilibili':return BilibiliTopics(self).apply()
        if self.p=='xiaohongshu':return apply_topics(self)
        if self.p in ['bilibili','youtube']:
            sel=self.one_visible(self.cfg.get('tag_input','input[aria-label="标签"]'))
            for tag in tags:
                existing=self.b.js("document.querySelector("+json.dumps(sel)+").parentElement.parentElement.innerText")
                if tag in existing.splitlines():result.append({'tag':tag,'existing':True});continue
                self.b.edit(sel,tag);self.b.enter(sel)
                self.b.wait(lambda:tag in [x.strip() for x in self.b.js("document.querySelector("+json.dumps(sel)+").parentElement.parentElement.innerText").splitlines()],timeout=8)
                result.append({'tag':tag,'added':True})
            return result
        editor=self.cfg['editor'];candidate=self.cfg['topic_candidates']
        for tag in tags:
            existing=self.b.js("document.querySelector("+json.dumps(editor)+").innerText")
            if ('#'+tag+'[话题]#') in existing or self.b.js("[...document.querySelectorAll('[data-mention]')].some(e=>e.innerText.trim()==="+json.dumps('#'+tag)+")"):
                result.append({'tag':tag,'existing':True});continue
            self.b.focus();self.b.end(editor);self.b.insert(' #'+tag)
            def find():
                return self.b.js("(()=>{const es=[...document.querySelectorAll("+json.dumps(candidate)+")].filter(e=>e.getClientRects().length&&!e.closest('[contenteditable=true]')&&e.innerText.trim().replace(/^#/,'')==="+json.dumps(tag)+");if(es.length!==1)return null;const e=es[0];e.scrollIntoView({block:'nearest'});const r=e.getBoundingClientRect();return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2})})()")
            r=self.b.wait(find,timeout=12);self.b.point(r['x'],r['y'])
            def linked():
                if self.p=='douyin':return self.b.js("[...document.querySelectorAll('[data-mention]')].some(e=>e.innerText.trim()==="+json.dumps('#'+tag)+")")
                return '#'+tag+'[话题]#' in self.b.js("document.querySelector("+json.dumps(editor)+").innerText")
            self.b.wait(linked,timeout=5);result.append({'tag':tag,'entity_verified':True})
        return result

    def covers(self):
        covers=self.m['covers']
        if self.p=='youtube':
            result=YouTubeDraft(self).covers()
            self.j['cover_visual_review']=result['visual_review']
            return result
        elif self.p=='xiaohongshu':
            if self.shown(self.cfg['cover_entry']):self.b.tap(selector=self.cfg['cover_entry'])
            else:
                self.b.tap(selector='.cover > .default')
                self.b.wait(lambda:'编辑封面' in self.body(),timeout=6);self.tap('编辑封面')
            self.b.wait(lambda:self.b.js("document.querySelector("+json.dumps(self.cfg['cover_input'])+")!==null"))
            before=self.b.cover_state();self.b.fill_cover(self.cfg['cover_input'],self.local(covers['3:4']))
            self.b.wait(lambda:self.b.cover_state()!=before,timeout=12)
            self.tap('裁剪');self.tap('3:4');self.evidence('cover-3x4');self.tap('完成')
        elif self.p=='bilibili':
            if self.shown('.cover .cover-img'):self.b.tap(selector='.cover .cover-img')
            else:self.tap('添加封面')
            self.b.wait(lambda:self.b.js("document.querySelector("+json.dumps(self.cfg['cover_input'])+")!==null"))
            # Turn sync off only when its real checkbox is checked.
            self.b.js("(()=>{const e=[...document.querySelectorAll('label')].find(e=>e.innerText.includes('双比例同步改动'));const c=e?.querySelector('input[type=checkbox]');if(c?.checked)c.click();return c?.checked||false})()")
            for ratio,label in [('4:3','首页推荐封面（4:3）'),('16:9','个人空间封面（16:9）')]:
                self.tap(label);before=self.b.cover_state();self.b.fill_cover(self.cfg['cover_input'],self.local(covers[ratio]))
                self.b.wait(lambda:self.b.cover_state()!=before,timeout=12);self.evidence('cover-'+ratio.replace(':','x'))
            self.tap('完成')
        else:
            es=self.b.js("JSON.stringify([...document.querySelectorAll("+json.dumps(self.cfg['cover_entries'])+")].map(e=>{const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}}))")
            if len(es)!=2:raise UIError('Expected horizontal and portrait cover entries; inspect changed UI')
            self.b.point(es[0]['x'],es[0]['y']);self.b.wait(lambda:'设置横封面' in self.body())
            # The main cover editor's upload input is distinct from AI reference-image inputs.
            for ratio,label in [('4:3','设置横封面'),('3:4','设置竖封面')]:
                # The vertical tab and footer can share text. Prefer the real button.
                self.b.semantic('button',label) # Both ratio switch actions are actual buttons.
                # Both ratio editors may remain mounted. Match the upload area's visible parent,
                # not its input visibility; inputs themselves are intentionally hidden.
                if self.cfg.get('cover_input'):sel=self.cfg['cover_input']
                else:
                    self.b.js('''(()=>{document.querySelectorAll('[data-cover-upload]').forEach(e=>e.removeAttribute('data-cover-upload'));const matches=[...document.querySelectorAll('input[type=file][accept*=image]')].filter(e=>{if(e.classList.contains('semi-upload-hidden-input-replace'))return false;for(let p=e.parentElement,i=0;p&&i<4;p=p.parentElement,i++){if(p.innerText.includes('生成参考图'))return false;if(p.innerText.includes('点击上传文件或拖拽文件到这里')){const r=p.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(p).display!=='none'}}return false});if(matches.length!==1)throw Error('Cover upload target count '+matches.length);matches[0].setAttribute('data-cover-upload','active');return true})()''')
                    sel='input[data-cover-upload=active]'
                before=self.b.cover_state();self.b.fill_cover(sel,self.local(covers[ratio]))
                self.b.wait(lambda:self.b.cover_state()!=before,timeout=12);self.evidence('cover-'+ratio.replace(':','x'))
            self.b.semantic('button','完成')
        self.j['cover_visual_review']='pending';return {'status':'set','visual_review':'pending','instruction':'Inspect platform preview screenshots; record review with --step review-covers --evidence PATH'}

    def declaration(self):
        if self.p=='douyin':
            if self.cfg['declaration'] not in self.body():self.tap('请选择自主声明');self.tap(self.cfg['declaration']);self.tap('确定')
        elif self.p=='bilibili':
            sel=self.cfg['declaration_input']
            if self.b.js('document.querySelector('+json.dumps(sel)+').value')!=self.cfg['declaration']:
                self.b.tap(selector=sel)
                self.b.wait(lambda:self.cfg['declaration'] in self.body(),timeout=8)
                self.tap(self.cfg['declaration'])
                self.b.wait(lambda:self.b.js('document.querySelector('+json.dumps(sel)+').value')==self.cfg['declaration'],timeout=8)
        elif self.p=='xiaohongshu':
            if self.cfg['declaration'] not in self.body():self.tap('添加内容类型声明');self.tap(self.cfg['declaration'])
        else:
            if 'made_for_kids' not in self.item:raise UIError('Set youtube.made_for_kids based on actual intended audience')
            YouTubeDraft(self).ensure_advanced()
            name='VIDEO_MADE_FOR_KIDS_'+('MFK' if self.item['made_for_kids'] else 'NOT_MFK')
            self.b.tap(selector='tp-yt-paper-radio-button[name="'+name+'"]')
            # Wording differs by Studio release. Read the displayed question first; manifest records chosen answer explicitly.
            if not isinstance(self.item.get('ai_disclosure'),bool):raise UIError('Inspect current AI question and explicitly set youtube.ai_disclosure true/false; cartoon animation and realistic alterations are different questions')
            self.b.tap(selector='tp-yt-paper-radio-button[name="VIDEO_HAS_ALTERED_CONTENT_'+('YES' if self.item['ai_disclosure'] else 'NO')+'"]')
            self.b.tap(selector='tp-yt-paper-radio-button[name=VIDEO_PAID_PRODUCT_PLACEMENT_NO]')
        return self.evidence('declaration')

    def settings(self):
        if self.p!='youtube':return {'status':'preserve_existing_settings','instruction':'Inspect category in final readback; select an appropriate leaf in the live UI if required'}
        YouTubeDraft(self).ensure_advanced()
        category=self.item.get('category')
        # Use the category field itself, independent of the account's default.
        if category:
            selector=self.cfg['category_input']
            current=self.b.js("(()=>{const es=[...document.querySelectorAll("+json.dumps(selector)+")];if(es.length!==1)throw Error('Category select ambiguous');return es[0].innerText.trim()})()")
            if current!=category:
                self.b.tap(selector=selector);self.b.wait(lambda:category in self.body());self.tap(category)
                self.b.wait(lambda:self.b.js('document.querySelector('+json.dumps(selector)+').innerText.trim()')==category)
        if self.item.get('language'):
            labels={'zh-Hans':'中文（简体）','zh-Hant':'中文（繁体）','en':'英语'}
            label=labels.get(self.item['language'],self.item['language'])
            current=self.b.js("(()=>{const es=[...document.querySelectorAll('ytcp-text-dropdown-trigger')].filter(e=>e.innerText.startsWith('视频语言'));if(es.length!==1)throw Error('Language select ambiguous');es[0].setAttribute('data-language-target','active');return es[0].innerText})()")
            if label not in current:
                self.b.tap(selector='[data-language-target=active]');self.b.wait(lambda:label in self.body());self.tap(label)
                self.b.wait(lambda:label in self.b.js("document.querySelector('[data-language-target=active]').innerText"))
        return self.evidence('settings')

    def save(self):
        if self.j.get('cover_visual_review')=='pending':raise UIError('Cover preview needs visual review; record it before saving')
        if self.p=='youtube':
            return YouTubeDraft(self).save()
        if self.p=='xiaohongshu':
            self.b.semantic('button','暂存离开') # Current accessible ref targets the actual save button.
        else:self.tap('存草稿' if self.p=='bilibili' else '暂存离开')
        def saved():
            s=self.b.state();return s if (('group=draft' in s['url']) if self.p=='bilibili' else ('继续编辑' in s['text']) if self.p=='douyin' else ('保存成功' in s['text'] or '草稿箱' in s['text'])) else None
        return self.b.wait(saved,timeout=20)

    def reopen(self):
        if 'save' not in self.j['steps']:raise UIError('Save the draft before reopening it')
        if self.p=='youtube':
            YouTubeDraft(self).reopen()
            return self.evidence('reopened')
        if self.p=='douyin':self.tap('继续编辑')
        elif self.p=='bilibili':self.tap(self.item['title'])
        elif self.p=='xiaohongshu':
            self.b.wait(lambda:bool(re.search(r'草稿箱\(\d+\)',self.body())) or self.b.js("document.querySelector('.draft-actions')!==null"),timeout=15)
            if not self.b.js("document.querySelector('.draft-actions')!==null"):
                self.b.tap(text=re.search(r'草稿箱\(\d+\)',self.body()).group())
            code="(()=>{const title="+json.dumps(self.item['title'])+";const es=[...document.querySelectorAll('.draft-actions')].filter(e=>e.parentElement.innerText.includes(title));if(es.length!==1)throw Error('Matching draft not unique');const e=[...es[0].querySelectorAll('.btn')].find(e=>e.innerText.trim()==='编辑');e.click();return true})()"
            self.b.js(code)
        try:self.b.wait(lambda:self.shown(self.cfg['title']),timeout=6)
        except UIError:
            exists=self.b.js('document.querySelector('+json.dumps(self.cfg['title'])+')!==null')
            if not exists:raise
            # Last resort for a loaded dialog whose background rendering is paused.
            self.b.cdp('Page.bringToFront');self.b.wait(lambda:self.shown(self.cfg['title']),timeout=20)
        return self.evidence('reopened')

    def verify(self):
        if 'reopen' not in self.j['steps']:raise UIError('Reopen the saved draft before marking verified')
        s=self.evidence('verified');title_values=[x.get('value') or x.get('text') for x in s['inputs']]
        if self.item['title'] not in title_values:raise UIError('Saved title differs')
        editor=self.b.js('document.querySelector('+json.dumps(self.cfg['editor'])+').innerText')
        if not description_matches(self.item['description'],editor,self.p):raise UIError('Saved description differs')
        if self.p in ['douyin','xiaohongshu']:
            for tag in self.item.get('topics',[]):
                if self.p=='douyin':ok=self.b.js("[...document.querySelectorAll('[data-mention]')].some(e=>e.innerText.trim()==="+json.dumps('#'+tag)+")")
                else:ok='#'+tag+'[话题]#' in editor
                if not ok:raise UIError('Missing linked topic '+tag)
        elif self.p in ['bilibili','youtube']:
            topics=self.j.get('bilibili_actual_topics',self.item.get('topics',[])) if self.p=='bilibili' else self.item.get('topics',[])
            if self.p=='youtube':YouTubeDraft(self).ensure_advanced()
            sel=self.one_visible(self.cfg.get('tag_input','input[aria-label="标签"]'))
            chips=self.b.js('document.querySelector('+json.dumps(sel)+').parentElement.parentElement.innerText')
            for tag in topics:
                if tag not in [x.strip() for x in chips.splitlines()]:raise UIError('Missing saved tag '+tag)
        if self.p!='youtube' and self.cfg['declaration'] not in s['text'] and not any(x.get('value')==self.cfg['declaration'] for x in s['inputs']):raise UIError('AI declaration missing')
        if self.p=='bilibili':BilibiliTopics(self).verify_activity()
        if self.p=='youtube':
            YouTubeDraft(self).verify_settings()
            radios=self.b.js("JSON.stringify([...document.querySelectorAll('tp-yt-paper-radio-button[aria-checked=true]')].map(e=>e.getAttribute('name')))")
            for name in ['VIDEO_MADE_FOR_KIDS_'+('MFK' if self.item['made_for_kids'] else 'NOT_MFK'),'VIDEO_HAS_ALTERED_CONTENT_'+('YES' if self.item['ai_disclosure'] else 'NO')]:
                if name not in radios:raise UIError('Saved declaration missing '+name)
        if self.j.get('cover_visual_review')!='passed':raise UIError('Cover visual review has not been recorded')
        return {'status':'saved_reopened_verified','url':s['url'],'published':False,'review_required':True}

    def open(self):
        from urllib.parse import urlparse
        try:result=self.select()
        except UIError as error:
            if self.j.get('tab_id') or 'no tab matching' not in str(error).lower():raise
            result=self.b.open(self.cfg['url'],'视频发布准备')
            self.j['tab_id']=result['tabId'];self.persist()
        home=self.cfg.get('home_url')
        current=urlparse(result.get('url',''))
        if home and not self.j.get('upload_attempted'):
            known=urlparse(home)
            if (current.hostname,current.path.rstrip('/'))==(known.hostname,known.path.rstrip('/')):
                result=self.b.send('navigate',{'url':self.cfg['url']})
        return result

    def dry_run(self):
        # Deliberately local only: never selects a tab, uploads, clicks, or changes a live draft.
        plan=self.review_plan()
        return {'status':'local_dry_run','platform':self.p,'review_fingerprint':plan['review_fingerprint'],
                'would_submit':False,'browser_verification':'not_performed',
                'next':'confirm_only' if self.j.get('submission_attempted') else 'live_identity_visibility_and_draft_review',
                'identity_markers_configured':bool(self.item.get('expected_account_markers'))}

    def check_context(self,path):
        # A separate current UI observation is required; it is not publication authorization.
        if not path or not path.is_file():raise UIError('Supply the actual account/visibility/copy UI observation')
        observation=json.loads(path.read_text(encoding='utf8'))
        result=validate_context(self.p,self.item,observation,self.m.get('required_description_prefix',''))
        self.j['context_review']={'passed':True,'video_sha256':self.hash,'copy_sha256':self.copy_hash,
             'evidence_sha256':digest(path),'evidence':str(path.resolve()),'tab_id':self.j.get('tab_id'),
             'at':datetime.datetime.now().isoformat(timespec='seconds')}
        self.persist();return result

    def review_plan(self):
        covers={k:digest(self.local(v)) for k,v in self.m['covers'].items()}
        fingerprint=review_fingerprint(dict(self.m,video_sha256=self.hash),self.p,covers)
        return {'platform':self.p,'title':self.item['title'],'review_fingerprint':fingerprint,
                'authorization_required':True,'template':{'approved':False,'platforms':{self.p:{'review_fingerprint':fingerprint,'visibility':'public'}}}}

    def confirm_published(self):
        if self.p!='xiaohongshu':return self.confirm()
        report=confirm_published(self)
        write(self.root/(self.p+'-published.json'),report)
        return report['gate']

    def confirm(self):
        state=self.b.publication_state(self.item['title'])
        result=publication_signal(self.p,state,self.item['title'],self.j.get('submission_attempted',False),self.j.get('youtube_video_id'))
        if self.p=='xiaohongshu' and result.get('proof',{}).get('status')=='submitted':
            note_id=self.b.js(RECEIPT_ID)
            if isinstance(note_id,str) and re.fullmatch(r'[a-fA-F0-9]{24}',note_id):
                self.j['xiaohongshu_note_id']=note_id;self.persist()
        write(self.root/(self.p+'-publication.json'),{'gate':result,'observation':state})
        return result

    def submit(self):
        receipt=getattr(self,'authorization',None)
        authorize(receipt,self.p,self.review_plan()['review_fingerprint'])
        if self.j.get('steps',{}).get('verify',{}).get('status')!='done' or self.j.get('cover_visual_review')!='passed':
            raise UIError('Draft fields and cover review must be green before submission')
        # An uncertain previous click can only be read, never clicked again.
        if self.j.get('submission_attempted'):return self.confirm()
        actual=self.b.js('(()=>{const t=document.querySelector('+json.dumps(self.cfg['title'])+');const d=document.querySelector('+json.dumps(self.cfg['editor'])+');return JSON.stringify({title:t?.value||t?.innerText||null,description:d?.innerText||null})})()')
        if normalized(actual.get('title'))!=normalized(self.item['title']) or not description_matches(self.item['description'],actual.get('description'),self.p):
            raise UIError('Current draft content differs; no publication click')
        prefix=self.m.get('required_description_prefix','')
        if prefix and not (actual.get('description') or '').replace('\u200b','').startswith(prefix):
            raise UIError('Required description prefix differs in actual editor')
        if self.item.get('visibility') not in (None,'public'):raise UIError('Public authorization conflicts with configured visibility')
        if self.item.get('expected_account_markers'):
            context=self.j.get('context_review',{})
            if not context.get('passed') or context.get('video_sha256')!=self.hash or context.get('copy_sha256')!=self.copy_hash:
                raise UIError('Current account/visibility observation must be reviewed before submit')
            age=(datetime.datetime.now()-datetime.datetime.fromisoformat(context['at'])).total_seconds()
            if age<0 or age>3600:raise UIError('Account/visibility observation expired; read the UI again')
            if context.get('tab_id')!=self.j.get('tab_id'):raise UIError('Account observation belongs to another draft tab')
            evidence=Path(context['evidence'])
            if not evidence.is_file() or digest(evidence)!=context['evidence_sha256']:raise UIError('Context evidence changed')
        if self.p=='youtube':
            if self.j.get('youtube_checks',{}).get('status')!='checked':
                return {'status':'processing_pending','light':'yellow','reason':'checks_not_green'}
            self.b.semantic('tab','公开范围')
            selector='tp-yt-paper-radio-button[name=PUBLIC]'
            self.b.wait(lambda:self.shown(selector),timeout=12);self.b.tap(selector=selector)
            self.b.wait(lambda:self.b.js('document.querySelector('+json.dumps(selector)+').getAttribute("aria-checked")')=='true',timeout=8)
        self.j['submission_attempted']=True
        self.j['submission_started_at']=datetime.datetime.now().astimezone().isoformat()
        self.persist()
        final='立即投稿' if self.p=='bilibili' else '发布'
        # Explicit final-click path, accessible only after the bound receipt.
        if self.p=='bilibili':
            target=self.b.target(selector='.submit-actions .submit-add')
            if target['text']!=final or target['disabled']:raise UIError('Final Bilibili control differs')
            self.b.send('click',{'selector':'.submit-actions .submit-add'})
        else:self.b.semantic('button',final,allow_final=True)
        def finished():
            r=self.confirm();return r if r['light']!='yellow' else None
        try:return self.b.wait(finished,timeout=25)
        except UIError:
            return {'status':'processing_pending','light':'yellow','reason':'click_recorded_wait_for_matching_success_do_not_retry'}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('manifest',type=Path);ap.add_argument('--platform',choices=list(PROFILES),required=True);ap.add_argument('--run-dir',type=Path,required=True);ap.add_argument('--session',required=True);ap.add_argument('--endpoint',default='http://127.0.0.1:10086');ap.add_argument('--step',choices=STEPS+['inspect','open','prepare','status','review-covers','context','checks','review-plan','dry-run','check-context','submit','confirm','confirm_published'],default='inspect');ap.add_argument('--profiles',type=Path);ap.add_argument('--evidence',type=Path);ap.add_argument('--authorization',type=Path)
    a=ap.parse_args()
    try:
        preflight=check(a.manifest)
        p=Publisher(a.manifest,a.platform,a.run_dir,a.session,a.endpoint,json.loads(a.profiles.read_text(encoding='utf-8')) if a.profiles else None)
        p.j['video_duration']=preflight.get('media',{}).get('duration');p.persist()
        if a.step=='open':p.b.preflight()
        if a.authorization:p.authorization=json.loads(a.authorization.read_text(encoding='utf-8'))
        if a.step=='open':r=p.open()
        elif a.step=='status':r=p.j
        elif a.step=='review-plan':r=p.review_plan()
        elif a.step=='dry-run':r=p.dry_run()
        elif a.step=='check-context':r=p.check_context(a.evidence)
        elif a.step=='review-covers':
            r=p.review_covers(a.evidence)
        elif a.step=='prepare':
            r={}
            for step in steps_for(p.p):
                if p.j['steps'].get(step,{}).get('status')=='done':continue
                r[step]=p.run(step)
                print(json.dumps(p.j['gate'],ensure_ascii=False),flush=True)
                if p.j['steps'][step]['status']=='pending':r={'next':'Processing; resume same run later, no retransmission','gate':p.j['gate']};break
                if step=='covers':r={'next':'Review actual cover crop once per ratio, then review-covers','gate':light('cover-review',pending=True)};break
            else:r={'status':'saved_reopened_verified','gate':p.j.get('gate')}
        else:
            r=p.run(a.step)
            if a.step not in ['inspect','context','confirm','submit']:r={'step':a.step,'gate':p.j.get('gate')}
        print(json.dumps(r,ensure_ascii=False,indent=2));return 0
    except (UIError,ValueError,OSError,KeyError) as e:
        print(json.dumps(light(a.step,reason=str(e)[:700]),ensure_ascii=False),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
