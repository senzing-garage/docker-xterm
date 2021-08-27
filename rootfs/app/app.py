#!/usr/bin/env python3

import argparse
import fcntl
from flask import Flask, render_template
from flask_socketio import SocketIO
import logging
import os
import pty
import select
import shlex
import struct
import subprocess
import termios

__all__ = []
__version__ = "1.2.0"  # See https://www.python.org/dev/peps/pep-0396/
__date__ = '2020-04-26'
__updated__ = '2021-08-27'

SENZING_PRODUCT_ID = "5024"  # See https://github.com/Senzing/knowledge-base/blob/master/lists/senzing-product-ids.md
log_format = '%(asctime)s %(message)s'

# Pull OS environment variables

url_prefix = os.environ.get("SENZING_BASE_URL_XTERM", "/")
static_url_path = url_prefix[:-1]
socketio_path = "{0}socket.io".format(url_prefix[1:])
io_connect_path = "{0}socket.io".format(url_prefix)

# Initialize Flask instance and SocketIO instance.

app = Flask(__name__, static_folder=".", static_url_path=static_url_path)
app.config["SECRET_KEY"] = os.environ.get("SENZING_XTERM_SECRET", "senzing-xterm-secret!")
app.config["file_descriptor"] = None
app.config["child_pid"] = None
socketio = SocketIO(app, path=socketio_path)


def set_window_size(file_descriptor, row, col, xpix=0, ypix=0):
    """
    Set the window size.
    """

    winsize = struct.pack("HHHH", row, col, xpix, ypix)
    fcntl.ioctl(file_descriptor, termios.TIOCSWINSZ, winsize)


def read_os_write_socketio():
    """
    Read from file descriptor and send to pseudo-terminal.
    """

    max_read_bytes = 1024 * 20
    while True:
        socketio.sleep(0.01)
        if app.config["file_descriptor"]:
            timeout_sec = 0
            (data_ready, _, _) = select.select([app.config["file_descriptor"]], [], [], timeout_sec)
            if data_ready:
                output = os.read(app.config["file_descriptor"], max_read_bytes).decode()
                socketio.emit("pty-output", {"output": output}, namespace="/pty")

# -----------------------------------------------------------------------------
# Flask
# -----------------------------------------------------------------------------


@app.route(url_prefix)
def index():
    return render_template(
        "index.html",
        io_connect_path=io_connect_path
    )

# -----------------------------------------------------------------------------
# socketio
# -----------------------------------------------------------------------------


@socketio.on("pty-input", namespace="/pty")
def pty_input(data):
    """
    Write to the pseudo-terminal.
    """

    if app.config["file_descriptor"]:
        os.write(app.config["file_descriptor"], data["input"].encode())


@socketio.on("resize", namespace="/pty")
def resize(data):
    """
    Account for window resize.
    """

    if app.config["file_descriptor"]:
        set_window_size(app.config["file_descriptor"], data["rows"], data["cols"])


@socketio.on("connect", namespace="/pty")
def connect():
    """
    New client connection.
    """

    # If child process already running, don't start a new one.

    if app.config["child_pid"]:
        return

    # Start a new Pseudo Terminal (PTY) to communicate with.

    (child_pid, file_descriptor) = pty.fork()

    # If child process, all output sent to the pseudo-terminal.

    if child_pid == 0:
        subprocess.run(app.config["cmd"])

    # If parent process,

    else:
        app.config["file_descriptor"] = file_descriptor
        app.config["child_pid"] = child_pid
        set_window_size(file_descriptor, 50, 50)
        cmd = " ".join(shlex.quote(cmd_arg) for cmd_arg in app.config["cmd"])
        socketio.start_background_task(target=read_os_write_socketio)
        print("Started background task (pid: {0}) running command: '{1}'".format(child_pid, cmd))

# -----------------------------------------------------------------------------
# Define argument parser
# -----------------------------------------------------------------------------


def get_parser():
    ''' Parse commandline arguments. '''

    arguments = {
        "--cmd-args": {
            "default": "",
            "dest": "cmd_args",
            "metavar": "SENZING_COMMAND_ARGS",
            "help": "Command line arguments. Default: None"
        },
        "--command": {
            "default": "bash",
            "dest": "command",
            "metavar": "SENZING_COMMAND",
            "help": "Command to run in terminal. Default: None"
        },
        "--debug": {
            "dest": "debug",
            "action": "store_true",
            "help": "Enable debugging. Default: False"
        },
        "--host": {
            "default": "0.0.0.0",
            "dest": "host",
            "metavar": "SENZING_HOST",
            "help": "Server listens to this host. Default: 0.0.0.0"
        },
        "--port": {
            "default": 5000,
            "dest": "port",
            "metavar": "SENZING_PORT",
            "help": "Server listens on this port. Default: 5000"
        },
    }

    parser = argparse.ArgumentParser(
        prog="xterm",
        description="Web-based X-terminal. For more information, see https://github.com/Senzing/docker-xterm",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    for argument_key, argument_values in arguments.items():
        parser.add_argument(argument_key, **argument_values)

    return parser

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def main():

    log_level_map = {
        "notset": logging.NOTSET,
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "fatal": logging.FATAL,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }

    log_level_parameter = os.getenv("SENZING_LOG_LEVEL", "info").lower()
    log_level = log_level_map.get(log_level_parameter, logging.INFO)
    logging.basicConfig(format=log_format, level=log_level)

    # Parse input.

    args = get_parser().parse_args()

    # Start listening.

    logging.info("senzing-{0}0001I Senzing X-term version: {1} updated: {2}".format(SENZING_PRODUCT_ID, __version__, __updated__))
    logging.info("senzing-{0}0002I Senzing X-term serving on http://{1}:{2}".format(SENZING_PRODUCT_ID, args.host, args.port))

    app.config["cmd"] = [args.command] + shlex.split(args.cmd_args)
    socketio.run(app, debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
