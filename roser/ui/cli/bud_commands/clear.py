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
import os

from . import BudCommand
from ....utils import LOGGER


class ClearBudCommand(BudCommand):
    def execute(self, text: str):
        if os.name == "posix":  # Linux/Unix/MacOS
            os.system("clear")

    def complete(self, text, line, begidx, endidx) -> List[str]:
        return []

    def help(self):
        LOGGER.info("Clear the console screen")
