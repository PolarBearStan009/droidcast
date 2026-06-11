import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class Device:
    serial: str
    state: str
    model: str = ''


class ADB:
    def __init__(self, path: str = ''):
        self.path = path or shutil.which('adb') or 'adb'

    def available(self) -> bool:
        code, _, _ = self._run('version')
        return code == 0

    def _run(self, *args, device: Optional[str] = None, timeout: int = 10):
        cmd = [self.path]
        if device:
            cmd += ['-s', device]
        cmd += list(args)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return r.returncode, r.stdout.strip(), r.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, '', 'timeout'
        except FileNotFoundError:
            return -1, '', f'adb not found at: {self.path}'

    def _run_binary(self, *args, device: Optional[str] = None, timeout: int = 30):
        cmd = [self.path]
        if device:
            cmd += ['-s', device]
        cmd += list(args)
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=timeout)
            return r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired:
            return -1, b'', b'timeout'
        except FileNotFoundError:
            return -1, b'', f'not found: {self.path}'.encode()

    def devices(self) -> list:
        _, out, _ = self._run('devices', '-l')
        result = []
        for line in out.split('\n')[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial, state = parts[0], parts[1]
            model = next(
                (p.split(':', 1)[1].replace('_', ' ') for p in parts[2:] if p.startswith('model:')),
                serial,
            )
            result.append(Device(serial=serial, state=state, model=model))
        return result

    def device_info(self, serial: str) -> dict:
        _, model, _ = self._run('shell', 'getprop', 'ro.product.model', device=serial)
        _, version, _ = self._run('shell', 'getprop', 'ro.build.version.release', device=serial)
        _, battery_raw, _ = self._run('shell', 'dumpsys', 'battery', device=serial)
        _, res_raw, _ = self._run('shell', 'wm', 'size', device=serial)

        battery = -1
        for line in battery_raw.split('\n'):
            if 'level:' in line:
                try:
                    battery = int(line.split(':')[1].strip())
                except ValueError:
                    pass
                break

        resolution = ''
        if 'Physical size:' in res_raw:
            resolution = res_raw.split('Physical size:')[-1].strip().split('\n')[0].strip()

        return {
            'model': model.strip() or serial,
            'android': version.strip(),
            'battery': battery,
            'resolution': resolution,
        }

    def screenshot(self, serial: str, output_path: str) -> bool:
        _, data, _ = self._run_binary('exec-out', 'screencap', '-p', device=serial, timeout=20)
        if data:
            with open(output_path, 'wb') as f:
                f.write(data)
            return True
        return False

    def keyevent(self, serial: str, keycode: str) -> None:
        self._run('shell', 'input', 'keyevent', keycode, device=serial)

    def push(self, serial: str, local: str, remote: str) -> tuple:
        code, out, err = self._run('push', local, remote, device=serial, timeout=120)
        return code == 0, out or err

    def pull(self, serial: str, remote: str, local: str) -> tuple:
        code, out, err = self._run('pull', remote, local, device=serial, timeout=120)
        return code == 0, out or err

    def list_dir(self, serial: str, path: str) -> list:
        _, out, _ = self._run('shell', f'ls -la "{path}"', device=serial)
        entries = []
        for line in out.split('\n'):
            line = line.strip()
            if not line or line.startswith('total'):
                continue
            parts = line.split(None, 8)
            if len(parts) < 8:
                continue
            perms = parts[0]
            raw_name = parts[-1]
            # Strip symlink target (name -> target)
            name = raw_name.split('->')[0].strip() if '->' in raw_name else raw_name
            # Drop entries that are absolute paths or empty (e.g. ls reporting the dir itself)
            if not name or name in ('.', '..') or name.startswith('/'):
                continue
            try:
                size = int(parts[4])
            except (ValueError, IndexError):
                size = 0
            is_dir = perms.startswith('d') or perms.startswith('l')
            entries.append({'name': name, 'is_dir': is_dir, 'size': size})
        return sorted(entries, key=lambda x: (not x['is_dir'], x['name'].lower()))

    def delete(self, serial: str, path: str) -> bool:
        code, _, _ = self._run('shell', f'rm -rf "{path}"', device=serial)
        return code == 0

    def wifi_enable(self, serial: str, port: int = 5555) -> bool:
        code, _, _ = self._run('tcpip', str(port), device=serial)
        return code == 0

    def wifi_ip(self, serial: str) -> Optional[str]:
        _, out, _ = self._run('shell', 'ip', '-f', 'inet', 'addr', 'show', 'wlan0', device=serial)
        m = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', out)
        return m.group(1) if m else None

    def wifi_connect(self, ip: str, port: int = 5555) -> tuple:
        code, out, err = self._run('connect', f'{ip}:{port}', timeout=15)
        msg = out or err
        return code == 0 and 'connected' in msg.lower(), msg

    def push_clipboard(self, serial: str, text: str) -> None:
        safe = text.replace("'", "'\\''")
        self._run('shell', f"am broadcast -a clipper.set -e text '{safe}'", device=serial)
