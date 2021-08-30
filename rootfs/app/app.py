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
import sys
import termios

__all__ = []
__version__ = "1.2.0"  # See https://www.python.org/dev/peps/pep-0396/
__date__ = '2020-04-26'
__updated__ = '2021-08-30'

SENZING_PRODUCT_ID = "5024"  # See https://github.com/Senzing/knowledge-base/blob/master/lists/senzing-product-ids.md
log_format = '%(asctime)s %(message)s'

# -----------------------------------------------------------------------------
# Message handling
# -----------------------------------------------------------------------------

# 1xx Informational (i.e. logging.info())
# 3xx Warning (i.e. logging.warning())
# 5xx User configuration issues (either logging.warning() or logging.err() for Client errors)
# 7xx Internal error (i.e. logging.error for Server errors)
# 9xx Debugging (i.e. logging.debug())

MESSAGE_INFO = 100
MESSAGE_WARN = 300
MESSAGE_ERROR = 700
MESSAGE_DEBUG = 900

message_dictionary = {
    "100": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}I",
    "101": "Senzing X-term version: {0} updated: {1}",
    "102": "Senzing X-term serving on http://{0}:{1}",
    "103": "Connected. PID: {0}",
    "104": "Started background task. PID: {0} Running command: '{1}'",
    "297": "Enter {0}",
    "298": "Exit {0}",
    "299": "{0}",
    "300": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}W",
    "499": "{0}",
    "500": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}E",
    "699": "{0}",
    "700": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}E",
    "899": "{0}",
    "900": "senzing-" + SENZING_PRODUCT_ID + "{0:04d}D",
    "999": "{0}",
}


def message(index, *args):
    index_string = str(index)
    template = message_dictionary.get(index_string, "No message for index {0}.".format(index_string))
    return template.format(*args)


def message_generic(generic_index, index, *args):
    return "{0} {1}".format(message(generic_index, index), message(index, *args))


def message_info(index, *args):
    return message_generic(MESSAGE_INFO, index, *args)


def message_warning(index, *args):
    return message_generic(MESSAGE_WARN, index, *args)


def message_error(index, *args):
    return message_generic(MESSAGE_ERROR, index, *args)


def message_debug(index, *args):
    return message_generic(MESSAGE_DEBUG, index, *args)

# -----------------------------------------------------------------------------
# Initialize environment
# -----------------------------------------------------------------------------

# Pull OS environment variables.


url_prefix = os.environ.get("SENZING_BASE_URL_XTERM", "/")
xterm_secret = os.environ.get("SENZING_XTERM_SECRET", "senzing-xterm-secret!")

# Synthesize variables.

static_url_path = url_prefix[:-1]
socketio_path = "{0}socket.io".format(url_prefix[1:])
io_connect_path = "{0}socket.io".format(url_prefix)

# Initialize Flask instance and SocketIO instance.

app = Flask(__name__, static_folder=".", static_url_path=static_url_path)
app.config["SECRET_KEY"] = xterm_secret
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

    logging.info(message_info(103, app.config["child_pid"]))

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
        logging.info(message_info(104, child_pid, cmd))

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

    # Configure logging.

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

    logging.info(message_info(101, __version__, __updated__))
    logging.info(message_info(102, args.host, args.port))

    app.config["cmd"] = [args.command] + shlex.split(args.cmd_args)
    socketio.run(app, debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
