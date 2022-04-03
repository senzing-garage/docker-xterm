#!/usr/bin/env python3

import argparse
import fcntl
from flask import Flask, request, render_template
from flask_socketio import SocketIO, join_room, leave_room, rooms
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
    "104": "Started background task. PID: {0} Running command: '{1}' On {2}",
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
app.config["sessions"] = dict()
socketio = SocketIO(app, path=socketio_path)


def set_window_size(file_descriptor, row, col, xpix=0, ypix=0):
    """
    Set the window size.
    """

    winsize = struct.pack("HHHH", row, col, xpix, ypix)
    fcntl.ioctl(file_descriptor, termios.TIOCSWINSZ, winsize)


def read_os_write_socketio(tty):
    """
    Read from file descriptor and send to pseudo-terminal.
    """

    session = app.config["sessions"].get(tty)

    max_read_bytes = 1024 * 20
    while True:
        socketio.sleep(0.01)
        if session and session["file_descriptor"]:
            timeout_sec = 0
            (data_ready, _, _) = select.select([session["file_descriptor"]], [], [], timeout_sec)
            if data_ready:
                try:
                    output = os.read(session["file_descriptor"], max_read_bytes).decode()

                except OSError:

                    # Something went wrong with the process.
                    # Retrieve whether and why it stopped and clean up, if necessary.

                    result = os.waitid(os.P_PID, session["child_pid"], os.WEXITED|os.WNOWAIT)
                    reason = None

                    # Convert si_code into readable name, as the os module defined it

                    for r in ("EXITED", "KILLED", "DUMPED", "TRAPPED", "STOPPED", "CONTINUED"):
                        if result.si_code == os.__getattribute__("CLD_"+r):
                            reason = r
                            break

                    if reason is None:
                        reason = "unknown"
                    elif reason in ("EXITED", "KILLED", "DUMPED"):

                        # The process has ended, but remains as a zombie
                        # until we read its return code.  Because os.wait()
                        # blocks until a child process exits, we first
                        # checked to make sure one was waiting for us.

                        os.wait()

                    #output = "Broken pipe: {}".format(result)
                    output = "Broken pipe: {}".format(reason)
                    logging.warn("Broken pipe: {} ({})".format(result, reason))
                    return

                finally:

                    # In any case, submit the output to the browser.

                    socketio.emit("pty-output", {"output": output}, to=tty, namespace="/pty")
                    session["last_line"] = (session["last_line"] + output).split("\n")[-1]

# -----------------------------------------------------------------------------
# Flask
# -----------------------------------------------------------------------------

non_canonical_route = static_url_path
if not non_canonical_route:
    non_canonical_route = non_canonical_route + "/"

@app.route(url_prefix)
# the above _should_ redirect a non-canonical URL to it's canonical version
# however, it doesn't seem to work.  So this:
@app.route(non_canonical_route)
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

    # rooms() automatically obtains client from request context.
    for room in rooms():
        session = app.config["sessions"].get(room)
        if session and check_pid(session["child_pid"]):
            os.write(session["file_descriptor"], data["input"].encode())


@socketio.on("resize", namespace="/pty")
def resize(data):
    """
    Account for window resize.
    """

    # rooms() automatically obtains client from request context.
    for room in rooms():
        session = app.config["sessions"].get(room)
        if session and check_pid(session["child_pid"]):
            set_window_size(session["file_descriptor"], data["rows"], data["cols"])


@socketio.on("request-tty", namespace="/pty")
def request_tty(data):
    """
    Request to be connected to a specific (or new) pseudo-terminal.
    """

    reattached = False

    if data["tty"] is not None:
        logging.info("Client requested tty {}".format(data["tty"]))
    else:
        logging.info("Client requested new tty")

    # rooms() automatically obtains client from request context.
    for room in rooms():
        if room in app.config["sessions"]:
            if data["tty"] is None and check_pid(app.config["sessions"][room]["child_pid"]):
                logging.info(message_info(103, app.config["sessions"][room]["child_pid"]))
                reattached = True
                logging.info("Client reattached to {}".format(room))
            else:
                leave_room(room)

    if reattached:
        return

    if data["tty"] is not None:
        session = app.config["sessions"].get(data["tty"])
        if session and check_pid(session["child_pid"]):
            output = "\r\n" + session["last_line"]
            socketio.emit("pty-output", {"output": output}, to=request.sid, namespace="/pty")
            join_room(data["tty"])
            socketio.emit("pty-connect", {"tty": data["tty"], "requestHonored": True}, to=request.sid, namespace="/pty")
            logging.info("Client attached to {}".format(data["tty"]))
            return

        else:
            output = "The requested tty {} is not active. Connecting to a new tty.\r\n".format(data["tty"])
            socketio.emit("pty-output", {"output": output}, to=request.sid, namespace="/pty")
            logging.info("Client couldn't be attached to {}".format(data["tty"]))
            #logging.info("Client couldn't be attached to {}\n  available ttys: {}\n  dead ttys: {}".format(
            #    data["tty"],
            #    list(map(lambda i: i[0], filter(lambda i: check_pid(i[1]["child_pid"]), app.config["sessions"].items()))),
            #    list(map(lambda i: i[0], filter(lambda i: not check_pid(i[1]["child_pid"]), app.config["sessions"].items())))))

    socketio.emit("pty-output", {"output": "\r\n"}, to=request.sid, namespace="/pty")

    cmd = app.config["cmd"]

    # Start a new Pseudo Terminal (PTY) to communicate with.
    # This thread will duplicate into two, with the same state but one "parent"
    # and one "child". The parent will be told the pid of the child, while the
    # child will be told 0. We replace our child python process with a new bash
    # process which uses the same pid and file descriptor.

    (child_pid, file_descriptor) = pty.fork()

    # If we are the child process after the fork, replace this process with the shell.

    if child_pid == 0:

        # Unfortunately, we have been given an invalid file descriptor, we can't do this:
        #tty = os.ttyname(file_descriptor)
        # Instead, we know the slave file descriptior as STDOUT.

        tty = os.ttyname(pty.STDOUT_FILENO)

        # We print our newly found out name to stdout so the parent process can pick it up.

        print(tty)

        # Now we can replace ourselves with the shell.

        executable = cmd[0]
        #os.fsync()
        os.execvp(executable, cmd)

    # If we are the parent process after the fork, remember the pid and
    # file descriptor and start forwarding data between it and socketio.

    else:

        # Read tty name that child process reports,

        tty = ''
        last = None
        while last != '\n':
            last = os.read(file_descriptor, 1).decode()
            if last not in [None, '\r', '\n']:
                tty += last

        if tty.startswith("/dev/"):
            tty = tty[len("/dev/"):]

        # If the tty is not an existing session, add it to our dictionary,
        # set an initial window size and start the background task.

        preexisting = tty in app.config["sessions"]
        app.config["sessions"][tty] = dict(child_pid=child_pid, file_descriptor=file_descriptor, cmd=cmd, last_line="")
        set_window_size(file_descriptor, 50, 50)

        if not preexisting:
            socketio.start_background_task(target=lambda: read_os_write_socketio(tty))

        join_room(tty)
        socketio.emit("pty-connect", {"tty": tty}, to=request.sid, namespace="/pty")
        cmd = " ".join(shlex.quote(cmd_arg) for cmd_arg in cmd)
        logging.info(message_info(104, child_pid, cmd, tty))

@socketio.on("connect", namespace="/pty")
def connect():
    """
    New client connection.
    """

    socketio.emit("pty-output", {"output": "\r\nWelcome to Senzing xterm!\r\n"}, to=request.sid, namespace="/pty")

    for room in rooms():
        if room in app.config["sessions"]:
            if child_pid(app.config["sessions"][room]["child_pid"]):
                logging.info(message_info(103, app.config["sessions"][room]["child_pid"]))
            else:
                leave_room(room)

    logging.info(message_info(103, None))

# -----------------------------------------------------------------------------
# Check if there is a process with a certain pid
# -----------------------------------------------------------------------------

def check_pid(pid):
    """
    Check For the existence of a unix pid.
    Also reports zombie processes, which already exited, but whose return code
    has yet to be read by the parent process (by calling os.wait() ) to vanish.
    """

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True

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
