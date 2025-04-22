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
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import os
from .roser_env import RoserENV

import colorlog

# Define a custom log level
OUTDATED_IMAGE = 25  # A number between WARNING (30) and INFO (20)

# Add the custom log level to the logging module
logging.addLevelName(OUTDATED_IMAGE, "OUTDATED_IMAGE")


def outdated_image(self, message, *args, **kwargs):
    if self.isEnabledFor(OUTDATED_IMAGE):
        self._log(OUTDATED_IMAGE, message, args, **kwargs)


# Add the new method to the logger
logging.Logger.outdated_image = outdated_image

# Create a logger
LOGGER = colorlog.getLogger()
LOGGER.setLevel(logging.INFO)

# Create a formatter with colored output
formatter = colorlog.ColoredFormatter(
    "%(log_color)s[%(levelname)s] %(message)s",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "white",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_yellow",
        "OUTDATED_IMAGE": "purple",
    },
)

# Create a handler for file and set the formatter
file_handler = RotatingFileHandler(
    os.path.join(RoserENV.ROSER_DIR, ".log"),
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
)
file_handler.setFormatter(formatter)

# Add the file handler to the logger
LOGGER.addHandler(file_handler)

# Log a break section to the log file
break_line = "=" * 80
LOGGER.info(break_line)
LOGGER.info(f"New run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
LOGGER.info(break_line)

# Create a handler and set the formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Add the console handler to the logger
LOGGER.addHandler(console_handler)

if __name__ == "__main__":
    LOGGER.warning("test")
