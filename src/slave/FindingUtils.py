import threading
import time

import win32api
import win32con
import winsound

from src.core.utils import WindowsUtils


class FindingManager:
    def __init__(self):
        self.flag = True
        self.volume = 0.1

    def all(self, volume):
        self.sound(volume)
        self.video()

    def sound(self, volume):
        self.volume = volume
        self.flag = True
        threading.Thread(target=self._find_sound).start()

    def video(self):
        self.flag = True
        threading.Thread(target=self._find_video).start()

    def _find_sound(self):
        while self.flag:
            play_sound(self.volume)
            time.sleep(0.5)

    def _find_video(self):
        while self.flag:
            play_video()
            time.sleep(0.5)


def play_sound(volume):
    old_volume = WindowsUtils.get_volume()
    WindowsUtils.set_volume(volume)
    winsound.Beep(1320, 1000)
    WindowsUtils.set_volume(old_volume)


def play_video():
    win_key_code = 91
    win32api.keybd_event(win_key_code, 0, 0, 0)
    time.sleep(0.01)
    win32api.keybd_event(win_key_code, 0, win32con.KEYEVENTF_KEYUP, 0)
    time.sleep(1)
    win32api.keybd_event(win_key_code, 0, 0, 0)
    time.sleep(0.01)
    win32api.keybd_event(win_key_code, 0, win32con.KEYEVENTF_KEYUP, 0)
