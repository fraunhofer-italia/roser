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

from typing import List


class RoserGLB:
    RECORD_SAVE_PATH: str = None
    ROSER_EDITORS: List[str] = ["code", "gedit", "nano", "vim"]


class RoserENV:
    def get_env(context, env_variable_name: str, value_type, default=None):
        try:
            result = os.environ[env_variable_name]
            if value_type == bool:
                return result.lower() in ["1", "y", "yes", "true", "t"]
            else:
                return result
        except KeyError:
            if not default is None:
                return default
            else:
                raise Exception(
                    f"RoserENV exception: the env variable `{env_variable_name}` is not correctly defined",
                )

    BUILD_DEVCONTAINER = get_env(
        f"Devcontainer build", "ROSER_BUILD_DEVCONTAINER", bool, False
    )
    ALWAYS_ON_TOP = get_env(f"Devcontainer build", "ROSER_ALWAYS_ON_TOP", bool, True)
    TERMINAL_PROVIDER: str = ""
    OVERRIDE_VOLUMES: bool = get_env(
        f"Always Override Volumes", "ROSER_OVERRIDE_VOLUMES", bool, False
    )
    DIRECTORY: bool = get_env(
        f"Allow to select the directory in which roser is started.",
        "ROSER_DIRECTORY",
        str,
        os.getcwd(),
    )
    BRANCH: bool = get_env(
        f"Allow to specify the Roser branch", "ROSER_BRANCH", str, ""
    )

    ROSER_LOG: str = get_env(
        f"Allow to specify the directory of the roser file",
        "ROSER_DIR",
        str,
        "~/.roser/.log",
    )
