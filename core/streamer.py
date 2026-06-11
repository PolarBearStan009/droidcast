import os
import shutil
import socket
import subprocess
import tempfile
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler

_VIEWER_HTML = '''<!DOCTYPE html>
<html>
<head>
  <title>Droidcast — Live</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{background:#0d0d0d;display:flex;flex-direction:column;align-items:center;
         justify-content:center;height:100vh;font-family:monospace;color:#888}
    video{max-height:92vh;max-width:100%;border:1px solid #2a2a2a}
    footer{margin-top:10px;font-size:11px;letter-spacing:.05em}
  </style>
</head>
<body>
  <video id="v" controls autoplay muted playsinline></video>
  <footer>DROIDCAST · LIVE MIRROR</footer>
  <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
  <script>
    var v = document.getElementById('v');
    function load(){
      if(Hls.isSupported()){
        var h=new Hls({lowLatencyMode:true,liveSyncDurationCount:2});
        h.loadSource('stream.m3u8'); h.attachMedia(v);
        h.on(Hls.Events.MANIFEST_PARSED,function(){v.play();});
        h.on(Hls.Events.ERROR,function(_,d){if(d.fatal)setTimeout(load,3000);});
      } else if(v.canPlayType('application/vnd.apple.mpegurl')){
        v.src='stream.m3u8';
      }
    }
    load();
  </script>
</body>
</html>'''


def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


class Streamer:
    def __init__(self):
        self._streaming = False
        self._http: HTTPServer | None = None
        self._adb_proc: subprocess.Popen | None = None
        self._ffmpeg_proc: subprocess.Popen | None = None
        self.stream_dir = ''
        self.port = 8888

    def start(self, serial: str, adb_path: str, ffmpeg_path: str,
              bitrate: int = 2_000_000, resolution: str = '720x1280',
              port: int = 8888) -> tuple:
        if self._streaming:
            return False, 'Already streaming'

        self.port = port
        self.stream_dir = tempfile.mkdtemp(prefix='droidcast_')
        self._streaming = True

        with open(os.path.join(self.stream_dir, 'index.html'), 'w') as f:
            f.write(_VIEWER_HTML)

        try:
            handler = partial(SimpleHTTPRequestHandler, directory=self.stream_dir)
            self._http = HTTPServer(('', port), handler)
        except OSError as e:
            self._streaming = False
            return False, f'Port {port} in use: {e}'

        threading.Thread(target=self._http.serve_forever, daemon=True).start()
        threading.Thread(target=self._pipeline,
                         args=(serial, adb_path, ffmpeg_path, bitrate, resolution),
                         daemon=True).start()

        ip = _local_ip()
        return True, f'http://{ip}:{port}'

    def _pipeline(self, serial, adb_path, ffmpeg_path, bitrate, resolution):
        m3u8 = os.path.join(self.stream_dir, 'stream.m3u8')
        while self._streaming:
            self._adb_proc = subprocess.Popen(
                [adb_path, '-s', serial, 'exec-out',
                 'screenrecord', '--output-format=h264',
                 f'--bit-rate={bitrate}', f'--size={resolution}', '-'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            self._ffmpeg_proc = subprocess.Popen(
                [ffmpeg_path, '-y', '-i', 'pipe:0',
                 '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency',
                 '-f', 'hls', '-hls_time', '2', '-hls_list_size', '5',
                 '-hls_flags', 'delete_segments', m3u8],
                stdin=self._adb_proc.stdout, stderr=subprocess.DEVNULL,
            )
            self._adb_proc.stdout.close()
            self._adb_proc.wait()
            self._ffmpeg_proc.wait()

    def stop(self) -> None:
        self._streaming = False
        for proc in (self._adb_proc, self._ffmpeg_proc):
            if proc:
                try:
                    proc.terminate()
                    proc.wait(timeout=2)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        if self._http:
            self._http.shutdown()
            self._http = None
        if self.stream_dir and os.path.isdir(self.stream_dir):
            shutil.rmtree(self.stream_dir, ignore_errors=True)
        self._adb_proc = None
        self._ffmpeg_proc = None

    def is_running(self) -> bool:
        return self._streaming
