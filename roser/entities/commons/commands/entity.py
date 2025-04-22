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
from typing import Any, Dict, List

from ....utils import (
    LOGGER,
    ConfigurationException,
    DockerComposeHandler,
    run_subprocess,
    get_dict_value,
    has_flag,
    Paths,
)
from ..arguments import JINJA_ENV, Arguments
from .base import TMuxCommand, Defaults, check_arguments


@dataclass
class EntityCommand(TMuxCommand):
    stay_alive: bool = False

    # available only if non HostPetal
    service_name: str = None
    docker: DockerComposeHandler = None

    # available only if HostPetal
    kill_commands: List[str] = None
    ws_path: str = None

    # internal variables
    _unspecified_commands: List[str] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        # if the number of commands is odd and not 1 -> add an empty command
        # so that a new terminal inside the container is spawned
        if not len(self.commands) == 1 and not len(self.commands) % 2 == 0:
            self.commands.append(":")

        self.tmux_window_name = f"{self.entity_name}/{self.name}"
        # Defines the kill command
        self.kill_commands = (
            [self.kill_commands]
            if isinstance(self.kill_commands, str)
            else self.kill_commands
        )
        self.kill_commands = (
            [f"/bin/bash -ic 'cd {self.ws_path}; {c}'" for c in self.kill_commands]
            if self.docker is None
            else None
        )

        # Defines if the terminal will be stay alive at the end
        bin_bash = "; /bin/bash" if self.stay_alive else " && exit || /bin/bash"
        # Defines the commands without arguments
        self._unspecified_commands = []
        for c in self.commands:
            if not self.docker is None:
                self._unspecified_commands += [
                    "; ".join(
                        self.docker.execute(
                            self.service_name,
                            f'echo "{c}" >> ~/.bash_history',
                            True,
                        )
                        + self.docker.execute(
                            self.service_name, f"{c}{bin_bash}", False
                        ),
                    )
                ]
            else:
                self._unspecified_commands += [
                    f" cd {self.ws_path}; 'echo \"{c}\" >> ~/.bash_history'; {c}{bin_bash}"
                ]

        # Clears commands
        self.commands = []

    def _substitute_arguments(self, args: Dict[str, Any] = {}) -> List[str]:
        current_args = copy.deepcopy(self.args)
        current_args.update(args)

        # Substitutes JINJA in commands strings
        substituted_commands = [
            JINJA_ENV.from_string(c).render(current_args)
            for c in self._unspecified_commands
        ]
        # Remove empty arguments to allow launch argument default value usage.
        substituted_commands = [
            " ".join([s for s in c.split(" ") if not s.endswith(":=")])
            for c in substituted_commands
        ]
        substituted_commands = [
            " ".join([";" if s.endswith(":=;") else s for s in c.split(" ")])
            for c in substituted_commands
        ]
        return substituted_commands

    def parse(
        name: str,
        entity_name: str,
        paths: Paths,
        dictionary: Dict[str, Any],
        context: str,
        docker: DockerComposeHandler,
    ) -> EntityCommand:
        host_command = get_dict_value(
            context=context,
            dictionary=dictionary,
            key="host",
            default=docker is None,
            value_types=bool,
        )
        if docker is None and not host_command:
            LOGGER.warning(
                context,
                " host petal cannot have container commands. Ignoring option `host`.",
            )
            host_command = True
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
            key="subcommands",
            value_types=[list, str],
        )
        command_args = Arguments(
            get_dict_value(
                context=context,
                dictionary=dictionary,
                key="args",
                default={},
                value_types=dict,
            ),
            paths.roser,
        )
        stay_alive = get_dict_value(
            context=context,
            dictionary=dictionary,
            key="stay_alive",
            default=True,
            value_types=bool,
        )
        if not host_command:
            service_name = get_dict_value(
                context=context,
                dictionary=dictionary,
                key="service_name",
                default=(
                    None
                    if not len(docker.services.keys()) == 1
                    else list(docker.services.keys())[0]
                ),
                value_types=str,
            )
            if not service_name in docker.services.keys():
                raise ConfigurationException(
                    context,
                    f"Key 'service_name' not correctly defined. Docker compose defines: {list(docker.services.keys())}",
                )
        else:
            kill_commands = get_dict_value(
                context=context,
                dictionary=dictionary,
                key="kill",
                default=[],
                value_types=[str, list],
            )
        success, error = check_arguments(subcommands, command_args.keys())
        if not success:
            raise ConfigurationException(context, f"{error}")
        else:
            if error:
                LOGGER.warn(f"In context {context}: {error}")
        return EntityCommand(
            name=name,
            description=description,
            entity_name=entity_name,
            service_name=service_name if not host_command else None,
            commands=subcommands,
            docker=docker if not host_command else None,
            kill_commands=kill_commands if host_command else None,
            ws_path=paths.ws if host_command else None,
            args=command_args,
            stay_alive=stay_alive,
        )

    # args: List of flags, kwargs: dict of arguments
    def execute(self, args: List[str] = [], kwargs: Dict[str, Any] = {}):
        if self.check_and_send_kill(args):
            return
        if (
            not self.docker is None
            and not self.service_name in self.docker.services.keys()
        ):
            LOGGER.error(
                f"Petal {self.entity_name} must be updated. Service name {self.service_name} no more defined"
            )
            return
        # not starting container in case of Host Petal
        if not self.docker is None:
            success, result = run_subprocess(
                self.docker.start, False, save_path=self.check_save_path(args)
            )

        self.commands = self._substitute_arguments(kwargs)
        return super().execute(args, kwargs)

    def kill(self, save_path: str = None):
        if self.docker is None:
            for kill_command in self.kill_commands:
                success, result = run_subprocess(
                    kill_command, False, save_path=save_path
                )
        return super().kill()
