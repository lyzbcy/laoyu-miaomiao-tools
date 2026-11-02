"""Local preview server with byte ranges for real video scrubbing."""
import argparse, functools, os, re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

class RangeHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        self.byte_range=None
        path=self.translate_path(self.path)
        if not os.path.isfile(path):return super().send_head()
        f=open(path,'rb');st=os.fstat(f.fileno());size=st.st_size
        header=self.headers.get('Range')
        if header:
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',header.strip())
            valid=bool(match and any(match.groups()))
            if valid:
                first,last=match.groups()
                if not first:
                    count=int(last);valid=count>0;start=max(0,size-count);end=size-1
                else:start=int(first);end=min(int(last),size-1) if last else size-1
                valid=valid and 0<=start<=end<size
            if not valid:
                f.close();self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers();return None
            self.byte_range=(start,end);f.seek(start);self.send_response(206)
            self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
            length=end-start+1
        else:self.send_response(200);length=size
        self.send_header('Content-Type',self.guess_type(path));self.send_header('Content-Length',str(length));self.send_header('Accept-Ranges','bytes');self.send_header('Last-Modified',self.date_time_string(st.st_mtime));self.end_headers();return f

    def copyfile(self,source,outputfile):
        if self.byte_range is None:return super().copyfile(source,outputfile)
        remaining=self.byte_range[1]-self.byte_range[0]+1
        try:
            while remaining:
                chunk=source.read(min(1024*1024,remaining))
                if not chunk:break
                outputfile.write(chunk);remaining-=len(chunk)
        except (BrokenPipeError,ConnectionResetError):pass

    def log_message(self,*args):pass

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',required=True);a.add_argument('--port',type=int,default=8891);a.add_argument('--bind',default='127.0.0.1');v=a.parse_args()
    ThreadingHTTPServer((v.bind,v.port),functools.partial(RangeHandler,directory=v.directory)).serve_forever()
