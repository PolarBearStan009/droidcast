import os
import platform
import subprocess


def open_path(path: str) -> None:
    system = platform.system()
    if system == 'Darwin':
        subprocess.Popen(['open', path])
    elif system == 'Windows':
        os.startfile(path)
    else:
        subprocess.Popen(['xdg-open', path])


def open_url(url: str) -> None:
    import webbrowser
    webbrowser.open(url)
