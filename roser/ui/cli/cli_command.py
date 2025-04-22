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

from typing import List, Tuple
from abc import ABC, abstractmethod


class CliCommand(ABC):
    def __init__(self) -> None:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def flags(self) -> List[Tuple[str, str]]:
        pass

    @abstractmethod
    def execute(self, text: str):
        pass

    @abstractmethod
    def complete(
        self,
        text: str,
        line: str,
        begidx,
        endidx,
    ) -> List[str]:
        pass

    @abstractmethod
    def help(self):
        pass

    @property
    def condition(self):
        return True
