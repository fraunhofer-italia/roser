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

from .bud_command import BudCommand, complete_recursion
from ....utils import LOGGER, Code, has_flag, split_line
from ....entities import Petal


class CodeBudCommand(BudCommand):
    @property
    def flags(self):
        return [
            ("-c", "--container"),
        ]

    def complete(self, text, line, begidx, endidx) -> List[str]:
        entity = self.get_entity(line, remove_first=True)
        return complete_recursion(
            split_line(line)[1:],
            self.get_entities(),
            self.flags if isinstance(entity, Petal) and not entity.host else [],
        )

    def execute(self, text: str):
        args = text.split(" ")
        entity = self.get_entity(text)
        if has_flag(args, ("-c", "--container")):
            entity: Petal
            if not isinstance(entity, Petal) or entity.host:
                LOGGER.warning("Option '--container' only available for Petals")
                return
            # starts the containers
            entity.commands["start"].execute()

            # runs code on all containers
            for service in entity.docker.services.values():
                Code.run_on_container(
                    service.container_name,
                    devcontainer_file=entity.commands["build"].devcontainer_file,
                )

            # installs code extensions
            entity.commands["build"].install_devcontainer_extensions()

        else:
            # runs code on workspace
            Code.run(entity.paths.ws)

    def help(self):
        LOGGER.info("Edit specified Rose or Petal in vscode")

    @property
    def condition(self):
        return Code.is_installed()
