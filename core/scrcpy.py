import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ScrcpyConfig:
    max_size: int = 1080
    bit_rate: str = '8M'
    max_fps: int = 60
    turn_screen_off: bool = False
    show_touches: bool = False
    stay_awake: bool = True
    always_on_top: bool = False
    record_path: str = ''


class ScrcpyManager:
    def __init__(self, path: str = ''):
        self.path = path or shutil.which('scrcpy') or 'scrcpy'
        self._process: Optional[subprocess.Popen] = None

    def available(self) -> bool:
        try:
            r = subprocess.run([self.path, '--version'], capture_output=True, timeout=5)
            return r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def launch(self, serial: str, config: ScrcpyConfig) -> tuple:
        if self.is_running():
            return False, 'Already running'

        cmd = [
            self.path,
            '-s', serial,
            '--max-size', str(config.max_size),
            '--video-bit-rate', config.bit_rate,
            '--max-fps', str(config.max_fps),
            '--window-title', f'Droidcast — {serial}',
        ]

        if config.turn_screen_off:
            cmd.append('--turn-screen-off')
        if config.show_touches:
            cmd.append('--show-touches')
        if config.stay_awake:
            cmd.append('--stay-awake')
        if config.always_on_top:
            cmd.append('--always-on-top')
        if config.record_path:
            cmd += ['--record', config.record_path]

        try:
            self._process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, ''
        except FileNotFoundError:
            return False, f'scrcpy not found at: {self.path}'

    def stop(self) -> None:
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

    def poll(self) -> Optional[int]:
        if self._process:
            return self._process.poll()
        return None

    @staticmethod
    def make_record_path(folder: str) -> str:
        os.makedirs(folder, exist_ok=True)
        ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        return os.path.join(folder, f'droidcast_{ts}.mp4')
