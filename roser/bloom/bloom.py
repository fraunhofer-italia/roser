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
import argparse
import os
import shutil
import sys
from typing import Dict

import jinja2
import pkg_resources

environment = jinja2.Environment()


def specialize_folder(
    source: str, destination: str, specialization_dict: Dict[str, str]
):
    shutil.copytree(source, destination)
    for root, dirs, files in os.walk(destination):
        for file in files:
            with open(os.path.join(root, file), "r") as f:
                template = environment.from_string(f.read()).render(specialization_dict)

            with open(os.path.join(root, file), "w") as f:
                f.write(template)


def bloom_petal(name: str):
    specialize_folder(
        os.path.join(
            pkg_resources.resource_filename("roser", "resources/"), "templates/petal_ws"
        ),
        os.path.join(os.getcwd(), f"{name}_ws"),
        {"name": name},
    )


def bloom_rose(name: str):
    specialize_folder(
        os.path.join(
            pkg_resources.resource_filename("roser", "resources/"), "templates/rose_ws"
        ),
        os.path.join(os.getcwd(), f"{name}_ws"),
        {"name": name},
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "name",
        help="Name of the petal",
    )
    parser.add_argument(
        "-p",
        "--petal",
        help="Allow to create a petal ws",
        action="store_true",
        required=False,
    )
    # parser.add_argument(
    #     "-r",
    #     "--rose",
    #     help="Allow to create a rose ws",
    #     action="store_true",
    #     required=False,
    # )

    args = vars(parser.parse_args())

    if args["petal"]:
        bloomer = bloom_petal
    # elif args["rose"]:
    #     bloomer = bloom_rose
    else:
        print("Neither rose or petal specified exiting.")
        sys.exit(1)

    bloomer(args["name"])


if __name__ == "__main__":
    main()
