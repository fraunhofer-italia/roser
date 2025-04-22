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
import time

import pyfiglet


def generate_header(program_name, version, description):
    # Generate ASCII art for the program name
    ascii_art = pyfiglet.figlet_format(program_name, font="slant")

    # Create the header template
    header_template = f"""
{ascii_art}
{"=" * 50}
{program_name} v{version}
Description: {description}
{"=" * 50}
"""

    return header_template


def show_header():
    header = generate_header(
        "ROSER \U0001F339",
        "1.0.0-beta",
        "Docker ROS workspace manager",
    )
    os.system("clear")
    print(header)


if __name__ == "__main__":
    show_header()
    attempts = 0
    while True:
        try:
            time.sleep(10)
        except KeyboardInterrupt:
            attempts += 1
            if attempts < 10:
                print("\tNice try! ROSER \U0001F339 cannot be closed \U0001F609")
            elif attempts < 20:
                print("\tStill trying?")
