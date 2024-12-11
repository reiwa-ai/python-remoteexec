import argparse
import sys, os, subprocess
from typing import List, Dict, Tuple, Union, Callable, Optional
import types
import socket
import json
import time
import queue
import ctypes
import threading
from remoteexec import *
from remoteexec.remoteexec import SnippetRunnerLocal
from remoteexec.hooks import *
from remoteexec.communicate import *
from remoteexec.communicate.serializer import loads, dumps
from remoteexec.communicate.sync import *
from remoteexec.communicate.exceptions import *
from remoteexec.inout import *

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--sync_frequency', type=float, default=5)
    parser.add_argument('--listen_port', type=int, default=9165)
    parser.add_argument('--listen_addr', type=str, default='')
    parser.add_argument('--debug_mode', action='store_true')

    args = parser.parse_args()

    if args.listen_port > 0 and args.listen_addr != '':
        fpS = SocketIO(listen_port=args.listen_port, listen_addr=args.listen_addr)
    else:
        fpS = ConsoleIO(sys.stdout, sys.stdin)
    reciever = SocketReciever()
    server = Communicator(connection=fpS, sync_frequency=args.sync_frequency, use_compress=not args.debug_mode)
    try:
        server.host(reciever=reciever)
    except Exception as e:
        try:
            server._send({'cmd':'exception', 'message':f'{str(type(e).__name__)}({str(e)})'})
        except Exception as e:
            pass
        try:
            fpS.close()
        except Exception as e:
            pass

    