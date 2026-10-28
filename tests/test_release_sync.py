"""Release-only consistency checks, no external writes."""
from pathlib import Path
import hashlib,json,re,subprocess,unittest,zipfile,shutil
R=Path(__file__).resolve().parents[1];S=R/'skills/lyzbcy-video-publish-assistant'
class ReleaseSync(unittest.TestCase):
 def setUp(self):
  self.skill=(S/'SKILL.md').read_text(encoding='utf8');self.version=re.search(r'  version: ([\d.]+)',self.skill)[1]
  self.html=(R/'docs/index.html').read_text(encoding='utf8');self.registry=json.loads((R/'docs/version.json').read_text(encoding='utf8'))['pages']['laoyu-miaomiao-tools']
 def test_skill_manifest_and_release_marker(self):
  manifest=json.loads((S/'update.json').read_text(encoding='utf8'));self.assertEqual(manifest['version'],self.version)
  self.assertIn('正式版 '+self.version,self.skill);self.assertNotIn('公开分发保持原版',self.skill)
  self.assertRegex((S/'CHANGELOG.md').read_text(encoding='utf8'),r'## \['+re.escape(self.version)+r'\].*正式发行')
  for path,h in manifest['sha256'].items():self.assertEqual(hashlib.sha256((S/path).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),h,path)
 def test_all_target_download_links_match(self):
  urls=re.findall(r'https://github.com/lyzbcy/laoyu-miaomiao-tools/releases/download/[^\s"<>\)]+/lyzbcy-video-publish-assistant.zip',self.html)
  self.assertGreaterEqual(len(urls),3);self.assertEqual(len(set(urls)),1)
  row=next(x for x in (R/'README.md').read_text(encoding='utf8').splitlines() if '`lyzbcy-video-publish-assistant`' in x)
  self.assertIn('v'+self.version,row);self.assertIn(urls[0],row)
 def test_card_and_ai_summary_versions(self):
  card=self.html.split('id="video-publish-assistant"',1)[1].split('</article>',1)[0]
  self.assertIn('多平台视频投稿 · v'+self.version,card)
  self.assertIn('11) lyzbcy-video-publish-assistant（多平台视频投稿 · v'+self.version+'）',self.html)
 def test_refresh_registry_and_changelog(self):
  self.assertIn("version: '"+self.registry['version']+"'",self.html)
  self.assertIn(self.registry['changes'][0],self.html);self.assertIn('v'+self.version,self.registry['changes'][0])
 def test_zip_matches_manifest_and_source(self):
  with zipfile.ZipFile(R/'dist/lyzbcy-video-publish-assistant.zip') as z:
   self.assertIsNone(z.testzip())
   files=re.findall(r'^    - (\S+)$',self.skill,re.M)
   self.assertEqual(set(z.namelist()),{'lyzbcy-video-publish-assistant/'+x for x in files})
   for path in files:self.assertEqual(z.read('lyzbcy-video-publish-assistant/'+path),(S/path).read_bytes().replace(b'\r\n',b'\n'))
 @unittest.skipUnless(shutil.which('node'),'Node needed')
 def test_inline_scripts_parse(self):
  for script in re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>',self.html,re.S):
   if script.strip():
    r=subprocess.run(['node','-e',"new Function(require('fs').readFileSync(0,'utf8'))"],input=script,capture_output=True,text=True,encoding='utf8')
    self.assertEqual(r.returncode,0,r.stderr)
