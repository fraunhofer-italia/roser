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

from . import BudCommand
from ....roser import Roser
from ....utils import (
    LOGGER,
    ConfigurationException,
    RoserENV,
)
from ..cli import RoserCli
from ..backend import BACKEND


class UpdateBudCommand(BudCommand):
    def execute(self, text: str):
        BACKEND.roser.close(keep_core_alive=True)
        try:
            new_backend = Roser(
                path=RoserENV.DIRECTORY,
                branch=RoserENV.BRANCH,
            )
            # deletes no more existing Roses or Petals
            for name in BACKEND.roser.items.keys():
                delattr(RoserCli, f"do_{name}")
                delattr(RoserCli, f"complete_{name}")
                delattr(RoserCli, f"help_{name}")
            # adds new Roses or Petals
            for name, entity in new_backend.items.items():
                setattr(RoserCli, f"do_{name}", entity.execute)
                setattr(RoserCli, f"complete_{name}", entity.complete)
                setattr(RoserCli, f"help_{name}", entity.help)

            BACKEND.roser = new_backend
        except ConfigurationException as e:
            LOGGER.error("Failed to update Roser with error: " + e.message)

        return

    def complete(self, text, line, begidx, endidx) -> List[str]:
        return []

    def help(self):
        LOGGER.info("Update Roser with respect to the roser.yaml")
