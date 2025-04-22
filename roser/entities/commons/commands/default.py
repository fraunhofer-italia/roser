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

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from ....ui import TMUX_HANDLER
from ....utils import (
    LOGGER,
    DockerComposeHandler,
    DockerException,
    run_subprocess,
    RoserENV,
    Code,
    has_flag,
    get_flag_value,
)
from .base import Command, TMuxCommand, Defaults
from .entity import EntityCommand


@dataclass
class StartCommand(Command):
    name: str = "start"
    description: str = "starts Petal entity"
    flags: List[Tuple[str, str]] = field(default_factory=lambda: [("-s", "--save")])

    # available only if non HostPetal
    docker: DockerComposeHandler = None

    def __post_init__(self):
        # self.flags = [("-da", "--docker-args")] # TODO: fix this
        return super().__post_init__()

    def execute(self, args: List[str] = [], kwargs: Dict[str, Any] = {}):
        # docker_compose_flags = parse_docker_compose_flags(args, "docker compose start") # TODO: fix this
        success, result = run_subprocess(
            self.docker.start, False, save_path=self.check_save_path(args)
        )

    def kill(self, save_path: str = None):
        return


@dataclass
class StopCommand(Command):
    name: str = "stop"
    description: str = "stops Petal entity"
    flags: List[Tuple[str, str]] = field(default_factory=lambda: [("-s", "--save")])

    # available only if non HostPetal
    docker: DockerComposeHandler = None

    def __post_init__(self):
        if not self.docker is None:
            # self.flags = [("-da", "--docker-args")] # TODO: fix this
            pass
        else:
            self.flags = []
        return super().__post_init__()

    def execute(self, args: List[str] = [], kwargs: Dict[str, Any] = {}):
        if not self.docker is None:
            # docker_compose_flags = parse_docker_compose_flags(
            #    args, "docker compose kill"
            # ) # TODO: fix this
            success, result = run_subprocess(
                self.docker.kill, False, False, save_path=self.check_save_path(args)
            )

        for command in self.commands:
            success, result = run_subprocess(
                command, False, save_path=self.check_save_path(args)
            )

    def kill(self, save_path: str = None):
        return


@dataclass
class AttachCommand(TMuxCommand):
    name: str = "attach"
    description: str = "attaches to the Petal entity"
    unique_attached_window_count: int = 0

    # available only if non HostPetal
    docker: DockerComposeHandler = None

    # available only if HostPetal
    ws_path: str = None

    def __post_init__(self):
        if not self.docker is None and len(self.docker.services) > 1:
            self.flags += [("-s", "--service")]

    def execute(self, args: List[str] = [], kwargs: Dict[str, Any] = {}):
        self.commands = []
        if has_flag(args, ("-k", "--kill")):
            terminal_index = get_flag_value(args, ("-k", "--kill"))
            # Terminal index not specified killing all attached terminals
            if terminal_index is None:
                for i in range(self.unique_attached_window_count):
                    TMUX_HANDLER.kill_window(
                        self.tmux_session_name,
                        f"{self.entity_name}/{self.name}_{i}",
                        save_path=self.check_save_path(args),
                    )
                self.unique_attached_window_count = 0
                return
        else:
            if self.docker is None:
                self.commands = [f"cd {self.ws_path}; /bin/bash"]
            else:
                run_subprocess(
                    self.docker.start, False, save_path=self.check_save_path(args)
                )
                if "-s" in args or "--service" in args:
                    for service_arg in ["-s", "--service"]:
                        try:
                            service_name = args[args.index(service_arg) + 1]
                        except (IndexError, ValueError):
                            pass
                    if service_name in self.docker.services.keys():
                        self.commands += self.docker.execute(
                            service_name, "/bin/bash", hide=True
                        )

                    else:
                        LOGGER.error(
                            f"Petal '{self.entity_name}' has not service '{service_name}'"
                        )
                        return
                else:
                    for service in self.docker.services.keys():
                        self.commands += self.docker.execute(
                            service, "/bin/bash", hide=True
                        )

            terminal_index = self.unique_attached_window_count
            self.unique_attached_window_count += 1

        self.tmux_window_name = f"{self.entity_name}/{self.name}_{terminal_index}"
        return super().execute(args, kwargs)


# Joins sub_commands command in a single command (build command)
@dataclass
class BuildCommand(TMuxCommand):
    name: str = "build"
    description: str = "builds entity. In case of non Host Petal build the image and creates the container"
    build_commands: List[EntityCommand] = field(default_factory=list)

    # available only if non HostPetal
    docker: DockerComposeHandler = None
    devcontainer_file: str = None
    _devcontainer_extensions_installed: bool = False

    def __post_init__(self):
        self.flags += [
            ("-p", "--pull"),
            ("-nc", "--no-cache"),
            ("-ud", "--use-dockerfile"),
        ]
        self.tmux_window_name = f"{self.entity_name}/build"
        if not self.docker is None:
            # self.flags.append(("-da", "--docker-args")) # TODO: fix this
            pass
        for build_command in self.build_commands:
            if not build_command.description == Defaults.COMMAND_DESCRIPTION:
                self.description += "; " + build_command.description

    def execute(self, args: List[str] = [], kwargs: Dict[str, Any] = {}):
        self.commands = []
        if self.check_and_send_kill(args):
            return

        # creates the base of the build command
        if not self.docker is None:
            try:
                if has_flag(args, ("-p", "--pull")):
                    self.commands += self.docker.pull()
                else:
                    self.commands += self.docker.build(
                        has_flag(args, ("-ud", "--use-dockerfile")),
                        has_flag(args, ("-nc", "--no-cache")),
                    )
            except DockerException as e:
                LOGGER.error(f"In Petal {self.entity_name}: {e}")

        for build_command in self.build_commands:
            if (
                self.docker is None
                or build_command.service_name in self.docker.services.keys()
            ):
                self.commands += build_command._unspecified_commands
            else:
                LOGGER.error(
                    f"Petal {self.entity_name} has no more service {build_command.service_name}."
                )

        try:
            self.commands[-1] += " && exit"
        except IndexError:
            self.commands.append("exit")
        self.commands = ["; ".join(self.commands)]
        super().execute(args, kwargs)

        self._devcontainer_extensions_installed = False
        if (
            not self.docker is None
            and RoserENV.BUILD_DEVCONTAINER
            and not has_flag(args, ("-s", "--save"))
        ):
            self.install_devcontainer_extensions()
        return

    def install_devcontainer_extensions(self):
        if self._devcontainer_extensions_installed or not Code.is_installed():
            return
        self._devcontainer_extensions_installed = True

        self.commands = []
        for service_name, service in self.docker.services.items():
            (
                devcontainer_host_command,
                container_command,
            ) = Code.DevContainersHandler.get_prepare_container_commands(
                service.container_name, self.devcontainer_file
            )
            self.commands += [
                "; ".join(
                    [
                        devcontainer_host_command,
                        "; ".join(self.docker.execute(service_name, container_command)),
                    ]
                )
            ]
        return super().execute([], {})
