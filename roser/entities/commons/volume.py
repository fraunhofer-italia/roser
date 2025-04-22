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
import os
import shutil
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List

from ...utils import LOGGER


@dataclass
class Volume:
    class Type(Enum):
        FILE = "file"
        FOLDER = "folder"
        LIST = "list"

        def __str__(self):
            return str(self.value)

        def possibilities():
            return [element.value for element in Volume.Type]

        def get_path_type(path: str):
            try:
                with open(path, "r") as f:
                    pass
            except IsADirectoryError:
                return Volume.Type.FOLDER
            except FileNotFoundError:
                return None

            return Volume.Type.FILE

    context: str
    name: str
    type: Type
    output: str
    input: Any = ""

    configurations: List[str] = field(default_factory=list)
    unconfigured: List[str] = field(default_factory=list)

    @staticmethod
    def _link(input: str, output: str, only_contents: bool = False):
        configurations = []
        unconfigured = []
        dirs_created = []

        if (
            os.path.isfile(input)
            and not os.path.isdir(output)
            and os.path.isdir(os.path.dirname(output))
        ):
            configurations.append(output)
            try:
                os.link(input, output)
            except OSError as e:
                LOGGER.error(f"Failed to link {input}")
                if not os.access(input, os.W_OK):
                    LOGGER.error(
                        f"Roser has not enough permissions to access file '{input}'. To be mounted must be writable by the user."
                    )
                unconfigured.append(output)
        elif os.path.isfile(input) and os.path.isdir(output):
            file = os.path.join(output, os.path.basename(input))
            configurations.append(file)
            try:
                os.link(input, file)
            except OSError as e:
                LOGGER.error(f"Failed to link {input}")
                if not os.access(input, os.W_OK):
                    LOGGER.error(
                        f"Roser has not enough permissions to access file '{input}'. To be mounted must be writable by the user."
                    )
                unconfigured.append(file)
        elif os.path.isdir(input) and os.path.isdir(output):
            dest_subfolder = output
            if only_contents:
                configurations += [
                    os.path.join(output, file) for file in os.listdir(input)
                ]
            else:
                dest_subfolder = os.path.join(output, os.path.basename(input))
                configurations.append(dest_subfolder)
                try:
                    os.makedirs(dest_subfolder)
                except FileExistsError:
                    unconfigured.append(dest_subfolder)
                    LOGGER.error(f"Failed to link {dest_subfolder}")
                    return (configurations, unconfigured)

            dirs_created.append(dest_subfolder)
            failed = False
            for root, _, files in os.walk(input):
                for filename in files:
                    src_path = os.path.join(root, filename)
                    dest_path = os.path.join(
                        dest_subfolder, os.path.relpath(src_path, input)
                    )
                    dest_dir = os.path.dirname(dest_path)
                    if not dest_dir in dirs_created:
                        try:
                            dirs_created.append(dest_dir)
                            os.makedirs(dest_dir)
                        except FileExistsError:
                            if only_contents and dest_dir in configurations:
                                unconfigured.append(dest_dir)
                            LOGGER.error(f"Failed to create folder {dest_dir}")
                            failed = True
                    try:
                        os.link(src_path, dest_path)
                    except OSError as e:
                        if only_contents and dest_path in configurations:
                            unconfigured.append(dest_path)
                        LOGGER.error(f"Failed to link {dest_path}")
                        if not os.access(src_path, os.W_OK):
                            LOGGER.error(
                                f"Roser has not enought permissions to access file '{src_path}'. To be mounted must be writable by the user."
                            )
                        failed = True
            if failed and not only_contents:
                unconfigured.append(dest_subfolder)
                LOGGER.error(f"Failed to link {dest_subfolder}")
        else:
            if not os.path.exists(input):
                LOGGER.error(
                    f"Failed to link {input} with {output}. "
                    f"Input path not exists: {input}"
                )
            elif not os.path.exists(output):
                LOGGER.error(
                    f"Failed to link {input} with {output}. "
                    f"Output path not exists: {output}"
                )
            else:
                input_type = "file" if os.path.isfile(input) else "folder"
                output_type = "file" if os.path.isfile(output) else "folder"
                LOGGER.error(
                    f"Failed to link {input} with {output}. "
                    "No matching types between input and output: "
                    f"Input type: {input_type} - Output type: {output_type} "
                )

        return (configurations, unconfigured)

    def mount(self):
        self.configurations = []
        self.unconfigured = []
        if (
            self.type in [Volume.Type.FILE, Volume.Type.FOLDER]
            and isinstance(self.input, str)
            and (os.path.isfile(self.input) or os.path.isdir(self.input))
        ):
            self.configurations, self.unconfigured = Volume._link(
                self.input, self.output, only_contents=True
            )
        elif (
            self.type == self.Type.LIST
            and isinstance(self.input, list)
            and all([isinstance(item, str) for item in self.input])
            and os.path.isdir(self.output)
        ):
            for element in self.input:
                result = Volume._link(element, self.output, only_contents=False)
                self.configurations += result[0]
                self.unconfigured += result[1]
        else:
            if self.input == "":
                LOGGER.warning(
                    f"In context {self.context}: "
                    f"The volume `{self.name}` is not configured"
                )
            else:
                LOGGER.error(
                    f"In context {self.context}: "
                    f"The volume `{self.name}` is wrongly defined, type must be `{self.type}`"
                )

        return len(self.unconfigured) == 0

    def unmount(self, only_configured: bool = True):
        for configuration in self.configurations:
            if configuration not in self.unconfigured or not only_configured:
                if os.path.isfile(configuration):
                    os.remove(configuration)
                elif os.path.isdir(configuration):
                    shutil.rmtree(configuration)
