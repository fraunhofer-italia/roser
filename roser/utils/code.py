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
import json
import os
import re
import subprocess
from typing import List, Tuple
import pkg_resources

from .logger import LOGGER
from .utils import run_subprocess


class Code:
    class DevContainersHandler:
        def parse_default_extensions(
            default_extensions_file: str = "~/.config/Code/User/settings.json",
        ):
            try:
                with open(os.path.expanduser(default_extensions_file), "r") as f:
                    dict = json.load(f)
            except FileNotFoundError:
                return []
            except json.decoder.JSONDecodeError as e:
                LOGGER.warn(
                    f"Unable to parse default Code settings at {os.path.expanduser(default_extensions_file)}: {e}"
                )
                return []
            try:
                return dict["dev.containers.defaultExtensions"]
            except KeyError:
                return []

        def get_container_workspace(devcontainer_file_path: str) -> str:
            try:
                with open(os.path.expanduser(devcontainer_file_path), "r") as f:
                    # removes comments
                    json_string = re.sub(r"\s*//.*", "", f.read(), flags=re.MULTILINE)
                    dict = json.loads(json_string)
            except FileNotFoundError:
                return None
            except json.decoder.JSONDecodeError as e:
                LOGGER.warn(
                    f"Unable to parse .devcontainer file at {os.path.expanduser(devcontainer_file_path)}: {e}"
                )
                return None
            try:
                return dict["workspaceFolder"]
            except KeyError:
                LOGGER.warning(
                    f"Unable to parse vscode workspaceFolder from file `{devcontainer_file_path}.`"
                )
                return None

        def parse_file_extension(devcontainer_file_path: str):
            try:
                with open(os.path.expanduser(devcontainer_file_path), "r") as f:
                    # removes comments
                    json_string = re.sub(r"\s*//.*", "", f.read(), flags=re.MULTILINE)
                    dict = json.loads(json_string)
            except FileNotFoundError:
                return []
            except json.decoder.JSONDecodeError as e:
                LOGGER.warn(
                    f"Unable to parse .devcontainer file at {os.path.expanduser(devcontainer_file_path)}: {e}"
                )
                return []
            try:
                return dict["extensions"]
            except KeyError:
                LOGGER.warning(
                    f"Unable to parse vscode extensions from file `{devcontainer_file_path}.`"
                )
                return []

        def get_install_extensions_command(extensions_names: List[str]) -> str:
            return " && ".join(
                [f"code-server --install-extension {e}" for e in extensions_names]
            )

        def get_prepare_container_commands(
            container_name: str, devcontainer_file_path: str = None
        ) -> Tuple[str, str]:
            extensions = Code.DevContainersHandler.parse_default_extensions()
            if not devcontainer_file_path is None:
                extensions += Code.DevContainersHandler.parse_file_extension(
                    devcontainer_file_path
                )
            install_extensions_command = (
                Code.DevContainersHandler.get_install_extensions_command(extensions)
            )

            host_command = "docker cp {} {}:/tmp  > /dev/null 2>&1".format(
                pkg_resources.resource_filename("roser", "resources/")
                + "scripts/download_vscode_server.sh",
                container_name,
            )
            container_command = (
                f'echo "Installing vscode server inside container {container_name} do not stop the container."; '
                + "/bin/bash /tmp/download_vscode_server.sh  >/dev/null 2>&1; "
                + "rm /tmp/download_vscode_server.sh; "
                + 'echo "export PATH=$PATH:~/.vscode-server/bin/$(ls -1t ~/.vscode-server/bin/ | head -n 1)/bin" >> ~/.bashrc; '
                + "source ~/.bashrc"
            )
            if install_extensions_command:
                container_command += (
                    f'; echo "Installing vscode extensions inside container {container_name} do not stop the container."; '
                    + install_extensions_command
                )
            return (host_command, container_command)

    def is_installed() -> bool:
        try:
            if run_subprocess("code --version", show_error=False)[0]:
                return True
        except FileNotFoundError as e:
            return False

    def run(folder: str):
        subprocess.run(
            " ".join(["code", folder]),
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return

    def run_on_container(
        container_name: str,
        container_directory: str = None,
        devcontainer_file: str = None,
    ):
        if container_directory is None:
            container_directory = Code.DevContainersHandler.get_container_workspace(
                devcontainer_file
            )
            if container_directory is None:
                container_directory = container_name + "_ws"
        os.system(
            f"code --folder-uri vscode-remote://attached-container+$(printf '{container_name}' | xxd -p)/{container_directory}"
        )
        return
