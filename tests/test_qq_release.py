"""QQ release parity and package privacy checks; no external writes."""
from pathlib import Path
import hashlib,json,re,unittest,zipfile

R=Path(__file__).resolve().parents[1];S=R/'skills/lyzbcy-qq-napcat-messenger'

class QQReleaseTests(unittest.TestCase):
    def setUp(self):
        self.skill=(S/'SKILL.md').read_text(encoding='utf8')
        self.version=re.search(r'  version: "([\d.]+)"',self.skill)[1]
        self.files=re.findall(r'^    - (\S+)$',self.skill,re.M)
        self.html=(R/'docs/index.html').read_text(encoding='utf8')
        self.manifest=json.loads((S/'update.json').read_text(encoding='utf8'))
    def test_manifest_complete_and_current(self):
        self.assertEqual(self.manifest['version'],self.version)
        self.assertEqual(set(self.manifest['sha256']),set(self.files)-{'update.json'})
        for p,h in self.manifest['sha256'].items():self.assertEqual(hashlib.sha256((S/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),h)
    def test_no_private_machine_files_in_manifest(self):
        self.assertNotIn('runtime.local.json',self.files)
        self.assertTrue(all(not p.startswith('.') for p in self.files))
    def test_site_card_summary_and_readme(self):
        card=self.html.split('id="qq-napcat-messenger"',1)[1].split('</article>',1)[0]
        self.assertIn('QQ 自动收发 · v'+self.version,card)
        self.assertIn('10) lyzbcy-qq-napcat-messenger（QQ 自动收发 · v'+self.version+'）',self.html)
        row=next(x for x in (R/'README.md').read_text(encoding='utf8').splitlines() if x.startswith('| 💬 `lyzbcy-qq-napcat-messenger`'))
        self.assertIn('v'+self.version,row)
    def test_download_links_consistent(self):
        links=re.findall(r'https://github.com/lyzbcy/laoyu-miaomiao-tools/releases/download/[^\s"<>\)]+/lyzbcy-qq-napcat-messenger.zip',self.html)
        self.assertGreaterEqual(len(links),2);self.assertEqual(len(set(links)),1)
        self.assertIn(links[0],(R/'README.md').read_text(encoding='utf8'))
    def test_zip_matches_source(self):
        with zipfile.ZipFile(R/'dist/lyzbcy-qq-napcat-messenger.zip') as z:
            self.assertIsNone(z.testzip());self.assertEqual(set(z.namelist()),{S.name+'/'+p for p in self.files})
            for p in self.files:self.assertEqual(z.read(S.name+'/'+p),(S/p).read_bytes().replace(b'\r\n',b'\n'))
    def test_changelog_and_page_refresh(self):
        self.assertIn('## ['+self.version+']',(S/'CHANGELOG.md').read_text(encoding='utf8'))
        page=json.loads((R/'docs/version.json').read_text(encoding='utf8'))['pages']['laoyu-miaomiao-tools']
        self.assertIn("version: '"+page['version']+"'",self.html)
        self.assertIn(page['changes'][0],self.html)

if __name__=='__main__':unittest.main()
