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
import subprocess
import sys

from setuptools import find_packages, setup
import sys


def run_shell_command(command: str):
    try:
        # Run the command using subprocess
        completed_process = subprocess.run(
            command.split(" "), capture_output=True, text=True, check=True
        )

        # Print the output of the command
        print("Command output:")
        print(completed_process.stdout)

    except subprocess.CalledProcessError as e:
        # If the command fails, print the error message
        print("Error:", e.stderr)
        print("Return code:", e.returncode)


def install_package(package_name: str):
    run_shell_command(f"sudo apt-get install -y {package_name}")


def is_package_installed(package_name):
    try:
        result = subprocess.run(
            ["dpkg", "-s", package_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )
        return "Status: install ok installed" in result.stdout
    except subprocess.CalledProcessError:
        return False


def enable_mount():
    username = os.environ["USER"]
    sudoers_filename = f"/etc/sudoers.d/roser-{username}-mount"
    if os.path.isfile(sudoers_filename):
        return
    run_shell_command(f"sudo touch {sudoers_filename}")
    os.system(
        f'echo "{username} ALL=(ALL) NOPASSWD: /bin/mount, /bin/umount, /usr/bin/mount, /usr/bin/umount" | sudo tee {sudoers_filename}'
    )
    run_shell_command(f"sudo chmod 440 {sudoers_filename}")


enable_mount()

for package in ["tmux", "wmctrl", "konsole"]:
    if not is_package_installed(package):
        install_package(package)

with open("LICENSE", "r") as fh:
    license = fh.read()

package_name = "roser"
setup(
    name=package_name,
    version="1.0.0-beta",
    packages=find_packages(),
    install_requires=[
        "setuptools",
        "docker>=6.1.3",
        "gitpython==3.1.40",
        "pyfiglet>=0.8.post1",
        "pyfiglet!=1.0.0",
        "pyfiglet!=1.0.0rc1",
        "libtmux==0.22.1",
        "jinja2==3.1.2",
        "colorlog==6.7.0",
        "vcstool==0.3.0",
        "pexpect==4.8.0",
        "pyyaml>=6.0",
        "pydantic>=2.0",
        "colorama",
    ],
    author="Marco Magri, Carlo Morganti",
    author_email="marco.magri@fraunhofer.it, carlo.morganti@fraunhofer.it",
    maintainer="Marco Magri, Carlo Morganti",
    maintainer_email="marco.magri.dev@gmail.com, carloski@live.it",
    description="ROS docker workspace handler",
    license="Apache License 2.0",
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "roser = roser.__main__:main",
            "roser-bloom = roser.bloom.bloom:main",
            "roserd = roser.daemon.daemon:main",
        ],
    },
)
