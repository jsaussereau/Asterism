#**********************************************************************#
#                               Asterism                               #
#**********************************************************************#
#
# Copyright (C) 2022 Jonathan Saussereau
#
# This file is part of Asterism.
# Asterism is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Asterism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Asterism. If not, see <https://www.gnu.org/licenses/>.
#

import os
import sys
import webbrowser
from threading import Thread
import tty
import termios
import result_explorer
import select
import socket

# Add local libs to path
current_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.join(current_dir, 'lib')
sys.path.append(lib_path)

import printc

# Default ip address: local
host_address = '127.0.0.1'
ip_address = host_address
port = 8052
network = False

def open_browser():
    webbrowser.open(ip_address + ':' + str(port), new=0, autoraise=True)

def close_server():
    restore_mode(old_settings)
    print('\r')
    os._exit(0)

def set_raw_mode():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(fd)
    return old_settings

def restore_mode(old_settings):
    fd = sys.stdin.fileno()
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

if __name__ == "__main__":
    from waitress import serve
    from flask import request

    # Check options
    if "-n" in sys.argv or "--network" in sys.argv:
        network = True

    if network:
        host_address = '0.0.0.0'
        ip_address = socket.gethostbyname(socket.gethostname())

    print("result explorer server running on " + printc.colors.BLUE + "http://" + ip_address + ":" + str(port) + '/' + printc.colors.ENDC, end="")
    if network:
        print(" (network-accessible)")
    else:
        print(" (localhost only)")
    print("press 'q' to quit")

    # Open the web page
    process = Thread(target=open_browser).start()

    # Start the server
    serve_thread = Thread(target=serve, args=(result_explorer.app.server,), kwargs={'host': host_address, 'port': port})
    serve_thread.start()

    old_settings = set_raw_mode()
    try:
        while True:
            # Check if a key is pressed
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                key = sys.stdin.read(1).lower()
                if key == 'q':
                    close_server()
    finally:
        restore_mode(old_settings)
