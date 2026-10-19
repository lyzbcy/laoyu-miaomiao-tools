"""Browser UI primitives. Python stdlib + installed curl; no browser/model download."""
from pathlib import Path
import base64,hashlib,json,os,subprocess,tempfile,time

class UIError(RuntimeError): pass

class Browser:
    def __init__(self, session, endpoint='http://127.0.0.1:10086', timeout=45):
        self.session,self.endpoint,self.timeout=session,endpoint.rstrip('/'),timeout

    def send(self,action,args=None):
        fd,path=tempfile.mkstemp(prefix='video-publish-',suffix='.json')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump({'session':self.session,'action':action,'args':args or {}},f,ensure_ascii=False)
            r=subprocess.run(['curl.exe' if os.name=='nt' else 'curl','-sS','--max-time',str(self.timeout),'-X','POST',self.endpoint+'/command','-H','Content-Type: application/json','--data-binary','@'+path],capture_output=True,timeout=self.timeout+3)
            if r.returncode: raise UIError(r.stderr.decode('utf-8',errors='replace')[:400])
            v=json.loads(r.stdout.decode('utf-8'))
            if not v.get('ok'):raise UIError(str(v.get('error',v)))
            return v.get('data')
        finally:Path(path).unlink(missing_ok=True)

    def js(self,code):
        r=self.send('evaluate',{'code':code});v=r.get('value')
        if r.get('type')=='string':
            try:return json.loads(v)
            except (ValueError,TypeError):pass
        return v

    def cdp(self,method,**params):return self.send('cdp',{'method':method,'params':params})
    def focus(self,on=True):self.cdp('Emulation.setFocusEmulationEnabled',enabled=on)
    def select(self,url):return self.send('find_tab',{'url':url})
    def open(self,url,group):return self.send('navigate',{'url':url,'newTab':True,'group_title':group})
    def wait(self,fn,timeout=20,interval=.5):
        deadline=time.monotonic()+timeout
        while True:
            v=fn()
            if v:return v
            if time.monotonic()>=deadline:raise UIError('UI condition timed out; inspect current page before retrying')
            time.sleep(interval)

    def point(self,x,y):
        self.focus()
        for t in ['mouseMoved','mousePressed','mouseReleased']:
            self.cdp('Input.dispatchMouseEvent',type=t,x=x,y=y,**({'button':'left','clickCount':1} if t!='mouseMoved' else {}))

    def target(self,selector=None,text=None,scope='body'):
        # Exact matching excludes editor content and preview copies. Prefer buttons/labels.
        code='''(()=>{const cfg=CFG;const root=document.querySelector(cfg.scope);if(!root)throw Error('Scope missing');let es=cfg.selector?[...root.querySelectorAll(cfg.selector)]:[...root.querySelectorAll('button,[role=button],[role=option],label,a,span,div,ytcp-button,tp-yt-paper-radio-button,yt-formatted-string')].filter(e=>e.innerText?.trim()===cfg.text&&!e.closest('[contenteditable=true]'));es=es.filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'});if(!cfg.selector){es=es.filter(e=>!es.some(other=>other!==e&&e.contains(other)));}if(es.length!==1)throw Error('Ambiguous/missing UI target '+JSON.stringify({cfg,count:es.length}));const e=es[0];e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2,tag:e.tagName,text:(e.innerText||e.getAttribute('aria-label')||'').trim(),disabled:e.disabled||e.getAttribute('aria-disabled')==='true'})})()'''.replace('CFG',json.dumps(dict(selector=selector,text=text,scope=scope),ensure_ascii=False))
        return self.js(code)

    def tap(self,selector=None,text=None,scope='body'):
        self.focus() # Focus emulation can change layout; measure after it is enabled.
        d=self.target(selector,text,scope)
        if d['text'] in ['发布','立即投稿','提交审核','确认发布','Publish','Schedule','定时发布']:raise UIError('Final publication is outside this draft-only script')
        if d['disabled']:raise UIError('UI target disabled')
        self.point(d['x'],d['y']);return d

    def semantic(self,role,name):
        """Use a current accessibility ref for ordinary tabs/buttons.

        Studio renders nested buttons and scrolls metadata panels. A semantic
        click avoids a measured coordinate landing on a nearby verification link.
        """
        if name.strip() in ['发布','立即投稿','提交审核','确认发布','Publish','Schedule','定时发布']:
            raise UIError('Final publication is outside this draft-only script')
        matches=[]
        def walk(node):
            if isinstance(node,list):return sum(walk(x) for x in node)
            if not isinstance(node,dict) or node.get('hidden'):return 0
            descendants=walk(node.get('children',[]))
            own=node.get('role')==role and node.get('name','').strip()==name.strip() and node.get('ref')
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
        # Move through the actual editor, rather than mutating a framework's hidden model.
        self.tap(selector=selector)
        self.key('a',2);self.insert(value)
        actual=self.js("(()=>{const e=document.querySelector("+json.dumps(selector)+");return e.isContentEditable?e.innerText:e.value})()")
        clean=lambda s:' '.join(s.replace('\u200b','').split())
        if clean(actual)!=clean(value):raise UIError('Text read-back differs; do not append/retry blindly')
        return actual

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
