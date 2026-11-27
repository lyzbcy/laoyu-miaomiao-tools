import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:
    import prepare_image_flow as flow
except ImportError:  # Pillow is optional for the rest of the skill
    flow=None

@unittest.skipUnless(flow,'Pillow needed')
class ImageFlow(unittest.TestCase):
    def test_header_comes_from_plan_never_hardcoded(self):
        card={'title':'Title','subtitle':'Sub','lines':['Point']}
        with patch.object(flow,'drawtext') as draw:
            draw.side_effect=lambda d,xy,s,size,color=flow.WHITE,bold=False,width=940:xy[1]+40
            flow.make_card(dict(card),Path('.'),None,1,1,{'kicker':'Author / Topic'})
            self.assertEqual(draw.call_args_list[0].args[2],'Author / Topic')
            draw.reset_mock()
            flow.make_card(dict(card),Path('.'),None,1,1,{})
            self.assertEqual([c.args[2] for c in draw.call_args_list],['Title','Sub','Point','01 / 01   ·   来自最终成片'])

if __name__=='__main__':unittest.main()
