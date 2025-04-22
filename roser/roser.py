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
import sys
from dataclasses import field
from typing import Any, Dict, List, Union, Tuple

import yaml

from .entities import Petal, Rose
from .entities.commons import JINJA_ENV, Defaults
from .ui import TMUX_HANDLER
from .utils import (
    LOGGER,
    ConfigurationException,
    find_files_by_extension,
    FolderStructure,
)


class Roser:
    items: Dict[str, Union[Rose, Petal]] = field(default_factory=dict)
    rose: Rose = None
    branch: str = ""

    def __init__(
        self,
        import_rose: bool = False,
        import_stable: bool = False,
        path: str = os.getcwd(),
        branch: str = "",
    ) -> None:
        self.branch = branch
        rose_descriptions, petal_descriptions = Roser.get_entities_descriptions(
            path, branch=self.branch
        )
        # there are roses
        if rose_descriptions:
            structure = FolderStructure(
                path=rose_descriptions[0].paths.ws,
                branch=self.branch,
                pull=import_rose,
                stable=import_stable,
            )
            if import_rose:
                try:
                    (
                        rose_descriptions,
                        petal_descriptions,
                    ) = Roser.get_entities_descriptions(path, branch=self.branch)
                except IndexError:
                    if not petal_descriptions:
                        raise ConfigurationException(
                            "Roser", "no roser configuration found!"
                        )
            for petal_description in petal_descriptions:
                if (
                    structure.is_inside(petal_description.paths.ws)
                    and not structure.get_structure(petal_description.paths.ws) is None
                ):
                    petal_description.structure = structure.get_structure(
                        petal_description.paths.ws
                    )
                else:
                    if not structure.is_inside(petal_description.paths.ws):
                        LOGGER.warn(
                            f"Petal {petal_description.name} is not inside the Rose, this may cause pull errors."
                        )
                    else:
                        if structure.get_structure(petal_description.paths.ws) is None:
                            LOGGER.warn(
                                f"Rose {rose_descriptions[0].name} folder structure is not correctly defined. Unable to connect it with Petal {petal_description.name}."
                            )
                    petal_description.structure = FolderStructure(
                        path=petal_description.paths.ws,
                        parent=None,
                        branch=self.branch,
                        pull=import_rose,
                        stable=import_stable,
                    )
        else:
            for petal_description in petal_descriptions:
                petal_description.structure = FolderStructure(
                    path=petal_description.paths.ws,
                    parent=None,
                    branch=self.branch,
                    pull=import_rose,
                    stable=import_stable,
                )

        self.items = {
            petal_description.name: Petal.from_description(
                petal_description,
            )
            for petal_description in petal_descriptions
        }
        if len(rose_descriptions) > 0:
            if len(rose_descriptions) > 1:
                LOGGER.error(
                    f"Multiple Roses not yet supported! Only Rose {rose_descriptions[0].name} considered"
                )
            rose_descriptions[0].structure = structure
            self.rose: Rose = Rose.from_description(
                rose_descriptions[0], copy.deepcopy(self.items)
            )
            self.rose.mount(rose_descriptions[0].petals)
            self.items.update({self.rose.name: self.rose})

        TMUX_HANDLER.add_session(Defaults.TMUX_SESSION_NAME)

    def close(self, keep_core_alive: bool = False):
        for _, item in self.items.items():
            item.close()
        TMUX_HANDLER.kill(keep_core_alive)

    @staticmethod
    def get_entities_descriptions(path: str, branch: str = ""):
        roser_files = find_files_by_extension(path, "roser.yaml")
        roser_files = [f for f in roser_files if not "roser/resources/templates" in f]
        roser_parse_result = Roser.parse_roser_files(roser_files, branch=branch)

        rose_descriptions: List[Rose.Description] = []
        petal_descriptions: List[Petal.Description] = []
        for file, roser_config in roser_parse_result.values():
            _, config_dict = next(iter(roser_config.items()))
            if "petals" in config_dict.keys():
                description: Rose.Description = Rose.Description.from_dict(
                    file, roser_config
                )
                rose_descriptions.append(description)
            else:
                description: Petal.Description = Petal.Description.from_dict(
                    file, roser_config
                )
                petal_descriptions.append(description)

        return rose_descriptions, petal_descriptions

    @staticmethod
    def parse_roser_files(
        roser_files: List[str], branch: str = ""
    ) -> Dict[str, Tuple[str, Dict[str, Any]]]:
        result: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        if branch:
            roser_file = branch + "." + "roser.yaml"
        else:
            roser_file = "roser.yaml"
        for file in roser_files:
            with open(file, "r") as f:
                try:
                    roser_config = yaml.load(
                        f.read(),
                        Loader=yaml.BaseLoader,  # Allow to interpret bool values as string in yaml
                    )
                    name = next(
                        iter(roser_config)
                    )  # First key must be the Rose or Petal name
                    if name in result.keys():
                        # updates with respect to the Roser branch
                        if (
                            os.path.basename(file) == roser_file
                            and not os.path.basename(result[name][0]) == roser_file
                        ):
                            result[name] = (file, roser_config)
                        elif (
                            os.path.basename(result[name][0]) == roser_file
                            and not os.path.basename(file) == roser_file
                        ):
                            continue
                        else:
                            raise ConfigurationException(
                                "Roses/Petals analysis",
                                f"Entity with name {name} cannot be defined! Already found one with this name.\n"
                                "Roser files paths: \n"
                                f"- {result[name][0]} \n"
                                f"- {file} ",
                            )
                    else:
                        result[name] = (file, roser_config)
                except yaml.MarkedYAMLError as e:
                    raise ConfigurationException(
                        f"Yaml library parsing of file {file}",
                        "Error occurred with message: " + e.__str__(),
                    )

        return result


if __name__ == "__main__":
    roser = Roser()
    sys.exit(0)
