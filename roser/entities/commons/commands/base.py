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

import os
import re
import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Union

from ....ui import TMUX_HANDLER
from ....utils import (
    LOGGER,
    get_bash_command_flags,
    has_flag,
    get_flag_value,
    RoserGLB,
)
from ..arguments import JINJA_ENV, Argument, Arguments


class Defaults:
    COMMAND_DESCRIPTION: str = "default"
    COMMANDS_NAMES: List[str] = [
        "attach",
        "start",
        "stop",
    ]
    TMUX_SESSION_NAME: str = "roser/petals"


def parse_docker_compose_flags(
    args: List[str], docker_compose_command: str
) -> List[str]:
    if not ("-da" in args or "--docker-args" in args):
        return []

    additional_docker_flags = args[args.index("--docker-args") + 1 :]
    valid_docker_flags = get_bash_command_flags(docker_compose_command)
    docker_flags = []
    for docker_flag in additional_docker_flags:
        if not docker_flag in valid_docker_flags:
            LOGGER.warning(
                f"Invalid flag `{docker_flag}` passed to command `{docker_compose_command}`. "
                "Ignoring it."
            )
        else:
            docker_flags.append(docker_flag)
    return docker_flags


def check_arguments(
    search_arg: Union[str, List[str]], arg_defined: List[str], jinja: bool = True
):
    if isinstance(search_arg, str):
        search_arg = [search_arg]

    if jinja:
        args_specified_in_command = []
        for c in search_arg:
            args_specified_in_command += re.findall(
                r"\{\{ ([a-zA-Z_][a-zA-Z0-9_]*) \}\}", c
            )
    else:
        args_specified_in_command = search_arg

    missing_arguments = list(set(args_specified_in_command) - set(arg_defined))
    if missing_arguments:
        return False, f"Arguments wrongly defined: {missing_arguments}"

    missing_arguments = list(set(arg_defined) - set(args_specified_in_command))
    if missing_arguments:
        return True, f"Arguments not used: {missing_arguments}"

    return True, ""


def get_jinja_arguments(arguments: Arguments) -> Arguments:
    result = copy.deepcopy(arguments)
    to_delete = []
    for c in arguments.values():
        if not re.findall(r"\{\{ ([a-zA-Z_][a-zA-Z0-9_]*) \}\}", str(c)):
            to_delete += [c.name]
    result.delete(to_delete)
    return result


@dataclass
class Command(ABC):
    name: str
    description: str
    commands: List[str] = field(default_factory=list)
    args: Arguments = field(default_factory=dict)
    flags: List[Tuple[str, str]] = field(
        default_factory=lambda: [("-k", "--kill"), ("-s", "--save")]
    )
    sleep: float = 0.0
    condition: str = "True"

    def __post_init__(self):
        self.commands = (
            [self.commands] if isinstance(self.commands, str) else self.commands
        )

    @staticmethod
    def evaluate_condition(condition, args):
        try:
            if eval(JINJA_ENV.from_string(condition).render(args)):
                return True
        except BaseException as e:
            pass
        return False

    @abstractmethod
    def execute(self, args: List[str] = [], kwargs: Dict[str, Any] = {}):
        self.check_and_send_kill(args)
        self.check_save_path(args)
        return

    @abstractmethod
    def kill(self, save_path: str = None):
        pass

    def get_flag_options(self, flag: Tuple[str, str]) -> List[str]:
        if flag == ("-s", "--save"):
            return [""]
        return []

    def check_and_send_kill(self, args: List[str]) -> bool:
        if has_flag(args, ("-k", "--kill")):
            self.kill(self.check_save_path(args))
            return True
        return False

    def check_save_path(self, args: List[str]) -> str:
        path = None
        value = (
            RoserGLB.RECORD_SAVE_PATH
            if not has_flag(args, ("-s", "--save"))
            else get_flag_value(args, ("-s", "--save"))
        )
        if not value is None:
            if os.path.isfile(value) or os.path.isdir(os.path.dirname(value)):
                path = value
            else:
                LOGGER.error(
                    f"Unable to save command {self.name}: Path {value} does not exist"
                )
        return path


@dataclass
class EmptyCommand(Command):
    name: str = "empty"
    description: str = Defaults.COMMAND_DESCRIPTION

    def execute(self, args: List[str] = [], kwargs: Dict[str, Any] = {}):
        return super().execute()


@dataclass
class TMuxCommand(Command):
    entity_name: str = ""
    tmux_session_name: str = Defaults.TMUX_SESSION_NAME
    tmux_window_name: str = None

    def execute(self, args: List[str] = [], kwargs: Dict[str, Any] = {}):
        if self.check_and_send_kill(args):
            return

        self.commands = [f"sleep {self.sleep}; {c}" for c in self.commands]
        TMUX_HANDLER.sessions[self.tmux_session_name].launch_window(
            self.tmux_window_name, self.commands, save_path=self.check_save_path(args)
        )
        return

    def kill(self, save_path: str = None):
        TMUX_HANDLER.kill_window(
            self.tmux_session_name,
            self.tmux_window_name,
            save_path=save_path,
        )
        return
