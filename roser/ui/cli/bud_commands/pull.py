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
from typing import List, Union

from .bud_command import BudCommand, complete_recursion
from ....utils import (
    LOGGER,
    ConfigurationException,
    has_flag,
    split_line,
)
from ....entities import Rose, Petal


class PullBudCommand(BudCommand):
    @property
    def flags(self):
        return [
            ("-s", "--stable"),
            ("-nr", "--no-root"),
            ("-od", "--only-docker"),
        ]

    def complete(self, text, line, begidx, endidx) -> List[str]:
        return complete_recursion(split_line(line)[1:], self.get_entities(), self.flags)

    def execute(self, text: str):
        args = text.split(" ")
        entity = self.get_entity(text)

        if entity.structure is None:
            LOGGER.error(f"Unable to pull entity {entity.name}")
            return

        if has_flag(args, ("-s", "--stable")):
            if isinstance(entity, Petal):
                has_stable = bool(entity.structure.get_stable_repos())
            if isinstance(entity, Rose):
                has_stable = all(
                    [bool(p.structure.get_stable_repos()) for p in entity.petals]
                )
            if not has_stable:
                LOGGER.error(
                    f"Unable to pull entity {entity.name}. No stable.repos file."
                )
                return

        if not has_flag(args, ("-od", "--only-docker")):
            try:
                # updates structure of the entity
                entity.structure.update(
                    pull=True,
                    root=(not has_flag(args, ("-nr", "--no-root"))),
                    stable=(has_flag(args, ("-s", "--stable"))),
                )
            except ConfigurationException as e:
                LOGGER.error(f"Failed to pull '{entity.name}' with error: {e}")
                return

        PullBudCommand._pull_docker(entity, has_flag(args, ("-s", "--stable")))

    def _pull_docker(entity: Union[Rose, Petal], use_stable: bool) -> bool:
        if isinstance(entity, Rose):
            for petal in entity.petals.values():
                if not petal.docker is None:
                    PullBudCommand._pull_docker(petal, use_stable)
        elif isinstance(entity, Petal):
            stable_tag = None
            if use_stable:
                stable_tag = entity.structure.get_stable_image_tag()
                if stable_tag is None:
                    raise ConfigurationException(
                        "This should not happen! Report this bug!"
                    )

            for command in entity.docker.pull(stable_tag):
                os.system(command)

        return True

    def help(self):
        LOGGER.info("Pull Rose or Petal recursively")
