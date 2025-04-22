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

from ..cli import CliCommand
from typing import List, Tuple, Union
from ....entities import Entity
from ....utils import removesuffix, get_flag, split_line
from ..backend import BACKEND


def complete_recursion(
    splitted: Union[str, List[str]], options: List[str], flags: List[Tuple[str, str]]
) -> List[str]:
    if len(splitted) == 1 and splitted[0] == "":
        return options + [flag[1] for flag in flags]

    # check flags
    if len(splitted) == 1:
        if splitted[0] == "-":
            return ["-"]
        if splitted[0].startswith("-"):
            if not get_flag(splitted[0], flags) is None:
                return [splitted[0].split("-")[-1]]
            else:
                if flags:
                    return [
                        flag[1].removeprefix("--")
                        for flag in flags
                        if flag[1].startswith(splitted[0])
                    ]
    flag = get_flag(splitted[0], flags)
    if not flag is None:
        flags.remove(flag)
        return complete_recursion(splitted[1:], options, flags)

    # check options
    if len(splitted) == 1:
        possibilities = [o for o in options if o.startswith(splitted[0])]
        if possibilities:
            if not "/" in splitted[0]:
                return possibilities
            else:
                return [possibility.split("/")[-1] for possibility in possibilities]

    if len(splitted) > 1:
        if splitted[0] in options:
            return complete_recursion(splitted[1:], [], flags)

    return None, splitted[0]


class BudCommand(CliCommand):
    entity: Entity

    def __init__(self) -> None:
        pass

    @property
    def name(self) -> str:
        return removesuffix(str(self.__class__.__name__), "BudCommand").lower()

    @property
    def flags(self) -> List[Tuple[str, str]]:
        return []

    def complete(
        self,
        text,
        line,
        begidx,
        endidx,
    ) -> List[str]:
        return complete_recursion(
            split_line(line)[1:],
            self.get_entities(),
            [],
        )

    @property
    def condition(self):
        return True

    def get_entity(
        self, input: Union[str, List[str]], remove_first: bool = False
    ) -> Entity:
        entity = None
        if isinstance(input, str):
            elements = input.split(" ")
            if remove_first:
                elements = elements[1:]
            elements = [s for s in elements if not s == "" or s == elements[-1]]
        if isinstance(input, list):
            elements = input

        if elements:
            entity = self.get_entity_by_name(elements[0])

        return entity

    def get_entity_by_name(self, name: str) -> Entity:
        if name in BACKEND.roser.items.keys():
            return BACKEND.roser.items[name]
        else:
            return None

    def get_entities(self) -> List[Entity]:
        return list(BACKEND.roser.items.keys())
