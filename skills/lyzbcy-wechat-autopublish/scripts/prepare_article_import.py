"""Local Word import carrier for an approved Markdown + ordered image article.

Creates a document for native WeChat 文档导入. It never logs in, uploads,
submits, adds a native Channels reference, or grants release authorization.
"""
import argparse, hashlib, json, re, zipfile
from pathlib import Path


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def prepare(plan_file, output):
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    p=Path(plan_file).resolve(); base=p.parent; plan=json.loads(p.read_text('utf-8-sig'))
    content=(base/plan['source']).resolve(); manifest=(base/plan['image_manifest']).resolve()
    if sha(content)!=plan['source_sha256'] or sha(manifest)!=plan['image_manifest_sha256']:
        raise ValueError('Source or image manifest fingerprint differs')
    m=json.loads(manifest.read_text('utf8'))
    if m['content_id']!=plan['content_id'] or m['source_video_sha256']!=plan['video_sha256']:
        raise ValueError('Manifest is not sourced from the selected final video')
    entries=m['images']; paths=[x['path'] for x in entries]
    if not entries or len(set(paths))!=len(paths) or [x['order'] for x in entries]!=list(range(1,len(entries)+1)):
        raise ValueError('Invalid image order')
    approved={x['path']:x['sha256'] for x in entries}
    text=content.read_text('utf8'); marker='\n## '+plan['title']+'\n'
    if text.count(marker)!=1:raise ValueError('Unique article title heading missing')
    body=text.split(marker,1)[1];d=Document()
    for name in ('Normal','List Bullet','Heading 1'):
        st=d.styles[name];st.font.name='Microsoft YaHei';st._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Microsoft YaHei');st.font.size=Pt(12 if name!='Heading 1' else 17);st.font.color.rgb=RGBColor.from_string('222222' if name!='Heading 1' else 'A78000');st.paragraph_format.space_after=Pt(8);st.paragraph_format.line_spacing=1.5
    seen=[];paragraphs=[]
    for line in body.splitlines():
        line=line.strip()
        if not line:continue
        match=re.fullmatch(r'!\[([^]]+)\]\(([^)]+)\)',line)
        if match:
            f=(content.parent/match[2]).resolve()
            if f.parent!=manifest.parent or f.name not in approved or sha(f)!=approved[f.name]:raise ValueError('Image not in approved manifest')
            seen.append(f.name);pa=d.add_paragraph();pa.alignment=WD_ALIGN_PARAGRAPH.CENTER;pa.add_run().add_picture(str(f),width=Inches(5.85));continue
        if line.startswith('### '):text=line[4:];d.add_heading(text,level=1)
        elif line.startswith('- '):text=line[2:];d.add_paragraph(text,style='List Bullet')
        else:text=line;d.add_paragraph(text)
        paragraphs.append(text)
    if seen!=paths:raise ValueError('Source image order differs from manifest')
    out=Path(output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise FileExistsError(out)
    temp=out.with_suffix('.tmp.docx');d.save(temp)
    try:
        with zipfile.ZipFile(temp) as z:
            actual=sorted(hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('word/media/'))
        if actual!=sorted(approved.values()):raise ValueError('Embedded media bytes differ')
        if [x.text for x in Document(temp).paragraphs if x.text]!=paragraphs:raise ValueError('DOCX body differs')
        if temp.stat().st_size>15_000_000:raise ValueError('Import exceeds observed 15 MB limit; verify current editor before using')
        temp.replace(out)
    finally:temp.unlink(missing_ok=True)
    return {'path':str(out),'sha256':sha(out),'content_id':plan['content_id'],'image_order':seen,'paragraphs':paragraphs,'size':out.stat().st_size,'status':'local_import_carrier_only'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--out',required=True);a=p.parse_args();print(json.dumps(prepare(a.plan,a.out),ensure_ascii=False))
