#!/usr/bin/env python3
"""Read-only Kimi WebBridge entry check; does not attach or navigate tabs."""
import argparse,json,sys
from browser import Browser,UIError

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--endpoint',default='http://127.0.0.1:10086')
    ap.add_argument('--session',required=True)
    a=ap.parse_args()
    try:print(json.dumps(Browser(a.session,a.endpoint).preflight(),ensure_ascii=False));return 0
    except (UIError,OSError,ValueError) as e:
        print(json.dumps({'bridge':'not_ready','reason':str(e)},ensure_ascii=False));return 2
if __name__=='__main__':sys.exit(main())
