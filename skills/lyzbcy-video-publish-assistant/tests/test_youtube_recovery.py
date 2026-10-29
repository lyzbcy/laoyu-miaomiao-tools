"""Synthetic UI recovery checks; no browser connection or real posting."""
from pathlib import Path
import json, shutil, subprocess, sys, unittest
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from browser import UIError
from youtube import DRAFT_FIELDS, DRAFT_ROW, YouTubeDraft


@unittest.skipUnless(shutil.which('node'), 'Node required for DOM replay')
class DOMRecovery(unittest.TestCase):
    def run_js(self, source, setup):
        # Minimal DOM adapter: selection is based on synthetic UI attributes,
        # not application internals. The production selector/decision JS runs.
        harness = r'''
const getComputedStyle=e=>({visibility:e.hidden?'hidden':'visible'});
const field=(text,label,hidden=false)=>({innerText:text,label,hidden,
  getClientRects:()=>hidden?[]:[1]});
function root(fields,hidden=false){return {hidden,getClientRects:()=>hidden?[]:[1],
  querySelectorAll:s=>fields.filter(e=>s.includes('aria-label="'+e.label+'"'))};}
function row(title,ids=[],hidden=false,buttons=1){return {
  innerText:'6:11\n'+title+'\n草稿',hidden,attrs:{},
  getClientRects:()=>hidden?[]:[1],
  querySelectorAll:s=>s==='a[href]'?ids.map(href=>({href})):
    Array.from({length:buttons},()=>field('编辑草稿','编辑草稿')),
  setAttribute(k,v){this.attrs[k]=v},removeAttribute(k){delete this.attrs[k]}};}
''' + setup + ';try{console.log(JSON.stringify({ok:true,value:eval(' + json.dumps(source) + ')}))}catch(e){console.log(JSON.stringify({ok:false,error:e.message}))}'
        result = subprocess.run(['node', '-e', harness], capture_output=True,
                                text=True, encoding='utf8', check=True)
        return json.loads(result.stdout)

    def fields(self, roots):
        profile = Path(__file__).resolve().parents[1] / 'scripts/profiles.json'
        values = json.loads(profile.read_text(encoding='utf8'))['youtube']
        cfg = {key:values[key] for key in ('title','editor')}
        setup = "const playlist=[field('Playlist','playlist-title'),field('Wrong','playlist-description')];const video=[field('Video','添加一个可描述你视频的标题（输入 @ 可提及某个频道）'),field('Right','向观看者介绍你的视频（输入 @ 可提及频道）')];const roots=" + roots + ";const document={querySelectorAll:s=>roots};"
        return self.run_js(DRAFT_FIELDS.replace('CFG', json.dumps(cfg)), setup)

    def test_hidden_playlist_fields_do_not_replace_video_description(self):
        result = self.fields('[root(playlist,true),root([...playlist,...video])]')
        self.assertTrue(result['ok'], result)
        self.assertEqual(json.loads(result['value']), {'title':'Video','description':'Right'})

    def test_hidden_old_video_root_is_ignored(self):
        result = self.fields('[root([field("Old","添加一个可描述你视频的标题（输入 @ 可提及某个频道）"),field("Old","向观看者介绍你的视频（输入 @ 可提及频道）")],true),root(video)]')
        self.assertEqual(json.loads(result['value'])['description'], 'Right')

    def test_missing_or_duplicate_visible_dialog_stops(self):
        for roots in ('[]', '[root(video),root(video)]'):
            self.assertFalse(self.fields(roots)['ok'])

    def test_missing_or_ambiguous_video_field_stops(self):
        for roots in ('[root(playlist)]', '[root([...video,field("Other","向观看者介绍你的视频（输入 @ 可提及频道）")])]'):
            self.assertFalse(self.fields(roots)['ok'])

    def rows(self, rows):
        source = DRAFT_ROW.replace('TITLE', json.dumps('Test')).replace('EXPECTED', json.dumps('abcdefghijk'))
        setup = 'const rows=' + rows + ';const document={querySelectorAll:s=>s==="ytcp-video-row"?rows:rows.filter(e=>e.attrs["data-publish-draft"])}'
        return self.run_js(source, setup)

    def test_unique_draft_without_link_can_be_opened_for_id_check(self):
        self.assertTrue(self.rows('[row("Test")]')['value'])

    def test_two_same_title_linkless_drafts_are_ambiguous(self):
        self.assertFalse(self.rows('[row("Test"),row("Test")]')['ok'])

    def test_explicit_wrong_video_link_is_not_selected(self):
        self.assertFalse(self.rows('[row("Test",["https://studio.youtube.com/video/12345678901/edit"])]')['value'])

    def test_matching_video_link_and_hidden_duplicate(self):
        self.assertTrue(self.rows('[row("Test",["https://studio.youtube.com/video/abcdefghijk/edit"]),row("Test",[],true)]')['value'])

    def test_hidden_or_duplicate_edit_buttons_do_not_select(self):
        for rows in ('[row("Test",[],true)]', '[row("Test",[],false,2)]', '[row("Test",[],false,0)]'):
            self.assertFalse(self.rows(rows)['value'])


class IdentityRecovery(unittest.TestCase):
    def make(self):
        b = Mock()
        p = SimpleNamespace(b=b, j={'youtube_kind':'video','youtube_video_id':'abcdefghijk','steps':{}},
                            item={'title':'Test'}, cfg={'title':'#title'},
                            shown=Mock(side_effect=[False,True]), persist=Mock())
        b.state.return_value={'url':'https://studio.youtube.com/channel/test/videos/upload'}
        b.wait.side_effect=lambda fn,**kw:fn()
        b.js.return_value=True
        return p, YouTubeDraft(p)

    def test_opened_linkless_draft_must_expose_bound_id(self):
        for actual in ('12345678901', None):
            p,d=self.make()
            d.context=Mock(return_value={'draft_dialog':True,'title':'Test','video_id':actual,'text':''})
            with self.assertRaisesRegex(UIError, 'ID differs or is missing'):
                d.reopen()
            p.b.tap.assert_called_once()  # Opens the draft, never edits/publishes it.
            p.b.edit.assert_not_called()
            p.persist.assert_not_called()
            self.assertEqual(p.j['youtube_video_id'], 'abcdefghijk')

    def test_matching_opened_id_preserves_binding(self):
        p,d=self.make()
        d.context=Mock(return_value={'draft_dialog':True,'title':'Test','video_id':'abcdefghijk','text':''})
        d.reopen()
        self.assertEqual(p.j['youtube_video_id'], 'abcdefghijk')
        p.persist.assert_called_once()

    def test_bound_id_missing_in_context_never_silently_passes(self):
        p,d=self.make()
        with self.assertRaises(UIError):d.remember({'title':'Test'})
        p.persist.assert_not_called()


if __name__ == '__main__':
    unittest.main()
