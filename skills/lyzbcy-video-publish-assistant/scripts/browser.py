"""Browser UI primitives. Python stdlib + installed curl; no browser/model download."""
from pathlib import Path
import base64,hashlib,json,os,subprocess,tempfile,time,ipaddress
from urllib.parse import urlparse

class UIError(RuntimeError): pass

class Browser:
    def __init__(self, session, endpoint='http://127.0.0.1:10086', timeout=45):
        self.session,self.endpoint,self.timeout=session,endpoint.rstrip('/'),timeout

    def curl(self,*args):
        # Per-request bypass only: never alter the process or remote-host proxy.
        host=urlparse(self.endpoint).hostname
        try:loopback=ipaddress.ip_address(host).is_loopback
        except ValueError:loopback=host=='localhost'
        cmd=['curl.exe' if os.name=='nt' else 'curl','-sS','--max-time',str(self.timeout)]
        if loopback:cmd+=['--noproxy','*']
        r=subprocess.run(cmd+list(args),capture_output=True,timeout=self.timeout+3)
        if r.returncode:raise UIError(r.stderr.decode('utf-8',errors='replace')[:400])
        return json.loads(r.stdout.decode('utf-8'))

    def preflight(self):
        status=self.curl(self.endpoint+'/status')
        if status.get('running') is not True or status.get('extension_connected') is not True:
            raise UIError('WebBridge extension not connected; open the logged-in Edge extension and check its connection address')
        tabs=self.send('list_browser_tabs') # Read only; never attach, focus or navigate.
        if isinstance(tabs,dict) and tabs.get('success') is False:raise UIError('WebBridge tab inventory failed')
        return {'bridge':'ready','extension_connected':True,'tabs':tabs,'account_verified':False}

    def send(self,action,args=None):
        fd,path=tempfile.mkstemp(prefix='video-publish-',suffix='.json')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump({'session':self.session,'action':action,'args':args or {}},f,ensure_ascii=False)
            v=self.curl('-X','POST',self.endpoint+'/command','-H','Content-Type: application/json','--data-binary','@'+path)
            if not v.get('ok'):raise UIError(str(v.get('error',v)))
            return v.get('data')
        finally:Path(path).unlink(missing_ok=True)

    def js(self,code):
        r=self.send('evaluate',{'code':code});v=r.get('value')
        if r.get('type')=='string' and isinstance(v,str) and v.lstrip().startswith(('{','[')):
            try:return json.loads(v)
            except (ValueError,TypeError):pass
        return v

    def cdp(self,method,**params):return self.send('cdp',{'method':method,'params':params})
    def focus(self,on=True):self.cdp('Emulation.setFocusEmulationEnabled',enabled=on)
    def select(self,url):return self.send('find_tab',{'url':url})
    def open(self,url,group):return self.send('navigate',{'url':url,'newTab':True,'group_title':group})
    def wait(self,fn,timeout=20,interval=.6):
        deadline=time.monotonic()+timeout
        while True:
            v=fn()
            if v:return v
            if time.monotonic()>=deadline:raise UIError('UI condition timed out; inspect current page before retrying')
            time.sleep(min(interval,max(0,deadline-time.monotonic())))
            interval=min(4,interval*1.7)

    def point(self,x,y):
        self.focus()
        for t in ['mouseMoved','mousePressed','mouseReleased']:
            self.cdp('Input.dispatchMouseEvent',type=t,x=x,y=y,**({'button':'left','clickCount':1} if t!='mouseMoved' else {}))

    def target(self,selector=None,text=None,scope='body'):
        # Exact matching excludes editor content and preview copies. Prefer buttons/labels.
        code='''(()=>{const cfg=CFG;const root=document.querySelector(cfg.scope);if(!root)throw Error('Scope missing');let es=cfg.selector?[...root.querySelectorAll(cfg.selector)]:[...root.querySelectorAll('button,[role=button],[role=option],label,a,span,div,ytcp-button,tp-yt-paper-radio-button,yt-formatted-string')].filter(e=>e.innerText?.trim()===cfg.text&&!e.closest('[contenteditable=true]'));es=es.filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'});if(!cfg.selector){es=es.filter(e=>!es.some(other=>other!==e&&e.contains(other)));}if(es.length!==1)throw Error('Ambiguous/missing UI target '+JSON.stringify({cfg,count:es.length}));const e=es[0];e.scrollIntoView({block:'center',behavior:'instant'});const r=e.getBoundingClientRect();return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2,tag:e.tagName,text:(e.innerText||e.getAttribute('aria-label')||'').trim(),disabled:e.disabled||e.getAttribute('aria-disabled')==='true'})})()'''.replace('CFG',json.dumps(dict(selector=selector,text=text,scope=scope),ensure_ascii=False))
        result=self.js(code)
        # A scroll can settle asynchronously. Re-measure at click time.
        return result

    def tap(self,selector=None,text=None,scope='body'):
        self.focus() # Focus emulation can change layout; measure after it is enabled.
        d=self.target(selector,text,scope)
        if d['text'] in ['发布','立即投稿','提交审核','确认发布','Publish','Schedule','定时发布']:raise UIError('Final publication is outside this draft-only script')
        if d['disabled']:raise UIError('UI target disabled')
        self.point(d['x'],d['y']);return d

    def semantic(self,role,name,allow_final=False,scope=None,video_id=None):
        """Use a current accessibility ref for ordinary tabs/buttons.

        Studio renders nested buttons and scrolls metadata panels. A semantic
        click avoids a measured coordinate landing on a nearby verification link.
        """
        if not allow_final and name.strip() in ['发布','立即投稿','提交审核','确认发布','Publish','Schedule','定时发布']:
            raise UIError('Final publication is outside this draft-only script')
        if scope:
            cfg=json.dumps(dict(scope=scope,role=role,name=name,video_id=video_id))
            target=self.js(SCOPED_TARGET.replace('CFG',cfg))
            if target['disabled']:raise UIError('Scoped target disabled')
            return self.point(target['x'],target['y'])
        matches=[]
        def walk(node):
            if isinstance(node,list):return sum(walk(x) for x in node)
            if not isinstance(node,dict) or node.get('hidden'):return 0
            descendants=walk(node.get('children',[]))
            own=node.get('role')==role and (node.get('name') or '').strip()==name.strip() and node.get('ref')
            if own and not descendants:matches.append(node['ref'])
            return descendants or int(bool(own))
        snapshot=self.send('snapshot');walk(snapshot.get('tree',[]))
        matches=list(dict.fromkeys(matches))
        if len(matches)!=1:raise UIError('Ambiguous/missing semantic target '+repr((role,name,len(matches))))
        return self.send('click',{'selector':matches[0]})

    def key(self,key,modifiers=0):
        num={'Enter':13,'Escape':27,'Backspace':8,'a':65}[key]
        for t in ['keyDown','keyUp']:self.cdp('Input.dispatchKeyEvent',type=t,key=key,code='KeyA' if key=='a' else key,windowsVirtualKeyCode=num,modifiers=modifiers)

    def insert(self,text):self.cdp('Input.insertText',text=text)

    def edit(self,selector,value):
        # Use the actual DOM control: a scrolling coordinate click can focus a
        # hidden mention input on Bilibili. Never mutate framework internals.
        cfg=json.dumps({'selector':selector,'value':value},ensure_ascii=False)
        actual=self.js('''(()=>{const q=CFG;const es=[...document.querySelectorAll(q.selector)].filter(e=>e.getClientRects().length);if(es.length!==1)throw Error('Editable control ambiguous');const e=es[0];e.focus();if(e.isContentEditable){const range=document.createRange();range.selectNodeContents(e);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);if(!document.execCommand('insertText',false,q.value)){e.textContent=q.value;e.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:q.value}))}}else{const proto=e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(proto,'value').set.call(e,q.value);e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}))}return e.isContentEditable?e.innerText:e.value})()'''.replace('CFG',cfg))
        clean=lambda s:' '.join(s.replace('\u200b','').split())
        if clean(actual)!=clean(value):raise UIError('Text read-back differs; do not append/retry blindly')
        return actual

    def enter(self,selector):
        self.focus()
        self.js("(()=>{const es=[...document.querySelectorAll("+json.dumps(selector)+")].filter(e=>e.getClientRects().length);if(es.length!==1)throw Error('Enter target ambiguous');es[0].focus();return true})()")
        return self.key('Enter')

    def signals(self):
        """One compact guard read; do not return a whole dashboard to the model."""
        return self.js('''(()=>{const t=document.body.innerText;return JSON.stringify({url:location.href,publication_hint:['稿件投递成功','投稿成功','发布成功'].find(s=>t.includes(s))||null})})()''')

    def publication_state(self,title):
        return self.js(r'''(()=>{const title=TITLE;const visible=e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden';const dialogs=[...document.querySelectorAll('[role=dialog]')].filter(visible).map(e=>e.innerText).filter(t=>t.includes(title)&&t.includes('发布于'));const rows=[...document.querySelectorAll('ytcp-video-row')].filter(e=>visible(e)&&e.innerText.split('\n').some(x=>x.trim()===title));const t=document.body.innerText;return JSON.stringify({url:location.href,text:['发布成功','稿件投递成功','投稿成功','发布失败','投稿失败','未通过验证'].filter(x=>t.includes(x)).join('\n'),published_dialog_text:dialogs.join('\n'),matching_row_text:rows.length===1?rows[0].innerText:'',matching_row_video_id:rows.length===1?(rows[0].querySelector('a[href*="/video/"]')?.href.match(/\/video\/([A-Za-z0-9_-]{11})/)?.[1]||null):null,row_count:rows.length})})()'''.replace('TITLE',json.dumps(title)))

    def cover_state(self):
        return self.js('''(()=>{const hash=s=>{let h=0;for(let i=0;i<s.length;i++)h=(h*31+s.charCodeAt(i))|0;return h};const canvases=[...document.querySelectorAll('canvas')].filter(e=>e.getBoundingClientRect().width>200&&e.getBoundingClientRect().height>150).map(e=>{try{return hash(e.toDataURL())}catch{return null}}).filter(x=>x!==null);const images=[...document.querySelectorAll('[role=dialog] img')].filter(e=>e.getBoundingClientRect().width>150&&e.complete&&e.naturalWidth).map(e=>hash(e.currentSrc||e.src));return JSON.stringify({canvases,images})})()''')

    def fill_cover(self,selector,file):
        # Cover inputs are intentionally reusable; a selected VIDEO is not.
        self.js('''(()=>{const es=[...document.querySelectorAll(SEL)];if(es.length!==1||!es[0].accept.startsWith('image'))throw Error('Not a unique image input');es[0].value='';return true})()'''.replace('SEL',json.dumps(selector)))
        return self.upload(selector,file)

    def end(self,selector):
        self.js("(()=>{const e=document.querySelector("+json.dumps(selector)+");e.focus();if(e.isContentEditable){const r=document.createRange();r.selectNodeContents(e);r.collapse(false);const s=getSelection();s.removeAllRanges();s.addRange(r)}else e.setSelectionRange(e.value.length,e.value.length);return true})()")

    def upload(self,selector,file):
        # Only observed real DOM inputs; count=1, never choose a secondary uploader by index.
        obs=self.js("JSON.stringify([...document.querySelectorAll("+json.dumps(selector)+")].map(e=>({tag:e.tagName,type:e.type,accept:e.accept,files:e.files?.length})))")
        if len(obs)!=1 or obs[0]['tag']!='INPUT' or obs[0]['type']!='file':raise UIError('File target missing or ambiguous')
        if obs[0]['files']:raise UIError('Input already contains a file; inspect upload progress, do not retransmit')
        self.focus();doc=self.cdp('DOM.getDocument',depth=0)
        node=self.cdp('DOM.querySelector',nodeId=doc['root']['nodeId'],selector=selector)['nodeId']
        self.cdp('DOM.setFileInputFiles',nodeId=node,files=[str(Path(file).resolve())])
        return {'file_selected':True,'upload_complete':False}

    def state(self):
        return self.js('''JSON.stringify({url:location.href,title:document.title,text:document.body.innerText,inputs:[...document.querySelectorAll('input,textarea,[contenteditable=true]')].filter(e=>e.getClientRects().length).map(e=>({tag:e.tagName,type:e.type,placeholder:e.getAttribute('placeholder'),label:e.getAttribute('aria-label'),value:e.value,text:e.isContentEditable?e.innerText:undefined})),fileInputs:[...document.querySelectorAll('input[type=file]')].map(e=>({id:e.id,name:e.name,accept:e.accept,cls:e.className,files:e.files?.length})),videos:[...document.querySelectorAll('video')].map(e=>({duration:Number.isFinite(e.duration)?e.duration:null,ready:e.readyState}))})''')

    def screenshot(self,path):
        # Capture only the current task tab; save pixels locally without printing base64.
        r=self.cdp('Page.captureScreenshot',format='jpeg',quality=85,fromSurface=True)
        p=Path(path).resolve();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(r['data']))
        return {'path':str(p),'bytes':p.stat().st_size,'format':'jpeg'}

def digest(file):
    h=hashlib.sha256()
    with Path(file).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

SCOPED_TARGET=r"""(()=>{const q=CFG;const visible=e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden';const roots=[...document.querySelectorAll(q.scope)].filter(visible);if(roots.length!==1)throw Error('Dialog scope missing or ambiguous');const root=roots[0];if(q.video_id&&!([...root.querySelectorAll('a[href]')].some(e=>{try{const u=new URL(e.href);return ['youtube.com','www.youtube.com','youtu.be'].includes(u.hostname)&&(u.searchParams.get('v')===q.video_id||u.pathname==='/'+q.video_id||u.pathname==='/shorts/'+q.video_id)}catch{return false}})))throw Error('Dialog video ID differs');let es=[...root.querySelectorAll('[role],button')].filter(e=>visible(e)&&(e.getAttribute('role')||(e.tagName==='BUTTON'?'button':''))===q.role&&(e.getAttribute('aria-label')||e.innerText||'').trim()===q.name.trim());es=es.filter(e=>!es.some(x=>x!==e&&e.contains(x)));if(es.length!==1)throw Error('Scoped semantic target missing or ambiguous');const e=es[0];e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2,disabled:!!e.disabled||e.getAttribute('aria-disabled')==='true'})})()"""
