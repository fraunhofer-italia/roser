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
import os
from dataclasses import dataclass, field
from typing import Any, Dict

from roser.utils.utils import ConfigurationException
from roser.utils.folder import FolderStructure
from ..utils import (
    LOGGER,
    RoserENV,
    Paths,
    get_dict_value,
    to_absolute_path,
    sort_by_feasibility,
)
from .commons import (
    JINJA_ENV,
    Arguments,
    ArgumentException,
    Defaults,
    CollectionCommand,
    EntityCommand,
)
from .entity import Entity
from .petal import Petal


@dataclass
class Rose(Entity):
    config_folder: str = ""
    source_folder: str = "workspaces"
    petals: Dict[str, Petal] = field(default_factory=dict)

    @dataclass
    class Description(Entity.Description):
        source_folder: str = "workspaces"
        petals: Dict[str, Any] = field(default_factory=dict)

        def from_dict(
            yaml_config_file: str, config_dict: Dict[str, Any]
        ) -> Rose.Description:
            name, config_dict = next(iter(config_dict.items()))
            config_path = os.path.realpath(os.path.dirname(yaml_config_file) + "/../")
            return Rose.Description(
                name=name,
                paths=Paths(
                    roser=yaml_config_file,
                    docker=os.path.join(config_path, "docker"),
                    ws=config_path,
                ),
                volumes=get_dict_value(
                    context=f"{name}({config_path})",
                    dictionary=config_dict,
                    key="volumes",
                    default={},
                    value_types=dict,
                ),
                commands=get_dict_value(
                    context=f"{name}({config_path})",
                    dictionary=config_dict,
                    key="commands",
                    default={},
                    value_types=dict,
                ),
                petals=get_dict_value(
                    context=f"{name}({config_path})",
                    dictionary=config_dict,
                    key="petals",
                    value_types=dict,
                ),
            )

    def unmount(self, only_configured: bool = True):
        for w_name, w in self.petals.items():
            for v_name, v in w.volumes.items():
                v.unmount(only_configured)

    def mount(
        self,
        petals_configurations: Dict[str, Any],
    ):
        for name, configuration in petals_configurations.items():
            context = f"{self.name} (Volume {name})"
            if isinstance(configuration, dict):
                volumes = get_dict_value(
                    context=context,
                    dictionary=configuration,
                    key="volumes",
                    value_types=dict,
                    default={},
                    eval=True,
                )
            else:
                continue
            for volume_name, volume in volumes.items():
                try:
                    self.petals[name].volumes[volume_name].input = to_absolute_path(
                        self.paths.docker,
                        volume,
                    )
                except KeyError:
                    raise ConfigurationException(
                        context,
                        f" volume {volume_name} of ws {name} does not match any configuration",
                    )

        repeat = True
        while True:
            result = False
            if repeat:
                result = True
                for w_name, w in self.petals.items():
                    for v_name, v in w.volumes.items():
                        ws_result = v.mount()
                        result = result and ws_result
            if result:
                break
            else:
                LOGGER.warning("Mount not possible")
                LOGGER.warning("The list of volumes that will be override is: ")
                for w_name, w in self.petals.items():
                    for v_name, v in w.volumes.items():
                        for value in v.unconfigured:
                            LOGGER.warning(f" - {value}")
                try:
                    user_input = (
                        input("Do you want to override them? [yes, no]: ")
                        if not RoserENV.OVERRIDE_VOLUMES
                        else "yes"
                    )
                except (EOFError, KeyboardInterrupt):
                    user_input = ""
                if user_input == "yes":
                    self.unmount(only_configured=False)
                    repeat = True
                elif user_input == "no":
                    break
                else:
                    LOGGER.warning("Write yes or no.")
                    repeat = False

    def __post_init__(self):
        default_commands = {}
        for ws_command in ["start", "stop", "build", "attach"]:
            if ws_command in self.commands.keys():
                LOGGER.warning(
                    f"In context `{self.name}`: "
                    f"Overwriting defined command `{ws_command}` with default one."
                )
            commands_and_args = {
                f"{petal_name}/{ws_command}": (w.commands[ws_command], Arguments())
                for petal_name, w in self.petals.items()
                if ws_command in w.commands.keys()
            }
            default_commands[ws_command] = CollectionCommand(
                name=ws_command,
                entity_name=self.name,
                commands_and_args=commands_and_args,
                description=next(iter(commands_and_args.values()))[0].description,
                new_session=True if ws_command in ["build", "attach"] else False,
            )
        self.commands.update(default_commands)

    def from_description(rose_description: Rose.Description, petals: Dict[str, Petal]):
        return Rose(
            name=rose_description.name,
            paths=rose_description.paths,
            structure=rose_description.structure,
            commands=Rose.parse_commands(
                rose_description.name,
                rose_description.commands,
                rose_description.paths,
                petals,
            ),
            volumes=Entity.parse_volumes(
                rose_description.name,
                rose_description.paths.ws,
                rose_description.volumes,
            ),
            petals=petals,
        )

    def parse_commands(
        rose_name: str,
        commands: Dict[str, Any],
        paths: Paths,
        petals: Dict[str, Petal],
    ):
        result = {}
        defined_subcommands = {p.name: p.commands for p in petals.values()}
        for name, command in commands.items():
            if not "subcommands" in command.keys():
                continue
            context = f"{rose_name} (Command {name})"
            try:
                result[name] = EntityCommand.parse(
                    name=name,
                    entity_name=rose_name,
                    dictionary=command,
                    paths=paths,
                    context=context,
                    docker=None,
                )
            except ArgumentException as e:
                raise ConfigurationException(context, "In args: " + e.message)

        defined_subcommands[rose_name] = result

        self_dependencies = {
            name: [
                d[1]
                for d in CollectionCommand.get_dependencies(
                    dictionary=command,
                    context=f"{rose_name} (Command {name})",
                    entity_names_filters=[rose_name],
                )
            ]
            for name, command in commands.items()
        }
        for name in sort_by_feasibility(self_dependencies):
            if not "commands" in commands[name].keys():
                continue
            try:
                result[name] = CollectionCommand.parse(
                    name=name,
                    entity_name=rose_name,
                    dictionary=commands[name],
                    paths=paths,
                    defined_subcommands=defined_subcommands,
                )
                defined_subcommands[rose_name].update(result)
            except ArgumentException as e:
                raise ConfigurationException(context, "In args: " + e.message)

        return result

    def close(self):
        self.unmount(only_configured=True)
