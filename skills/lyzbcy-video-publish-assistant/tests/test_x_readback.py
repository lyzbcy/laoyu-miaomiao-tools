"""Replay the public-post text query against text/image/BR DOM nodes."""
import json,subprocess,sys,tempfile,unittest,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from extension_steps import x_confirm,UIError

@unittest.skipUnless(shutil.which('node'),'Node needed')
class PublicTextReplay(unittest.TestCase):
 def run_query(self,code):
  fixture=r'''class Node {
 constructor(tag,text='',children=[]){this.tag=tag;this.text=text;this.children=children;for(const c of children)c.parent=this;this.alt=text;}
 cloneNode(){return new Node(this.tag,this.text,this.children.map(x=>x.cloneNode(true)));}
 querySelectorAll(s){return this.children.flatMap(c=>[...(s==='img[alt]'&&c.tag==='img'||s==='br'&&c.tag==='br'?[c]:[]),...c.querySelectorAll(s)]);}
 replaceWith(t){this.parent.children[this.parent.children.indexOf(this)]=new Node('text',t);}
 get textContent(){return this.tag==='img'?'':this.text+this.children.map(c=>c.textContent).join('');}
 get innerText(){return this.textContent;}}
 const text=new Node('div','',[new Node('text','猫咪 '),new Node('img','🐾'),new Node('br'),new Node('text','Add two numbers')]);
 const article={querySelector:s=>s==='[data-testid=tweetText]'?text:s==='video'?{}:null,querySelectorAll:s=>[{href:'https://x.com/example/status/123'}],innerText:'Made with AI'};
 const document={querySelectorAll:s=>[article]};
 '''
  r=subprocess.run(['node','-e',fixture+'process.stdout.write('+code+')'],capture_output=True,text=True,encoding='utf8',check=True)
  return json.loads(r.stdout)
 def test_image_emoji_and_linebreak_match(self):
  class B:
   js=lambda _,code:self.run_query(code)
  with tempfile.TemporaryDirectory() as td:
   result=x_confirm(B(),{'text':'猫咪 🐾\nAdd two numbers','account':'example'},Path(td)/'j.json')
   self.assertEqual(result['url'],'https://x.com/example/status/123')
 def test_copy_mismatch_does_not_confirm(self):
  class B:
   js=lambda _,code:self.run_query(code)
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'j.json'
   with self.assertRaises(UIError):x_confirm(B(),{'text':'猫咪 🐟 Add two numbers','account':'example'},p)
   self.assertFalse(p.exists())

if __name__=='__main__':unittest.main()
