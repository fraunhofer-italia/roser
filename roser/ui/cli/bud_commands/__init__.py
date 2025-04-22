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
from typing import List
from .bud_command import BudCommand

# TODO: read from files
from .clear import ClearBudCommand
from .quit import QuitBudCommand
from .spawn import SpawnBudCommand
from .edit import EditBudCommand
from .update import UpdateBudCommand
from .code import CodeBudCommand
from .pull import PullBudCommand
from .freeze import FreezeBudCommand
from .record import RecordBudCommand

BUD_COMMANDS: List[BudCommand] = [
    ClearBudCommand,
    QuitBudCommand,
    SpawnBudCommand,
    UpdateBudCommand,
    EditBudCommand,
    CodeBudCommand,
    PullBudCommand,
    FreezeBudCommand,
    RecordBudCommand,
]
