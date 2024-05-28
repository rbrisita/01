
import fcntl
import os
import platform
import sys
import termios
import threading
import time
import tty
from pynput import keyboard

class _raw(object):
    def __init__(self, stream):
        self.stream = stream
        self.fd = self.stream.fileno()
    def __enter__(self):
        self.original_stty = termios.tcgetattr(self.stream)
        tty.setcbreak(self.stream)
    def __exit__(self, type, value, traceback):
        print("raw exit")
        termios.tcsetattr(self.stream, termios.TCSANOW, self.original_stty)

class _nonblocking(object):
    def __init__(self, stream):
        self.stream = stream
        self.fd = self.stream.fileno()
    def __enter__(self):
        self.orig_fl = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, self.orig_fl | os.O_NONBLOCK)
    def __exit__(self, *args):
        print("nonblocking exit")
        fcntl.fcntl(self.fd, fcntl.F_SETFL, self.orig_fl)

# Get keyboard input to set and clear event
def kb_listener(on_press, on_release):
    print("on_press", on_press)
    print("on_release", on_release)

    pressed_keys = []
    current_key = None
    bytes_to_read = 1
    skipping = None

    with _raw(sys.stdin):
        with _nonblocking(sys.stdin):
            while True:
                c = sys.stdin.read(bytes_to_read)
                # print(f"{repr(c)}")

                if len(c):
                  c = c[-1] # get last character

                if c:
                    if c not in pressed_keys:
                      bytes_to_read = 1024
                      skipping = 5 # delay in x100ms keyboard auto repeat
                      current_key = c
                      pressed_keys.append(c)
                      on_press(c)
                elif skipping:
                    print(f"skipping {skipping}")
                    skipping -= 1
                elif not c and current_key:
                    bytes_to_read = 1
                    pressed_keys.remove(current_key)
                    on_release(current_key)
                    current_key = None

                time.sleep(0.1)
    print("KB Done")


def listen_keyboard(on_press, on_release):
    # if sys.platform == "Linux":
    if platform.system() == "Linux":
        kbl = threading.Thread(target=kb_listener, kwargs={"on_press": on_press, "on_release": on_release})
        # kbl.daemon = True
        kbl.start()
        return

    # Keyboard listener for spacebar press/release
    listener = keyboard.Listener(
        on_press=on_press, on_release=on_release
    )
    listener.start()
