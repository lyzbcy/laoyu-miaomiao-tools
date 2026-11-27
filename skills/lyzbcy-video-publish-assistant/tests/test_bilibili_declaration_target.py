import sys, unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from browser import Browser, UIError

class DeclarationTarget(unittest.TestCase):
    def test_menu_item_types_and_exact_match(self):
        b=Browser('offline'); b.js=Mock(return_value={'x':1,'y':2})
        b.target(text='AI generated content')
        code=b.js.call_args.args[0]
        for token in ('li,label','[role=menuitem]','[role=menuitemradio]','===cfg.text','getBoundingClientRect','es.length!==1'):
            self.assertIn(token,code)
    def test_wait_retries_only_missing_control(self):
        b=Browser('offline'); b.target=Mock(side_effect=[UIError('Ambiguous/missing UI target {"count":0}'),{'x':1,'y':2}]); b.wait=Mock(side_effect=lambda fn,**kw:fn() or fn())
        self.assertEqual(b.wait_target(text='AI generated content'),{'x':1,'y':2})
    def test_ambiguous_control_does_not_retry(self):
        b=Browser('offline'); b.target=Mock(side_effect=UIError('Ambiguous/missing UI target {"count":2}')); b.wait=Mock(side_effect=lambda fn,**kw:fn())
        with self.assertRaises(UIError):b.wait_target(text='AI generated content')
        b.target.assert_called_once()
