import hashlib,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:
    from PIL import Image
    import docx
    from prepare_article_import import prepare,sha
except ImportError:  # optional local dependencies
    Image=None

@unittest.skipUnless(Image is not None,'Pillow and python-docx needed')
class ImportTests(unittest.TestCase):
    def test_exact_embedded_assets_order_and_source(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);im=p/'images';im.mkdir()
            for i,color in enumerate(('yellow','black'),1):Image.new('RGB',(100,120),color).save(im/f'{i}.jpg')
            manifest=im/'manifest.json';manifest.write_text(json.dumps({'content_id':'c','source_video_sha256':'v','images':[{'path':f'{i}.jpg','sha256':sha(im/f'{i}.jpg'),'order':i} for i in (1,2)]}),'utf8')
            source=p/'source.md';source.write_text('# Draft\n\n## Title\n\nIntro\n\n![a](images/1.jpg)\n\n### Heading\n\n- Bullet\n\n![b](images/2.jpg)','utf8')
            plan=p/'plan.json';data={'title':'Title','content_id':'c','video_sha256':'v','source':'source.md','image_manifest':'images/manifest.json','source_sha256':sha(source),'image_manifest_sha256':sha(manifest)};plan.write_text(json.dumps(data),'utf8')
            r=prepare(plan,p/'out.docx');self.assertEqual(r['image_order'],['1.jpg','2.jpg']);self.assertEqual(r['paragraphs'],['Intro','Heading','Bullet'])
            source.write_text(source.read_text().replace('images/1.jpg','images/2.jpg'),'utf8')
            with self.assertRaises(ValueError):prepare(plan,p/'changed.docx')
            data['source_sha256']=sha(source);plan.write_text(json.dumps(data),'utf8')
            with self.assertRaises(ValueError):prepare(plan,p/'wrong_order.docx')

if __name__=='__main__': unittest.main()
