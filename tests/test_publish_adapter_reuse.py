"""Regression of observed tag/cover controls, without a browser connection."""
from pathlib import Path
import sys, unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/lyzbcy-video-publish-assistant/scripts'))
from bilibili import BilibiliTopics
from browser import UIError
from publish import Publisher


class OrdinaryTags(unittest.TestCase):
    def make(self):
        b=Mock();p=SimpleNamespace(b=b,body=Mock(return_value=''),cfg={'tag_input':'input'},one_visible=Mock(return_value='input'))
        b.wait.side_effect=lambda fn,**kw:fn()
        return p,BilibiliTopics(p)

    def test_native_typing_replaces_synthetic_fill(self):
        p,t=self.make();p.b.js.side_effect=[None,'Algorithm']
        t.edit_ordinary('input','Algorithm')
        p.b.insert.assert_called_once_with('Algorithm')
        p.b.key.assert_called_once_with('a',modifiers=2)
        p.b.edit.assert_not_called()

    def test_existing_tag_has_no_typing(self):
        p,t=self.make();t.chips=Mock(return_value=['Algorithm'])
        self.assertEqual(t.ordinary('Algorithm'),'added')
        p.b.insert.assert_not_called()

    def test_failed_value_readback_never_presses_enter(self):
        p,t=self.make();t.chips=Mock(return_value=[])
        p.b.wait.side_effect=UIError('value not accepted')
        with self.assertRaises(UIError):t.ordinary('Algorithm')
        p.b.enter.assert_not_called()


class CoverControls(unittest.TestCase):
    def make(self,entries,item=None,active='设置横封面'):
        # Publisher.__init__ always sets item from the manifest's platform entry; __new__ bypasses it, so supply it here.
        p=object.__new__(Publisher);p.p='douyin';p.m={'covers':{'4:3':'landscape','3:4':'portrait'}}
        p.cfg={'cover_entries':'.cover'};p.j={};p.item=item or {};p.b=Mock();p.local=Mock(side_effect=lambda x:x);p.evidence=Mock()
        # The cover editor names its active ratio step; a release may open either ratio first.
        p.b.js.side_effect=lambda code:entries if 'JSON.stringify([...document.querySelectorAll' in code else active if 'step-active' in code else True
        p.b.wait.side_effect=lambda fn,**kw:fn()
        p.b.cover_state.side_effect=['before-horizontal','after-horizontal','before-portrait','after-portrait']
        return p

    def structural(self,p,sizes):
        return patch('publish.dimensions',side_effect=lambda path:sizes[Path(path).name]),patch('publish.digest',return_value='0'*64)

    def test_initial_horizontal_canvas_does_not_require_a_same_named_button(self):
        p=self.make([{'x':1,'y':2}]);dimension,digest=self.structural(p,{'landscape':(400,300),'portrait':(300,400)})
        with dimension,digest:result=p.covers()
        # A prepared cover whose ratio matches passes by structure; no visual review is requested.
        self.assertEqual(result,{'status':'set','visual_review':'passed','verification':'prepared_ratio_and_observed_ui_change'})
        self.assertEqual(p.b.fill_cover.call_count,2)
        p.b.semantic.assert_any_call('button','设置竖封面')
        self.assertNotIn(('button','设置横封面'),[c.args for c in p.b.semantic.call_args_list])
        self.assertEqual(p.j['cover_visual_review'],'passed')

    def test_initial_vertical_canvas_uploads_portrait_first_then_switches(self):
        p=self.make([{'x':1,'y':2}],active='设置竖封面');dimension,digest=self.structural(p,{'landscape':(400,300),'portrait':(300,400)})
        with dimension,digest:p.covers()
        self.assertEqual([c.args[1] for c in p.b.fill_cover.call_args_list],['portrait','landscape'])
        p.b.semantic.assert_any_call('button','设置横封面')
        self.assertNotIn(('button','设置竖封面'),[c.args for c in p.b.semantic.call_args_list])

    def test_unknown_active_step_stops_before_upload(self):
        p=self.make([{'x':1,'y':2}],active='')
        with self.assertRaises(UIError):p.covers()
        p.b.fill_cover.assert_not_called()

    def test_requested_visual_review_stays_pending(self):
        p=self.make([{'x':1,'y':2}],{'cover_visual_required':True})
        self.assertEqual(p.covers()['visual_review'],'pending')
        self.assertEqual(p.j['cover_visual_review'],'pending')

    def test_mismatched_prepared_cover_ratio_stops(self):
        p=self.make([{'x':1,'y':2}]);dimension,digest=self.structural(p,{'landscape':(400,400),'portrait':(400,400)})
        with dimension,digest,self.assertRaises(UIError):p.covers()

    def test_ambiguous_cover_entry_stops_without_click(self):
        p=self.make([{'x':1,'y':2}]*3)
        with self.assertRaises(UIError):p.covers()
        p.b.point.assert_not_called();p.b.fill_cover.assert_not_called()


if __name__=='__main__':unittest.main()
