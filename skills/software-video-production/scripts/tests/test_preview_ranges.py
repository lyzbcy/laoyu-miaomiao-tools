import functools,importlib.util,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
spec=importlib.util.spec_from_file_location('preview',Path(__file__).resolve().parents[1]/'serve_preview.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class RangeTests(unittest.TestCase):
 def test_ranges_match_real_bytes_and_boundaries(self):
  with tempfile.TemporaryDirectory() as td:
   data=bytes(range(256))*64;Path(td,'video.mp4').write_bytes(data);server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(mod.RangeHandler,directory=td));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();url=f'http://127.0.0.1:{server.server_port}/video.mp4'
   try:
    for header,start,end in [('bytes=7000-7999',7000,7999),('bytes=12000-',12000,len(data)-1),('bytes=-30',len(data)-30,len(data)-1)]:
     with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':header})) as response:
      self.assertEqual(response.status,206);self.assertEqual(response.headers['Accept-Ranges'],'bytes');self.assertEqual(response.headers['Content-Range'],f'bytes {start}-{end}/{len(data)}');self.assertEqual(response.read(),data[start:end+1])
    with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(urllib.request.Request(url,headers={'Range':'bytes=999999-'}))
    self.assertEqual(error.exception.code,416)
    with urllib.request.urlopen(urllib.request.Request(url,method='HEAD',headers={'Range':'bytes=4-8'})) as response:self.assertEqual(response.status,206);self.assertEqual(response.headers['Content-Length'],'5');self.assertEqual(response.read(),b'')
   finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
