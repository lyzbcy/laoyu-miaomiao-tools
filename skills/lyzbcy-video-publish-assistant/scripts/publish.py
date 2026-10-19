#!/usr/bin/env python3
"""Prepare browser video drafts, with resumable checkpoints; never publish."""
from pathlib import Path
import argparse,datetime,json,re,shutil,sys,time
from browser import Browser,UIError,digest
from prepare_upload import check
from youtube import YouTubeDraft

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
        v=self.b.state();write(self.root/(self.p+'-'+label+'.json'),v)
        self.b.screenshot(self.root/(self.p+'-'+label+'.jpg'));return v
    def select(self):self.b.select(self.cfg['url'])
    def shown(self,selector):return self.b.js("!![...document.querySelectorAll("+json.dumps(selector)+")].find(e=>e.getClientRects().length)")
    def body(self):return self.b.js('document.body.innerText')
    def one_visible(self,selector):
        # Add an ephemeral DOM locator to an observed UI control, no hidden app state.
        marker='data-video-publish-control'
        self.b.js("(()=>{document.querySelectorAll('["+marker+"]').forEach(e=>e.removeAttribute('"+marker+"'));const es=[...document.querySelectorAll("+json.dumps(selector)+")].filter(e=>e.getClientRects().length);if(es.length!==1)throw Error('Visible control count '+es.length);es[0].setAttribute('"+marker+"','active');return true})()")
        return '['+marker+'=active]'
    def tap(self,text):return self.b.tap(text=text)

    def run(self,step):
        self.select()
        self.b.focus()
        try:
            current=self.b.state()
            if step!='inspect' and ('published=true' in current['url'] or any(x in current['text'] for x in ['投稿成功','稿件投递成功','发布成功'])):
                raise UIError('Possible manual publication detected. Inspect matching title/duration; do not create another draft')
            if self.p=='youtube' and step in ['text','declaration','topics','settings','covers','save','checks']:
                if not YouTubeDraft(self).context().get('draft_dialog'):
                    raise UIError('YouTube is not showing an upload draft; inspect whether the user already submitted it')
            result=getattr(self,step)()
            status='pending' if isinstance(result,dict) and result.get('status')=='processing_pending' else 'done'
            self.j['steps'][step]={'status':status,'at':datetime.datetime.now().isoformat(timespec='seconds'),'result':result}
            self.j['last_error']=None;self.persist();return result
        except Exception as e:
            self.j['last_error']={'step':step,'error':str(e),'at':datetime.datetime.now().isoformat(timespec='seconds')};self.persist()
            try:self.evidence('error-'+step)
            except Exception:pass
            raise
        finally:self.b.focus(False)

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
        if self.p in ['bilibili','youtube']:
            sel=self.one_visible(self.cfg.get('tag_input','input[aria-label="标签"]'))
            for tag in tags:
                existing=self.b.js("document.querySelector("+json.dumps(sel)+").parentElement.parentElement.innerText")
                if tag in existing.splitlines():result.append({'tag':tag,'existing':True});continue
                self.b.tap(selector=sel);self.b.insert(tag);self.b.key('Enter')
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
            self.b.tap(selector=self.cfg['cover_entry']);self.b.wait(lambda:self.b.js("document.querySelector("+json.dumps(self.cfg['cover_input'])+")!==null"))
            self.b.upload(self.cfg['cover_input'],self.local(covers['3:4']))
            self.tap('裁剪');self.tap('3:4');self.evidence('cover-3x4');self.tap('完成')
        elif self.p=='bilibili':
            self.tap('添加封面');self.b.wait(lambda:self.b.js("document.querySelector("+json.dumps(self.cfg['cover_input'])+")!==null"))
            # Turn sync off only when its real checkbox is checked.
            self.b.js("(()=>{const e=[...document.querySelectorAll('label')].find(e=>e.innerText.includes('双比例同步改动'));const c=e?.querySelector('input[type=checkbox]');if(c?.checked)c.click();return c?.checked||false})()")
            for ratio,label in [('4:3','首页推荐封面（4:3）'),('16:9','个人空间封面（16:9）')]:
                self.tap(label);self.b.upload(self.cfg['cover_input'],self.local(covers[ratio]));time.sleep(.7);self.evidence('cover-'+ratio.replace(':','x'))
            self.tap('完成')
        else:
            es=self.b.js("JSON.stringify([...document.querySelectorAll("+json.dumps(self.cfg['cover_entries'])+")].map(e=>{const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2}}))")
            if len(es)!=2:raise UIError('Expected horizontal and portrait cover entries; inspect changed UI')
            self.b.point(es[0]['x'],es[0]['y']);self.b.wait(lambda:'设置横封面' in self.body())
            # The main cover editor's upload input is distinct from AI reference-image inputs.
            for ratio,label in [('4:3','设置横封面'),('3:4','设置竖封面')]:
                self.tap(label)
                # Both ratio editors may remain mounted. Match the upload area's visible parent,
                # not its input visibility; inputs themselves are intentionally hidden.
                if self.cfg.get('cover_input'):sel=self.cfg['cover_input']
                else:
                    self.b.js('''(()=>{document.querySelectorAll('[data-cover-upload]').forEach(e=>e.removeAttribute('data-cover-upload'));const matches=[...document.querySelectorAll('input[type=file][accept*=image]')].filter(e=>{for(let p=e.parentElement,i=0;p&&i<4;p=p.parentElement,i++){if(p.innerText.includes('生成参考图'))return false;if(p.innerText.includes('点击上传文件或拖拽文件到这里')){const r=p.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(p).display!=='none'}}return false});if(matches.length!==1)throw Error('Cover upload target count '+matches.length);matches[0].setAttribute('data-cover-upload','active');return true})()''')
                    sel='input[data-cover-upload=active]'
                self.b.upload(sel,self.local(covers[ratio]));time.sleep(.7);self.evidence('cover-'+ratio.replace(':','x'))
            self.tap('完成')
        self.j['cover_visual_review']='pending';return {'status':'set','visual_review':'pending','instruction':'Inspect platform preview screenshots; record review with --step review-covers --evidence PATH'}

    def declaration(self):
        if self.p=='douyin':
            if self.cfg['declaration'] not in self.body():self.tap('请选择自主声明');self.tap(self.cfg['declaration']);self.tap('确定')
        elif self.p=='bilibili':
            sel=self.cfg['declaration_input']
            if self.b.js('document.querySelector('+json.dumps(sel)+').value')!=self.cfg['declaration']:self.b.tap(selector=sel);self.tap(self.cfg['declaration'])
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
            # Closed custom element shadow: locate the real button through CDP's exposed DOM, no fixed screen coordinates.
            root=self.b.cdp('DOM.getDocument',depth=-1,pierce=True)
            targets=[]
            def walk(n):
                attrs=dict(zip(n.get('attributes',[])[::2],n.get('attributes',[])[1::2]))
                if n.get('nodeName') in ['BUTTON','DIV','SPAN'] and (attrs.get('save-text')=='暂存离开' or any(c.get('nodeValue','').strip()=='暂存离开' for c in n.get('children',[]))):targets.append(n)
                for k in ['children','shadowRoots']:
                    for child in n.get(k,[]):walk(child)
            walk(root['root'])
            if len(targets)!=1:raise UIError('Save button is in a closed shadow root; inspect screenshot and click its current coordinates, then run inspect/reopen. No guessed coordinates.')
            n=targets[0];self.b.cdp('DOM.scrollIntoViewIfNeeded',nodeId=n['nodeId']);box=self.b.cdp('DOM.getBoxModel',nodeId=n['nodeId'])['model']['content'];self.b.point(sum(box[::2])/4,sum(box[1::2])/4)
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
        if normal(self.item['description']) not in normal(editor):raise UIError('Saved description differs')
        if self.p in ['douyin','xiaohongshu']:
            for tag in self.item.get('topics',[]):
                if self.p=='douyin':ok=self.b.js("[...document.querySelectorAll('[data-mention]')].some(e=>e.innerText.trim()==="+json.dumps('#'+tag)+")")
                else:ok='#'+tag+'[话题]#' in editor
                if not ok:raise UIError('Missing linked topic '+tag)
        elif self.p in ['bilibili','youtube']:
            if self.p=='youtube':YouTubeDraft(self).ensure_advanced()
            sel=self.one_visible(self.cfg.get('tag_input','input[aria-label="标签"]'))
            chips=self.b.js('document.querySelector('+json.dumps(sel)+').parentElement.parentElement.innerText')
            for tag in self.item.get('topics',[]):
                if tag not in [x.strip() for x in chips.splitlines()]:raise UIError('Missing saved tag '+tag)
        if self.p!='youtube' and self.cfg['declaration'] not in s['text'] and not any(x.get('value')==self.cfg['declaration'] for x in s['inputs']):raise UIError('AI declaration missing')
        if self.p=='youtube':
            YouTubeDraft(self).verify_settings()
            radios=self.b.js("JSON.stringify([...document.querySelectorAll('tp-yt-paper-radio-button[aria-checked=true]')].map(e=>e.getAttribute('name')))")
            for name in ['VIDEO_MADE_FOR_KIDS_'+('MFK' if self.item['made_for_kids'] else 'NOT_MFK'),'VIDEO_HAS_ALTERED_CONTENT_'+('YES' if self.item['ai_disclosure'] else 'NO')]:
                if name not in radios:raise UIError('Saved declaration missing '+name)
        if self.j.get('cover_visual_review')!='passed':raise UIError('Cover visual review has not been recorded')
        self.evidence('verified')
        return {'status':'saved_reopened_verified','url':s['url'],'published':False,'review_required':True}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('manifest',type=Path);ap.add_argument('--platform',choices=list(PROFILES),required=True);ap.add_argument('--run-dir',type=Path,required=True);ap.add_argument('--session',required=True);ap.add_argument('--endpoint',default='http://127.0.0.1:10086');ap.add_argument('--step',choices=STEPS+['inspect','open','prepare','status','review-covers','context','checks'],default='inspect');ap.add_argument('--profiles',type=Path);ap.add_argument('--evidence',type=Path)
    a=ap.parse_args()
    try:
        check(a.manifest)
        p=Publisher(a.manifest,a.platform,a.run_dir,a.session,a.endpoint,json.loads(a.profiles.read_text(encoding='utf-8')) if a.profiles else None)
        if a.step=='open':
            try:r=p.b.select(p.cfg['url'])
            except UIError as e:
                if 'no tab matching' not in str(e).lower() and 'was closed' not in str(e).lower():raise
                r=p.b.open(p.cfg['url'],'视频发布准备')
        elif a.step=='status':r=p.j
        elif a.step=='review-covers':
            r=p.review_covers(a.evidence)
        elif a.step=='prepare':
            r={}
            for step in steps_for(p.p):
                if p.j['steps'].get(step,{}).get('status')=='done':continue
                r[step]=p.run(step)
                print(json.dumps({'step':step,'status':p.j['steps'][step]['status']},ensure_ascii=False),flush=True)
                if p.j['steps'][step]['status']=='pending':r['next']='YouTube is still processing. Continue other platforms and resume this same command later; do not re-upload.';break
                if step=='covers':r['next']='Visually inspect cover previews, record review-covers, then resume prepare';break
        else:r=p.run(a.step)
        print(json.dumps(r,ensure_ascii=False,indent=2));return 0
    except (UIError,ValueError,OSError,KeyError) as e:
        print('Stopped: '+str(e),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
