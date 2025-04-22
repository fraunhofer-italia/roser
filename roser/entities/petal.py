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
from dataclasses import dataclass
from typing import Any, Dict

from roser.utils.logger import LOGGER
from roser.utils.utils import ConfigurationException
from roser.utils.docker import DockerComposeHandler
from roser.utils.folder import FolderStructure
from ..utils import get_dict_value, is_nvidia_docker_installed
from .commons import (
    Arguments,
    ArgumentException,
    AttachCommand,
    BuildCommand,
    Defaults,
    EmptyCommand,
    EntityCommand,
    StartCommand,
    StopCommand,
)
from .entity import Entity, Paths, Command

DEFAULT_PETAL_COMMANDS = [
    "start",
    "stop",
    "build",
    "attach",
]
DEFAULT_HOST_PETAL_COMMANDS = [
    "stop",
    "build",
    "attach",
]


@dataclass
class Petal(Entity):
    host: bool = False
    docker: DockerComposeHandler = None

    @dataclass
    class Description(Entity.Description):
        host: bool = False

        def from_dict(
            yaml_config_file: str, config_dict: Dict[str, Any]
        ) -> Petal.Description:
            name, config_dict = next(iter(config_dict.items()))

            config_path = os.path.realpath(os.path.dirname(yaml_config_file) + "/../")
            return Petal.Description(
                name=name,
                paths=Paths(
                    roser=yaml_config_file,
                    docker=os.path.join(
                        os.path.dirname(yaml_config_file),
                        get_dict_value(
                            context=f"{name}({config_path})",
                            dictionary=config_dict,
                            key="docker-compose",
                            default=os.path.join(config_path, "docker"),
                            value_types=str,
                        ),
                    ),
                    ws=config_path,
                    devcontainer=os.path.join(
                        config_path, ".devcontainer", "devcontainer.json"
                    ),
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
                host=get_dict_value(
                    context=f"{name}({config_path})",
                    dictionary=config_dict,
                    key="host",
                    default=False,
                    value_types=bool,
                ),
            )

    def from_description(description: Petal.Description):
        docker = None
        if not description.host:
            if not os.path.isfile(description.paths.docker) and os.path.isdir(
                description.paths.docker
            ):
                nvidia_compose = os.path.join(
                    description.paths.docker, "docker-compose-nvidia.yml"
                )
                has_nvidia_compose = os.path.exists(nvidia_compose)
                docker_compose_file = (
                    nvidia_compose
                    if is_nvidia_docker_installed() and has_nvidia_compose
                    else os.path.join(description.paths.docker, "docker-compose.yml")
                )
            else:
                docker_compose_file = description.paths.docker
            docker = DockerComposeHandler(docker_compose_file)
        return Petal(
            name=description.name,
            paths=description.paths,
            structure=description.structure,
            volumes=Entity.parse_volumes(
                description.name,
                description.paths.ws,
                description.volumes,
            ),
            commands=Petal.parse_commands(
                description.name,
                description.commands,
                description.paths,
                docker,
            ),
            host=description.host,
            docker=docker,
        )

    def __post_init__(self):
        # upgrades stop command to also kill all the other commands
        if self.docker is None:
            kill_commands = []
            for name, c in self.commands.items():
                # TODO: add kill commands to build and remove from this list
                if not name in ["stop", "attach", "start", "build"]:
                    kill_commands += c.kill_commands
            self.commands["stop"].commands += kill_commands
        return

    def close(self):
        self.commands["stop"].execute()

    def parse_commands(
        petal_name: str,
        commands: Dict[str, Any],
        paths: Paths,
        docker: DockerComposeHandler = None,
    ):
        result = {}

        if not docker is None:
            for default in DEFAULT_PETAL_COMMANDS:
                if not default in commands.keys():
                    commands[default] = {"subcommands": []}
        else:
            for default in DEFAULT_HOST_PETAL_COMMANDS:
                if not default in commands.keys():
                    commands[default] = {"subcommands": []}

        for name, command in commands.items():
            context = f"{petal_name} (Command {name})"
            if (name in DEFAULT_PETAL_COMMANDS and not docker is None) or (
                name in DEFAULT_HOST_PETAL_COMMANDS and docker is None
            ):
                result[name] = Petal.parse_default_command(
                    petal_name, name, command, paths, docker
                )
                continue
            try:
                result[name] = EntityCommand.parse(
                    name=name,
                    entity_name=petal_name,
                    paths=paths,
                    dictionary=command,
                    docker=docker,
                    context=context,
                )
            except ArgumentException as e:
                raise ConfigurationException(context, "In args: " + e.message)

        return result

    @staticmethod
    def parse_default_command(
        petal_name: str,
        name: str,
        command: Dict[str, Any],
        paths: Paths,
        docker: DockerComposeHandler = None,
    ) -> Command:
        context = f"Parsing default command '{name}'."
        if name == "start":
            return StartCommand(docker=docker)
        if name == "stop":
            kill_commands = get_dict_value(
                context=context,
                dictionary=command,
                key="kill",
                value_types=[str, list],
                default=[],
            )
            return StopCommand(commands=kill_commands, docker=docker)
        if name == "attach":
            return AttachCommand(
                entity_name=petal_name, docker=docker, ws_path=paths.ws
            )
        if name == "build":
            default_service_name = None
            subcommands = get_dict_value(
                context=context,
                dictionary=command,
                key="subcommands",
                value_types=[list, str],
            )
            if isinstance(subcommands, str):
                subcommands = [subcommands]
            kill_commands = get_dict_value(
                context=context,
                dictionary=command,
                key="kill",
                value_types=[str, list],
                default=[],
            )
            if not docker is None:
                try:
                    default_service_name = get_dict_value(
                        context=context,
                        dictionary=command,
                        key="service_name",
                        default=(
                            None
                            if not len(docker.services.keys()) == 1
                            else list(docker.services.keys())[0]
                        ),
                        value_types=str,
                    )
                except ConfigurationException as e:
                    pass
            build_commands = []
            for subcommand in subcommands:
                service_name = default_service_name
                build_command = subcommand
                if (
                    not docker is None
                    and isinstance(subcommand, list)
                    and len(subcommand) == 2
                    and subcommand[1] in docker.services.keys()
                ):
                    service_name = subcommand[1]
                    build_command = subcommand[0]
                if not docker is None and not service_name in docker.services.keys():
                    LOGGER.warn(
                        f"Build subcommand {subcommand[0]} is not correctly defined. Service name must be specified"
                    )
                    continue
                build_commands += [
                    EntityCommand(
                        name=name,
                        description="",
                        entity_name=petal_name,
                        service_name=service_name,
                        commands=[build_command],
                        docker=docker,
                        kill_commands=kill_commands if docker is None else None,
                        ws_path=paths.ws if docker is None else None,
                        args=Arguments({}),
                        stay_alive=False,
                    )
                ]
            return BuildCommand(
                entity_name=petal_name,
                docker=docker,
                devcontainer_file=paths.devcontainer,
                build_commands=build_commands,
            )
