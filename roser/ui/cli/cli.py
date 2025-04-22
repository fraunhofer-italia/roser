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

from typing import IO, Dict, List, Type, Union, Tuple
from abc import ABC, abstractmethod
import cmd
import colorama

from ...roser import Roser
from ...utils import LOGGER
from .cli_command import CliCommand
from .backend import BACKEND

colorama.init()


class RoserCli(cmd.Cmd):
    commands: Dict[str, CliCommand]

    def __init__(
        self,
        cli_commands: List[Type[CliCommand]],
        completekey: str = "tab",
        stdin: IO[str] = None,
        stdout: IO[str] = None,
        prefix: str = "",
    ) -> None:
        super().__init__(completekey, stdin, stdout)
        try:
            rose_name = BACKEND.roser.rose.name
        except AttributeError:
            rose_name = "roser"
        if prefix:
            prefix = f"{colorama.Fore.YELLOW}{colorama.Style.BRIGHT}{prefix}{colorama.Style.RESET_ALL}:"
        self.prompt = f"\U0001F339 {prefix}{colorama.Fore.RED}{colorama.Style.BRIGHT}{rose_name}{colorama.Style.RESET_ALL} > "

        # BudCommands Cli registration
        self.commands = {}
        for c in cli_commands:
            command: CliCommand = c()
            if command.condition:
                setattr(RoserCli, f"do_{command.name}", command.execute)
                setattr(RoserCli, f"complete_{command.name}", command.complete)
                setattr(RoserCli, f"help_{command.name}", command.help)
                self.commands[command.name] = command

        # Rose/Petal Commands Cli registration
        for name, entity in BACKEND.roser.items.items():
            if name in self.commands.keys():
                LOGGER.error(
                    f"Entity name '{name}' already used by a Bud command. This entity will not be accessible via cli."
                )
                continue
            setattr(RoserCli, f"do_{name}", entity.execute)
            setattr(RoserCli, f"complete_{name}", entity.complete)
            setattr(RoserCli, f"help_{name}", entity.help)

    def emptyline(self):
        return

    def default(self, line):
        return

    def onecmd(self, line: str):
        # splits line
        inputs = [input for input in line.strip().split(" ") if input != ""]
        execute_line = " ".join(inputs)

        # Manages Ctrl + D and spaces on RoserBud
        if not inputs or inputs[0] == "EOF" or inputs[0] == "":
            if inputs and inputs[0] == "EOF":
                print()
            return True

        # Help command
        if inputs[0] == "help":
            return super().onecmd(execute_line)

        # Bud commands
        if inputs[0] in self.commands.keys():
            success, wrong_argument = RoserCli.check_complete_result(
                inputs,
                self.commands[inputs[0]].complete("", execute_line, "", ""),
            )
            if success:
                return super().onecmd(execute_line)
            else:
                LOGGER.error(
                    f"Failed to execute Bud command. Error: Command wrongly defined, no correct argument '{wrong_argument}'"
                )
                return False

        # Rose/Petals commands execution check
        if inputs[0] in BACKEND.roser.items.keys():
            entity = BACKEND.roser.items[inputs[0]]
            success, wrong_argument = RoserCli.check_complete_result(
                inputs, entity.complete("", execute_line, "", "", allow_undeclared=True)
            )
            if success:
                return super().onecmd(execute_line)
            else:
                LOGGER.error(
                    f"Failed to execute Entity command. Error: Command wrongly defined, no correct argument '{wrong_argument}'"
                )
                return False

        LOGGER.error(f"No command found with name '{inputs[0]}'")
        return False

    @staticmethod
    def check_complete_result(
        inputs: List[str], result: Union[Tuple[None, str], List[str]]
    ) -> Tuple[bool, str]:
        if isinstance(result, list):
            if not result:
                return True, ""
            else:
                string_check = inputs[-1]
                if inputs[-1].startswith("--"):
                    string_check = inputs[-1].removeprefix("--")
                if "=" in inputs[-1]:
                    string_check = inputs[-1].split("=")[-1]
                if "/" in inputs[-1]:
                    string_check1 = inputs[-1].split("/")[-1]
                    if (not "=" in inputs[-1]) or (
                        "=" in inputs[-1] and string_check.endswith(string_check1)
                    ):
                        string_check = string_check1
                if "-" in string_check:
                    string_check = string_check.split("-")[-1]
                if string_check in result:
                    return True, ""

        if isinstance(result, Tuple) and result[0] is None:
            return False, result[1]
        else:
            return False, inputs[-1]
