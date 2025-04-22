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
from __future__ import annotations

import argparse
import os
import sys

from ..roser import Roser
from ..utils import LOGGER, ConfigurationException, RoserENV
from .cli import BACKEND, RoserCli
from .cli.bud_commands import BUD_COMMANDS
from .header import show_header
from .tmux_handler import TMUX_HANDLER

if __name__ == "__main__":
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
        "--hidden",
        help="Starts roser in hidden mode. No terminal will be spawned.",
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
        default="",
        help="Allow to specify the Roser branch",
        required=False,
    )
    parser.add_argument(
        "-ov",
        "--override_volumes",
        help="Allow to select if volumes should be overridden without question.",
        action="store_true",
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
    known_args, _ = parser.parse_known_args()
    args = vars(known_args)

    RoserENV.OVERRIDE_VOLUMES = args["override_volumes"] or RoserENV.OVERRIDE_VOLUMES
    RoserENV.TERMINAL_PROVIDER = args["terminal"]
    RoserENV.DIRECTORY = args["dir"]
    RoserENV.BRANCH = args["branch"]
    TMUX_HANDLER.hidden_mode = args["hidden"]
    show_header()
    try:
        roser = Roser(
            import_rose=args["import"] or args["import_stable"],
            import_stable=args["import_stable"],
            path=RoserENV.DIRECTORY,
            branch=RoserENV.BRANCH,
        )
    except ConfigurationException as e:
        LOGGER.error(e.message)
        LOGGER.error("Closing Roser ...")
        sys.exit(0)

    BACKEND.roser = roser
    cli = RoserCli(BUD_COMMANDS, prefix=args["prefix"])

    while True:
        try:
            cli.cmdloop()
        except KeyboardInterrupt:
            print()
