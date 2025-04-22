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

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Union

from ....ui import TMUX_HANDLER
from ....utils import (
    LOGGER,
    ConfigurationException,
    run_subprocess,
    has_flag,
    get_flag_value,
    get_dict_value,
    Paths,
)
from ..arguments import JINJA_ENV, Arguments, InvalidArgument
from .base import Command, Defaults, TMuxCommand, check_arguments, get_jinja_arguments
from .entity import EntityCommand
from .default import StartCommand, StopCommand, BuildCommand, AttachCommand


@dataclass
class CollectionCommand(Command):
    entity_name: str = ""
    commands_and_args: Dict[
        str,
        Tuple[
            Union[EntityCommand, StartCommand, StopCommand, BuildCommand],
            Arguments,
        ],
    ] = field(default_factory=dict)
    new_session: bool = True

    def __post_init__(self):
        self.flags += [("-h", "--hide")]
        if self.new_session:
            self.flags += [("-sc", "--sub-command")]
            for subcommand_name, (command, _) in self.commands_and_args.items():
                command.tmux_window_name = subcommand_name
                command.tmux_session_name = f"{self.entity_name}/{self.name}"

    def get_dependencies(
        dictionary: Dict[str, Any],
        context: str,
        entity_names_filters: List[str] = None,
    ):
        subcommands = get_dict_value(
            context=context,
            dictionary=dictionary,
            key="commands",
            value_types=[list, dict],
            default={},
        )
        if not subcommands:
            return []
        dependencies = []
        for subcommand in (
            subcommands.values() if isinstance(subcommands, dict) else subcommands
        ):
            petal = get_dict_value(
                context=context,
                dictionary=subcommand,
                key="petal",
                value_types=str,
            )
            command = get_dict_value(
                context=context,
                dictionary=subcommand,
                key="command",
                value_types=str,
            )
            if entity_names_filters is None or petal in entity_names_filters:
                dependencies.append((petal, command))
        return dependencies

    def parse(
        name: str,
        entity_name: str,
        dictionary: Dict[str, Any],
        paths: Paths,
        defined_subcommands,
    ) -> CollectionCommand:
        context = f"{entity_name} (Command {name})"
        description = get_dict_value(
            context=context,
            dictionary=dictionary,
            key="description",
            default=Defaults.COMMAND_DESCRIPTION,
            value_types=str,
        )
        subcommands = get_dict_value(
            context=context,
            dictionary=dictionary,
            key="commands",
            value_types=[list, dict],
        )
        rose_command_args = Arguments(
            get_dict_value(
                context=context,
                dictionary=dictionary,
                key="args",
                default={},
                value_types=dict,
            ),
            paths.roser,
        )
        if isinstance(subcommands, list):
            subcommands_dict = {}
            for subcommand in subcommands:
                petal_name = get_dict_value(
                    context=context,
                    dictionary=subcommand,
                    key="petal",
                    value_types=str,
                )
                command_name = get_dict_value(
                    context=context,
                    dictionary=subcommand,
                    key="command",
                    value_types=str,
                )
                subcommand_name = f"{petal_name}/{command_name}"
                i = 1
                while subcommand_name in subcommands_dict:
                    subcommand_name = subcommand_name + f"_{i}"
                    i += 1
                subcommands_dict[subcommand_name] = subcommand
            subcommands = subcommands_dict

        commands_and_args = {}
        for subcommand_name, subcommand in subcommands.items():
            petal_name = get_dict_value(
                context=context,
                dictionary=subcommand,
                key="petal",
                value_types=str,
            )
            command_name = get_dict_value(
                context=context,
                dictionary=subcommand,
                key="command",
                value_types=str,
            )
            command_args = Arguments(
                get_dict_value(
                    context=context,
                    dictionary=subcommand,
                    key="args",
                    default={},
                    value_types=dict,
                ),
                paths.roser,
            )
            merge = get_dict_value(
                context=context,
                dictionary=subcommand,
                key="merge",
                default=True,
                value_types=bool,
            )
            # TODO: Move this check the sum of the command args and add warning
            success, error = check_arguments(
                [command_arg.value for command_arg in command_args.values()],
                rose_command_args.keys(),
            )
            if not success:
                raise ConfigurationException(
                    context, f"Subcommand {subcommand_name}. {error}"
                )
            # else:
            #     if error:
            #         LOGGER.warn(f"Subcommand {subcommand_name}. {error}")

            try:
                defined_subcommand: Command = copy.deepcopy(
                    defined_subcommands[petal_name][command_name]
                )
                defined_subcommand.sleep = get_dict_value(
                    context=context,
                    dictionary=subcommand,
                    key="sleep",
                    value_types=[int, float],
                    default=0.0,
                )
                defined_subcommand.condition = get_dict_value(
                    context=context,
                    dictionary=subcommand,
                    key="condition",
                    default="True",
                    value_types=str,
                )
                if isinstance(defined_subcommand, CollectionCommand):
                    success, error = check_arguments(
                        command_args.keys(), defined_subcommand.args.keys(), jinja=False
                    )
                    if not success:
                        raise ConfigurationException(
                            context,
                            f"Merged subcommand {defined_subcommand.name}. {error}",
                        )
                if isinstance(defined_subcommand, CollectionCommand) and merge:
                    merged_commands_and_args = {}
                    forwarded_command_args = get_jinja_arguments(command_args)
                    # not forward
                    not_forwarded_command_args = copy.deepcopy(command_args)
                    not_forwarded_command_args.delete(forwarded_command_args.keys())
                    defined_subcommand.args.update(
                        not_forwarded_command_args, override_default=True
                    )
                    defined_subcommand.args.delete(forwarded_command_args.keys())
                    for subcommand_name, (
                        subcommand,
                        subcommand_args,
                    ) in defined_subcommand.commands_and_args.items():
                        # Merge name
                        merged_subcommand_name = (
                            f"{defined_subcommand.name}/{subcommand_name}"
                        )
                        # Merge args
                        try:
                            subcommand_args.evaluate_jinja(defined_subcommand.args)
                        except InvalidArgument as e:
                            raise ConfigurationException(
                                context,
                                f"Merged subcommand {merged_subcommand_name}. {e}",
                            )
                        # Merge sleeps
                        subcommand.sleep += defined_subcommand.sleep
                        # Merge conditions

                        subcommand.condition = (
                            (
                                defined_subcommand.condition
                                + " and "
                                + JINJA_ENV.from_string(subcommand.condition).render(
                                    defined_subcommand.args
                                )
                            )
                            if subcommand.condition
                            else defined_subcommand.condition
                        )
                        merged_commands_and_args[merged_subcommand_name] = (
                            subcommand,
                            subcommand_args,
                        )
                    commands_and_args.update(merged_commands_and_args)
                else:
                    commands_and_args[subcommand_name] = (
                        defined_subcommand,
                        command_args,
                    )
            except KeyError:
                raise ConfigurationException(
                    context,
                    f"Unable to get command {command_name} for petal {petal_name}",
                )
        return CollectionCommand(
            name=name,
            entity_name=entity_name,
            commands_and_args=commands_and_args,
            description=description,
            args=rose_command_args,
        )

    def execute(self, args: List[str] = [], kwargs: Dict[str, Any] = {}):
        session_name = f"{self.entity_name}/{self.name}"
        if self.check_and_send_kill(args):
            return
        if self.new_session:
            if has_flag(args, ("-sc", "--sub-command")):
                try:
                    subcommand = get_flag_value(args, ("-sc", "--sub-command"))
                    if not subcommand in self.commands_and_args:
                        raise ValueError
                except ValueError:
                    LOGGER.error(
                        "Not correctly defined value for option ('-sc','--sub-command')."
                    )
                    return
            if not TMUX_HANDLER.exist_session(session_name):
                TMUX_HANDLER.add_session(
                    session_name,
                    not has_flag(args, ("-h", "--hide")),
                    save_path=self.check_save_path(args),
                )

        current_args = copy.deepcopy(self.args)
        current_args.update(kwargs)
        for command_name, (command, c_args) in self.commands_and_args.items():
            if not Command.evaluate_condition(command.condition, current_args):
                LOGGER.warn(
                    f"In command {session_name} "
                    f"not launching subcommand {command_name}."
                    "Condition not met."
                )
                continue
            if (
                has_flag(args, ("-sc", "--sub-command"))
                and isinstance(command, TMuxCommand)
                and not (subcommand == command_name)
            ):
                continue
            if any(
                [
                    isinstance(command, command_type)
                    for command_type in [
                        StartCommand,
                        StopCommand,
                        AttachCommand,
                        BuildCommand,
                    ]
                ]
            ):
                command.execute(args, kwargs)
            elif any(
                [
                    isinstance(command, command_type)
                    for command_type in [
                        EntityCommand,
                        CollectionCommand,
                    ]
                ]
            ):
                command_args = copy.deepcopy(c_args)
                command_args.evaluate_jinja(current_args)
                command.execute(args, command_args)

    def kill(self, save_path: str = None):
        session_name = f"{self.entity_name}/{self.name}"
        # runs Petal kill commands if are defined
        for command_and_args in self.commands_and_args.values():
            if (
                isinstance(command_and_args[0], EntityCommand)
                and command_and_args[0].docker is None
            ):
                command_and_args: Tuple[EntityCommand, Arguments]
                for kill_command in command_and_args[0].kill_commands:
                    success, result = run_subprocess(
                        kill_command, False, save_path=save_path
                    )
        TMUX_HANDLER.kill_session(session_name, save_path=save_path)

        return super().kill(save_path=save_path)

    def get_flag_options(self, flag: Tuple[str, str]) -> List[str]:
        if flag == ("-sc", "--sub-command"):
            return list(self.commands_and_args.keys())
        else:
            return super().get_flag_options(flag)
