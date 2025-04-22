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

import pkg_resources
from ..utils import user_question, user_input

ROSER_DAEMON_SERVICE_NAME = "roserd"


def start(*args, **kwargs):
    print("Starting service...")
    res = os.system(f"sudo systemctl start {ROSER_DAEMON_SERVICE_NAME}")
    if res == 0:
        print("Service stated!")
    return res


def stop(*args, **kwargs):
    print("Stopping service...")
    res = os.system(f"sudo systemctl stop {ROSER_DAEMON_SERVICE_NAME}")
    if res == 0:
        print("Service stopped!")
    return res


def status(*args, **kwargs):
    return os.system(f"sudo systemctl status {ROSER_DAEMON_SERVICE_NAME}")


def restart(*args, **kwargs):
    print("Restarting service...")
    res = os.system(f"sudo systemctl restart {ROSER_DAEMON_SERVICE_NAME}")
    if res == 0:
        print("Service restarted!")
    return res


def enable(*args, **kwargs):
    print("Enabling service...")
    res = os.system(f"sudo systemctl enable {ROSER_DAEMON_SERVICE_NAME}")
    if res == 0:
        print("Service enabled!")
    return res


def disable(*args, **kwargs):
    print("Disabling service...")
    res = os.system(f"sudo systemctl disable {ROSER_DAEMON_SERVICE_NAME}")
    if res == 0:
        print("Service disabled!")
    return res


def install(*args, **kwargs):
    folder = args[0]
    if not folder:
        print("Unable to install service. Folder must be provided.")
        return

    print("Installing service...")
    systemd_file_path = os.path.join(
        pkg_resources.resource_filename("roser", "resources/"), "roserd.service"
    )
    with open(systemd_file_path, "r") as f:
        service_file_content = f.read()

    prefix = (
        user_input("insert the desired prefix: ")
        if user_question("Do you want to add a new prefix for the roser instance? ")
        else ""
    )
    tmp_file = f"/tmp/{ROSER_DAEMON_SERVICE_NAME}.service"
    with open(tmp_file, "w") as f:
        f.write(
            service_file_content.replace("$USER$", os.getlogin())
            .replace("$FOLDER$", folder)
            .replace("$PREFIX_ARG$", f"--prefix {prefix}" if prefix else "")
        )

    res = os.system(
        f"sudo cp {tmp_file} /etc/systemd/system; sudo systemctl daemon-reload"
    )
    if res == 0:
        print("Service installed!")
    if user_question("Do you want to start the daemon now? "):
        start()
    return res == 0


def uninstall(*args, **kwargs):
    print("Uninstalling service...")
    disable()
    stop()
    res = os.system(
        f"sudo rm /etc/systemd/system/{ROSER_DAEMON_SERVICE_NAME}.service; sudo systemctl daemon-reload"
    )
    if res == 0:
        print("Service uninstalled!")
    return res == 0


action_to_fn = {
    "start": start,
    "stop": stop,
    "status": status,
    "restart": restart,
    "enable": enable,
    "disable": disable,
    "install": install,
    "uninstall": uninstall,
}


def main():
    parser = argparse.ArgumentParser(description="Roser daemon helper")
    parser.add_argument(
        "action",
        choices=list(action_to_fn.keys()),
        help="Action to perform",
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default="",
        help="Folder in which roserd should be installed",
    )

    args = parser.parse_args()
    return action_to_fn[args.action](args.folder)


if __name__ == "__main__":
    main()
