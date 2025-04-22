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

from typing import List
import os

from .bud_command import BudCommand, complete_recursion
from ....utils import (
    LOGGER,
    RoserGLB,
    append_to_bash_file,
    split_line,
)


class RecordBudCommand(BudCommand):
    # @property
    # def flags(self):
    #     return [
    #         ("-p", "--path"),
    #     ]

    def execute(self, text: str):
        args = text.split(" ")
        if len(args) < 1 or (args[0] not in ["start", "stop"]):
            LOGGER.error("Record command requires 'start' or 'stop' options")
            return
        if args[0] == "stop":
            if not RoserGLB.RECORD_SAVE_PATH is None and os.path.isfile(
                RoserGLB.RECORD_SAVE_PATH
            ):
                append_to_bash_file(
                    RoserGLB.RECORD_SAVE_PATH,
                    [
                        "#########################",
                        "# Roser Stop Recording  #",
                        "#########################",
                    ],
                )
            RoserGLB.RECORD_SAVE_PATH = None
        elif args[0] == "start":
            if len(args) > 1:
                if (
                    os.path.isfile(args[1])
                    or not os.path.isdir(args[1])
                    and os.path.isdir(os.path.dirname(args[1]))
                ):
                    if append_to_bash_file(
                        args[1],
                        [
                            "#########################",
                            "# Roser Start Recording #",
                            "#########################",
                        ],
                    ):
                        RoserGLB.RECORD_SAVE_PATH = args[1]
                    return
            LOGGER.error("Record 'start' requires a path to a file")
        return

    def complete(self, text, line, begidx, endidx) -> List[str]:
        return complete_recursion(split_line(line)[1:], ["start", "stop"], [])

    def help(self):
        LOGGER.info("Save the Roser commands in a file")
