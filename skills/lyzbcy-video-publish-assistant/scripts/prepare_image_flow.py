"""Build ordered mobile image cards FROM the final approved-for-review video.
Local preparation only: never uploads or authorizes either form."""
import argparse, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

W,H=1080,1440
YELLOW="#FFE116"; WHITE="#F6F4EC"; MUTED="#BDBDB4"; DARK="#141611"
FONT=Path("C:/Windows/Fonts/msyh.ttc")
BOLD=Path("C:/Windows/Fonts/msyhbd.ttc")
ROUTES={
"douyin":["video","image"], "xiaohongshu":["video","image"],
"bilibili":["video","dynamic_image"], "kuaishou":["video","image"],
"weibo":["video","image"], "youtube":["video","community_image_if_available"],
"x":["video","image_thread"], "wechat_channels":["video","image_if_available"],
"wechat_official":["article_images"], "juejin":["article_images"],
"zhihu":["video_if_available","article_images"]
}
def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for data in iter(lambda:f.read(1024*1024),b""): h.update(data)
    return h.hexdigest()
def font(size,bold=False): return ImageFont.truetype(str(BOLD if bold else FONT),size)
def drawtext(draw,xy,s,size,color=WHITE,bold=False,width=940):
    f=font(size,bold)
    rows=[]
    for original in s.split("\n"):
        row=""
        for c in original:
            if row and draw.textlength(row+c,font=f)>width:
                rows.append(row); row=c
            else: row+=c
        rows.append(row)
    x,y=xy
    for row in rows:
        draw.text((x,y),row,font=f,fill=color,anchor="lt")
        y+=int(size*1.42)
    return y
def panel(im,source,box):
    x,y,w,h=box
    source=ImageOps.contain(source.convert("RGB"),(w,h),Image.Resampling.LANCZOS)
    im.paste(source,(x+(w-source.width)//2,y+(h-source.height)//2))
def extract(video,sec, crop):
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"frame.png"
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-ss",str(sec),"-i",str(video),"-frames:v","1","-y",str(p)],check=True)
        with Image.open(p) as im: return im.convert("RGB").crop(tuple(crop) if crop else (0,0,*im.size))
def make_card(card,root,video,i,total,plan=None):
    if card.get("cover"):
        with Image.open(root/card["cover"]) as im:
            return ImageOps.fit(im.convert("RGB"),(W,H),Image.Resampling.LANCZOS)
    im=Image.new("RGB",(W,H),DARK); d=ImageDraw.Draw(im)
    for x in range(0,W,96): d.line((x,0,x,H),fill="#1C201A")
    for y in range(0,H,96): d.line((0,y,W,y),fill="#1C201A")
    d.polygon([(0,0),(W,0),(W,35),(0,110)],fill=YELLOW)
    d.rectangle((0,H-30,W,H),fill=YELLOW)
    kicker=card.get("kicker",(plan or {}).get("kicker",""))
    if kicker:drawtext(d,(70,116),kicker,28,YELLOW,True)
    drawtext(d,(70,169),card["title"],64,YELLOW,True)
    drawtext(d,(70,255),card["subtitle"],34,MUTED,width=930)
    if card.get("frame") is not None:
        d.rounded_rectangle((65,340,1015,884),radius=18,fill="#272B24",outline="#665C1B",width=3)
        panel(im,extract(video,card["frame"],card.get("crop")),(78,351,924,522))
        y=930
    else:
        y=340
    for idx,line in enumerate(card["lines"]):
        d.ellipse((70,y+13,86,y+29),fill=YELLOW)
        y=drawtext(d,(104,y),line,42,WHITE,idx==0,width=890 if card.get("frame") else 880)+23
    if y>1240: raise ValueError(f"card {i}: text exceeds layout ({y})")
    if card.get("sticker"):
        st=Image.open(root/card["sticker"]).convert("RGBA")
        st.thumbnail((195,195),Image.Resampling.LANCZOS)
        xx,yy=875-st.width//2,1327-st.height
        if yy<y-15: raise ValueError(f"card {i}: sticker overlaps text at {y}")
        im.paste(st,(xx,yy),st)
    drawtext(d,(70,1348),f"{i:02d} / {total:02d}   ·   {card.get('footer','来自最终成片')}",25,MUTED,width=930)
    return im
def verify(out,video,plan,content_id,src_hash):
    m=json.loads((out/"manifest.json").read_text(encoding="utf-8"))
    assert m["source_video_sha256"]==src_hash and Path(m["source_video"]).resolve()==video
    assert m["plan_sha256"]==digest(plan) and m["content_id"]==content_id
    images=m["images"]
    assert [a["order"] for a in images]==list(range(1,len(images)+1))
    assert sorted(a["path"] for a in images)==sorted(p.name for p in out.glob("*.jpg"))
    for a in images:
        p=out/a["path"]
        assert digest(p)==a["sha256"]
        with Image.open(p) as im:
            assert list(im.size)==a["dimensions"]==[W,H]
            im.load()
    expected={(p,f) for p,forms in ROUTES.items() for f in forms}
    assert {(r["platform"],r["form"]) for r in m["matrix"]}==expected
    assert len(m["matrix"])==len(expected)
    assert m["mode"]=="prepare" and not any(m["approval"].values())
    assert all(not r["release_authorized"] for r in m["matrix"])
    return m

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--video",required=True,type=Path)
    parser.add_argument("--plan",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--content-id",required=True)
    parser.add_argument("--expected-sha256",required=True)
    parser.add_argument("--verify-only",action="store_true")
    args=parser.parse_args()
    video=args.video.resolve(); plan=args.plan.resolve(); out=args.out.resolve()
    src_hash=digest(video)
    if src_hash.lower()!=args.expected_sha256.lower(): raise SystemExit("Final video digest mismatch; regenerate from latest master.")
    if args.verify_only:
        manifest=verify(out,video,plan,args.content_id,src_hash)
        print(f"Verified {len(manifest['images'])} ordered image hashes, dimensions, final master and independent form rows.")
        return
    data=json.loads(plan.read_text(encoding="utf-8-sig"))
    cards=data["cards"]; root=plan.parent
    if not cards or not any(c.get("frame") is not None for c in cards): raise ValueError("Require genuine final-video frames.")
    out.mkdir(parents=True,exist_ok=True)
    assets=[]
    for i,card in enumerate(cards,1):
        im=make_card(card,root,video,i,len(cards),data)
        p=out/f"{i:02d}.jpg"; im.save(p,quality=94,subsampling=0)
        entry={"order":i,"path":p.name,"sha256":digest(p),"dimensions":[W,H],"source_seconds":card.get("frame"),"crop":card.get("crop"),"title":card.get("title","封面")}
        for key in ("sticker","cover"):
            if card.get(key):
                asset=(root/card[key]).resolve()
                entry[key]={"path":str(asset),"sha256":digest(asset)}
        assets.append(entry)
    # Independent ordered content-form state; do not reuse video or earlier version approval.
    manifest={"content_id":args.content_id,"source_video":str(video),"source_video_sha256":src_hash,
      "plan_sha256":digest(plan),"images":assets,"caption":data["caption"],
      "approval":{"video":False,"image":False,"release":False},"mode":"prepare",
      "matrix":[{"platform":p,"form":form,"state":"local_prepared" if not form.startswith("video") else "video_separate_manifest",
                 "route_must_be_verified":True,"release_authorized":False}
             for p,forms in ROUTES.items() for form in forms]}
    (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    verify(out,video,plan,args.content_id,src_hash)
    print(f"{len(assets)} ordered mobile cards; {len(manifest['matrix'])} separate form/platform rows; NO release authorization.")
if __name__=="__main__": main()
