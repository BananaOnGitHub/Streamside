"""Apple-only HTTP integration. Linux skips explicitly, not claimed as passing."""
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import platform
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import unittest

ROOT=Path(__file__).resolve().parent.parent

@unittest.skipUnless(platform.system()=='Darwin' and shutil.which('xcrun'), 'requires Apple Foundation and Xcode command-line tools')
class FoundationCacheTests(unittest.TestCase):
    def test_actual_http_cache_hit_under_eight_stalled_transfers_and_304(self):
        requests=Counter();guard=threading.Lock()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass  # no URL/header logs
            def do_GET(self):
                with guard: requests[self.path]+=1
                if self.path.startswith('/blocked'): time.sleep(4)
                conditional=self.path=='/revalidate.gif' and self.headers.get('If-None-Match')=='"fixture-v1"'
                with guard: requests['conditional-304']+=bool(conditional)
                self.send_response(304 if conditional else 200)
                self.send_header('Cache-Control','max-age=0, must-revalidate' if self.path=='/revalidate.gif' else 'public, max-age=3600')
                self.send_header('ETag','"fixture-v1"');self.send_header('Content-Type','image/gif')
                self.send_header('Content-Length','0' if conditional else '6');self.end_headers()
                if not conditional:self.wfile.write(b'GIF89a')
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            source=(ROOT/'src/Streamside.c').read_text()
            lifecycle=source[source.index('/* Callback delivery and stopLoading'):source.index('static id protocol_canonical_request')]
            with tempfile.TemporaryDirectory() as folder:
                harness=Path(folder)/'foundation.m';binary=Path(folder)/'foundation'
                harness.write_text((ROOT/'tests/native/foundation_cache_prefix.m').read_text()+lifecycle+(ROOT/'tests/native/foundation_cache_main.m').read_text())
                built=subprocess.run(['xcrun','clang','-fblocks','-Wall','-Wextra','-Werror','-DTAS_IMAGE_DEMAND_DIAGNOSTIC=0','-I',str(ROOT/'src'),str(harness),'-framework','Foundation','-o',str(binary)],capture_output=True,text=True)
                self.assertEqual(built.returncode,0,built.stderr)
                ran=subprocess.run([binary,f'http://127.0.0.1:{server.server_port}'],capture_output=True,text=True,timeout=45)
                self.assertEqual(ran.returncode,0,ran.stderr)
                self.assertIn('Cache-hit admission-to-delivery',ran.stdout)
            self.assertEqual(requests['/hot.gif'],1)
            self.assertEqual(requests['conditional-304'],1)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=2)
