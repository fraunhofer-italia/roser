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
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Union

from ..utils import (
    ConfigurationException,
    FolderStructure,
    Paths,
    get_dict_value,
    to_absolute_path,
    removeprefix,
    get_flag,
    get_flag_value,
    LOGGER,
    args_to_dict,
    append_to_bash_file,
    split_line,
)
from .commons.arguments import Arguments, InvalidArgument
from .commons.commands import Command, Defaults
from .commons.volume import Volume


def complete_recursion(
    splitted: List[str],
    command: Command,
    command_flags: List[str] = [],
    command_args: List[str] = [],
    allow_undeclared: bool = False,
):
    def handle_slash(options: List[str], element: str):
        if not "/" in element:
            return options

        return [o.removeprefix(element[: element.rfind("/") + 1]) for o in options]

    if len(splitted) == 1 and splitted[0] == "":
        return command_flags + command_args

    # check flags
    if len(splitted) == 1:
        if splitted[0] == "-":
            return ["-"]
        if splitted[0].startswith("-"):
            if splitted[0] in command_flags:
                return [splitted[0].split("-")[-1]]
            else:
                return [
                    option.removeprefix("--")
                    for option in command_flags
                    if option.startswith(splitted[0])
                ]

    flag = get_flag(splitted[0], command.flags)
    if not flag is None:
        flag_options = command.get_flag_options(flag)
        if flag_options:
            if len(splitted) == 2:
                if splitted[1] == "":
                    return flag_options
                else:
                    result = [
                        option
                        for option in flag_options
                        if option.startswith(splitted[1])
                    ]
                    result = handle_slash(result, splitted[1])
                    return result
            if len(splitted) > 1:
                if splitted[1] in flag_options:
                    return complete_recursion(
                        splitted[2:], command, command_flags, command_args
                    )
        else:
            return complete_recursion(
                splitted[1:], command, command_flags, command_args
            )

    # check args
    if len(splitted) == 1:
        possibilities = [o for o in command_args if o.startswith(splitted[0])]
        if possibilities:
            if len(possibilities) == 1 and possibilities[0] in command_args:
                return [possibilities[0] + ":="]
            else:
                return possibilities
        if ":=" in splitted[0]:
            splitted_arg = splitted[0].split(":=")
            try:
                if len(splitted_arg) == 1:
                    return command.args[splitted_arg[0]].resolved_options
                else:
                    result = [
                        o
                        for o in command.args[splitted_arg[0]].resolved_options
                        if o.startswith(splitted_arg[1])
                    ]
                    result = handle_slash(result, splitted_arg[1])
                    if (
                        allow_undeclared
                        and command.args[splitted_arg[0]].allow_undeclared
                        and splitted_arg[1]
                    ):
                        result.append(splitted_arg[1])
                    return result
            except KeyError:
                pass
        if splitted[0].endswith(":"):
            return ["="]

    if len(splitted) > 1:
        if ":=" in splitted[0]:
            splitted_arg = splitted[0].split(":=")
            try:
                if not len(splitted_arg) == 1 and (
                    (not command.args[splitted_arg[0]].resolved_options)
                    or splitted_arg[1] in command.args[splitted_arg[0]].resolved_options
                ):
                    return complete_recursion(
                        splitted[1:], command, command_flags, command_args
                    )
            except KeyError:
                pass

    return None, splitted[0]


@dataclass
class Entity(ABC):
    name: str
    paths: Paths
    structure: FolderStructure = None
    commands: Dict[str, Command] = field(default_factory=dict)
    volumes: Dict[str, Volume] = field(default_factory=dict)
    source_folder: str = "src"

    @dataclass
    class Description(ABC):
        name: str
        paths: Paths
        structure: FolderStructure = None
        commands: Dict[str, Any] = field(default_factory=dict)
        volumes: Dict[str, Any] = field(default_factory=dict)
        source_folder: str = "src"

        @abstractmethod
        def from_dict(
            yaml_config_file: str, config_dict: Dict[str, Any]
        ) -> Entity.Description:
            pass

    def parse_volumes(entity_name: str, entity_path: str, volumes: Dict[str, Any]):
        result = {}
        for name, volume in volumes.items():
            context = f"{entity_name} (Volume {name})"
            type = get_dict_value(context, volume, "type", value_types=str)
            relative_destination = get_dict_value(
                context, volume, "destination", value_types=str, eval=True
            )
            if type in Volume.Type.possibilities():
                result[name] = Volume(
                    context=context,
                    name=name,
                    type=Volume.Type(type),
                    output=to_absolute_path(
                        os.path.join(entity_path, "docker"),
                        relative_destination,
                    ),
                )
            else:
                raise ConfigurationException(
                    context, f"the volume {type} does not exist"
                )

        return result

    def help(self):
        commands = {i: self.commands[i] for i in sorted(list(self.commands.keys()))}
        desired_length = max([len(c.name) for c in list(commands.values())])
        print()
        print("⏩ Commands ⏩")
        print("=" * 50)
        for name, command in commands.items():
            if not name in Defaults.COMMANDS_NAMES:
                print(
                    f"  \033[1;40m·\033[0m {command.name:<{desired_length}} -> {command.description}"
                )
        print()
        print("⏩ Default commands ⏩")
        print("=" * 50)
        for name, command in commands.items():
            if name in Defaults.COMMANDS_NAMES:
                print(
                    f"  \033[1;40m·\033[0m {command.name:<{desired_length}} -> {command.description}"
                )
        print()
        return

    def complete(
        self, text: str, line: str, begidx, endidx, allow_undeclared: bool = False
    ) -> List[str]:
        splitted = split_line(line)[1:]
        # Handle command name
        if not splitted or splitted[0].strip() == "":
            return list(self.commands.keys())

        command_name = splitted.pop(0)
        if not splitted:
            command_names = [
                cn for cn in self.commands.keys() if cn.startswith(command_name)
            ]
            return command_names

        command = self.commands[command_name]
        args_and_flags = splitted[:-1]
        for i in range(len(args_and_flags)):
            a_or_f = args_and_flags[i]
            if ":=" in a_or_f:
                args_and_flags[i] = a_or_f.split(":=")[0]

        command_flags = [
            flag_name[1]
            for flag_name in command.flags
            if not flag_name[1] in args_and_flags
        ]
        command_args = [
            arg_name
            for arg_name in command.args.keys()
            if not arg_name in args_and_flags
        ]

        return complete_recursion(
            splitted,
            command,
            command_flags,
            command_args,
            allow_undeclared=allow_undeclared,
        )

    def execute(self, text: str):
        try:
            args = text.split(" ")
            command_name = args.pop(0)

            user_flags = [arg for arg in args if arg.startswith("-")]
            for user_flag in user_flags:
                flag = get_flag(user_flag, self.commands[command_name].flags)
                if not flag is None:
                    options = self.commands[command_name].get_flag_options(flag)
                    value = get_flag_value(args, flag)
                    if (
                        not len(options) == 0
                        and not value in options
                        and not "" in options
                    ):
                        LOGGER.error(
                            f"Given flag {user_flag} requires one of the following options: \n {options}"
                        )
                        return
                    if (
                        len(options) == 0
                        and value is not None
                        and not value.startswith("-")
                    ):
                        LOGGER.error(
                            f"Given flag {user_flag} does not accept any options"
                        )
                        return
                else:
                    LOGGER.error(
                        f"Given flag '{user_flag}' does not exist. Available options are: '{self.commands[command_name].flags}'"
                    )
                    return

            save_path = self.commands[command_name].check_save_path(args)
            if not save_path is None:
                append_to_bash_file(
                    save_path,
                    [f"# Recording command {command_name} of entity {self.name}"],
                )
            self.commands[command_name].execute(args, Arguments(args_to_dict(args)))
            time.sleep(
                0.5
            )  # Sleep introduced to wait until command is executed before allowing next command
        except KeyError:
            LOGGER.error(f"Command `{text}` not found for entity {self.name}")
        except InvalidArgument as e:
            LOGGER.error(
                f"Unable to execute command `{text}` for entity {self.name}: {e}"
            )
            self.commands[command_name].kill()
        return
