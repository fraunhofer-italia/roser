#
# Copyright 2024 Fraunhofer Italia Research scarl.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Marco Magri <marco.magri@fraunhofer.it>
# Author: Carlo Morganti <carlo.morganti@fraunhofer.it>
#
import argparse
import os
import sys
import time

import libtmux

from .utils import SSHInfos, user_question, RoserENV
from .ui import TMUX_HANDLER


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--import",
        help="Allow to import a rose project",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "-is",
        "--import-stable",
        help="Allow to import stable version of a rose project",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "-c",
        "--command",
        help="Allow to specify a command to be directly exerted in roser",
        required=False,
    )
    parser.add_argument(
        "-a",
        "--attach",
        help="Allow to specify if attach to Roser Bud session on command execution",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--hidden",
        help="Starts roser in hidden mode. No terminal will be spawned.",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "-q",
        "--quit",
        help="Quits roser.",
        action="store_true",
        required=False,
    )
    parser.add_argument(
        "--prefix", type=str, help="Roser prefix", default="", required=False
    )
    parser.add_argument(
        "--terminal",
        type=str,
        help="Roser terminal provider",
        required=False,
    )
    parser.add_argument(
        "-b",
        "--branch",
        type=str,
        help="Allow to specify the Roser branch",
        required=False,
    )
    parser.add_argument(
        "-d",
        "--dir",
        help="Allow to select the directory in which roser is started.",
        default=RoserENV.DIRECTORY,
        type=str,
        required=False,
    )
    parser.add_argument(
        "-ov",
        "--override_volumes",
        help="Allow to select if volumes should be overridden without question.",
        action="store_true",
        required=False,
    )
    known_args, _ = parser.parse_known_args()
    known_args = vars(known_args)

    roserbud_session = None
    for session in TMUX_HANDLER.server.sessions:
        if session.name == "roser/bud":
            roserbud_session = session
            break

    if roserbud_session is None:
        if known_args["quit"] or known_args["command"]:
            print("No Roser Bud found.")
            return
        roserbud_session = TMUX_HANDLER.server.new_session(
            "roser/bud", window_name="roser/bud"
        )
        roserbud_session.windows[0].panes[0].send_keys(
            f"python3 -m roser.ui {' '.join(sys.argv[1:])}"
        )
        roserbud_session.set_option("mouse", "1")
    else:
        if known_args["quit"]:
            roserbud_session.windows[0].panes[0].send_keys("quit")
            return

        if known_args["command"]:
            roserbud_session.windows[0].panes[0].send_keys(known_args["command"])
            if not known_args["attach"]:
                return

        if known_args["branch"]:
            print("Existing Roser must be closed before starting a new one.")
            return

    try:
        TMUX_HANDLER.server.attach_session("roser/bud")
    except libtmux.exc.LibTmuxException:
        pass


if __name__ == "__main__":
    main()
