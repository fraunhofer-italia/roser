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
from collections import defaultdict
from dataclasses import dataclass
import getpass
import os
import re
import subprocess
import sys
import yaml
from typing import Any, Dict, List, Tuple, Union
import readline

import pexpect

from .logger import LOGGER

cached_sudo_password = None


class ConfigurationException(Exception):
    def __init__(self, context, message):
        error = f"In context {context}: {message}"
        super().__init__(error)
        self.message = error

    def __str__(self):
        return f"ConfigurationException: {self.message}"


@dataclass
class SSHInfos:
    username: str
    ip: str
    password: str
    folder: str

    @staticmethod
    def from_string(string: str):
        username, string = string.split("@")
        ip, string = string.split(":")
        password, folder = string.split("/", 1)
        return SSHInfos(username=username, ip=ip, password=password, folder=folder)

    def connect(self):
        def remove_arg(args: List[str], arg_name: str):
            try:
                index = args.index(arg_name)
                args.pop(index)
                args.pop(index)
            except ValueError:
                pass
            return args

        args = sys.argv.copy()
        args = remove_arg(args, "--ssh")
        args = remove_arg(args, "--terminal")
        args = remove_arg(args, "--prefix")
        os.system(
            f'sshpass -p "{self.password}" ssh -t -X {self.username}@{self.ip} "cd {self.folder}; python3 -m roser --prefix {self.username}@{self.ip} --terminal konsole {args}"'
        )


def is_correlated_to_paths(path: str, path_list: List[str]) -> bool:
    subpath_abs = os.path.abspath(path)
    for path in path_list:
        if os.path.commonpath([subpath_abs, os.path.abspath(path)]) in [
            os.path.abspath(path),
            subpath_abs,
        ]:
            return True
    return False


def is_inside_paths(path: str, path_list: List[str]) -> bool:
    return os.path.commonpath([path] + path_list) in path_list


def args_to_dict(input_list):
    result_dict = {}
    for item in input_list:
        try:
            key, value = item.split(":=")
            result_dict[key] = value
        except ValueError:
            pass
    return result_dict


def user_question(
    question: str, positive_answer: str = "y", negative_answer: str = "n"
) -> bool:
    try:
        response = user_input(question + f" [{positive_answer}/{negative_answer}] ")
    except (EOFError, KeyboardInterrupt):
        return False
    return True if response == positive_answer else False


def user_input(text: str) -> str:
    try:
        user_input = input(text)
        readline.remove_history_item(readline.get_current_history_length() - 1)
    except (EOFError, KeyboardInterrupt):
        return ""

    return user_input


# asks for password only if sudo is used
def run_subprocess(
    command: Union[str, List[str]],
    show_info: bool = False,
    show_error: bool = True,
    save_path: str = None,
):
    if isinstance(command, list):
        command: str = "; ".join(command)
    if show_info:
        LOGGER.info(f"Running `{command}`")

    global cached_sudo_password
    if command == "":
        return True, ""
    if not save_path is None:
        append_to_bash_file(save_path, command)
    try:
        child = pexpect.spawn(command, encoding="utf-8")
        sudo = False
        while True:
            index = child.expect(
                [r"\[sudo\] password", "Sorry, try again", pexpect.EOF], timeout=None
            )
            if index == 0:
                if not show_info:
                    LOGGER.info(f"Running `{command}`")
                # Prompted for the sudo password
                if cached_sudo_password is None:
                    sudo_password = getpass.getpass("Enter sudo password: ").strip()
                    cached_sudo_password = sudo_password
                child.sendline(cached_sudo_password)
                sudo = True
            elif index == 1:
                LOGGER.error("Incorrect password. Please try again.")
                cached_sudo_password = None
            elif index == 2:
                if sudo:
                    LOGGER.error("Incorrect password.")
                # Reached EOF, command execution is complete
                break
        child.close()
        if child.exitstatus == 0:
            return True, child.before.strip()
        else:
            log_output: str = child.before.strip()
            if sudo:
                return False, ""
            if show_error and log_output != "" and not sudo:
                LOGGER.error(log_output)
            return False, child.before.strip()
    except Exception as e:
        if show_error and str(e) != "":
            LOGGER.error(str(e))
        return False, str(e)


def install_nvidia_docker():
    run_subprocess(
        "curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg",
    )
    run_subprocess(
        "curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
        sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list",
    )
    run_subprocess("sudo apt update")
    run_subprocess("sudo apt -y install nvidia-container-toolkit", show_info=True)
    run_subprocess("sudo nvidia-ctk runtime configure --runtime=docker", show_info=True)
    run_subprocess("systemctl restart docker", show_info=True)


def is_nvidia_docker_installed() -> bool:
    try:
        if run_subprocess("nvidia-ctk --version", show_error=False)[0]:
            return True
    except FileNotFoundError as e:
        LOGGER.warning("nvidia-container-toolkit not installed")

    try:
        if run_subprocess("nvidia-smi", show_error=False)[0]:
            print(
                "nvidia-container-toolkit not found but the nvidia diver is available."
            )
            if user_question("Do you want to install nvidia-container-toolkit?"):
                install_nvidia_docker()
                return run_subprocess(
                    "nvidia-container-toolkit --version", show_error=False
                )[0]
    except FileNotFoundError as e:
        pass
    return False


def find_files_by_name(
    root_directory: str, name: str, max_depth=None, exclude_dirs: List[str] = []
) -> List[str]:
    found_files = []
    for root, dirs, files in os.walk(root_directory):
        # if the root is inside the dirs to exclude skip
        if exclude_dirs and is_inside_paths(root, exclude_dirs):
            dirs.clear()
            continue
        # avoid to go further in case of max depth reached
        current_depth = root[len(root_directory) :].count(os.path.sep)
        if not max_depth is None and current_depth == max_depth:
            dirs.clear()
            continue
        # files search
        for file in files:
            if file == name:
                found_files.append(os.path.join(root, file))
    return found_files


def find_files_by_extension(
    root_directory: str, extension: str, max_depth=None, exclude_dirs: List[str] = []
) -> List[str]:
    found_files = []
    for root, dirs, files in os.walk(root_directory):
        # if the root is inside the dirs to exclude skip
        if exclude_dirs and is_inside_paths(root, exclude_dirs):
            dirs.clear()
            continue
        # avoid to go further in case of max depth reached
        current_depth = root[len(root_directory) :].count(os.path.sep)
        if not max_depth is None and current_depth == max_depth:
            dirs.clear()
            continue
        # files search
        for file in files:
            if file.endswith(extension):
                found_files.append(os.path.join(root, file))
    return found_files


def to_absolute_path(
    base_path: str, path_string: Union[str, List[str]]
) -> Union[str, List[str]]:
    if isinstance(path_string, str):
        return (
            path_string
            if path_string.startswith("/")
            else os.path.abspath(os.path.join(base_path, path_string))
        )
    elif isinstance(path_string, list):
        return [to_absolute_path(base_path, p) for p in path_string]


def get_dict_value(
    context, dictionary, key, value_types, default=None, eval=False
) -> Any:
    def eval_string_bash(input_string):
        if not isinstance(input_string, str):
            return input_string

        def run_command(match):
            # Extract the command within $(...)
            command = match.group(1)

            try:
                # Run the command and capture its output
                result = subprocess.check_output(command, shell=True, text=True)
                return result.strip()  # Remove leading/trailing whitespaces
            except subprocess.CalledProcessError as e:
                # Handle errors if the command fails
                return f"Error: {e}"

        pattern = r"\$\((.*?)\)"
        result = re.sub(pattern, run_command, input_string)

        pattern = r"\$(\w+)"
        result = re.sub(
            pattern, lambda match: os.environ.get(match.group(1), ""), result
        )
        return result

    def convert_to_type(value, type):
        if type == dict and isinstance(value, dict):
            return recursive_apply_operation(value, eval_string_bash) if eval else value
        if type == list and isinstance(value, list):
            return value

        val = eval_string_bash(value) if eval else value
        if type == bool:
            if val.lower() == "true":
                return True
            elif val.lower() == "false":
                return False
        elif type == int:
            try:
                return int(value)
            except (TypeError, ValueError):
                pass
        elif type == float:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
        elif type == str:
            return val

        return None

    if not isinstance(value_types, list):
        value_types = [value_types]
    if isinstance(dictionary, dict):
        if key in dictionary.keys():
            for value_type in value_types:
                value = convert_to_type(dictionary[key], value_type)
                if not value is None:
                    return value

            if dictionary[key] == "" and default is not None:
                return default
            LOGGER.error(
                f"In context {context}: the value of the key {key} has not the correct type"
            )
    else:
        LOGGER.warning(f"In context {context}: dictionary argument is not a dictionary")

    if default is not None:
        return default
    else:
        raise ConfigurationException(context, f"the key {key} is not correctly defined")


def convert_bools(value: Union[str, List[str]]) -> Union[str, List[str]]:
    def check_bool(value: str):
        if value == "True" or value == "False":
            return value.lower()
        return value

    if isinstance(value, str):
        return check_bool(value)
    if isinstance(value, List):
        return [check_bool(element) for element in value]


def recursive_apply_operation(d, operation, *args, **kwargs):
    if isinstance(d, dict):
        for key, value in d.items():
            d[key] = recursive_apply_operation(value, operation, *args, **kwargs)
        return d
    elif isinstance(d, list):
        return [
            recursive_apply_operation(item, operation, *args, **kwargs) for item in d
        ]
    elif isinstance(d, str):
        return operation(d, *args, **kwargs)
    else:
        return d


def get_bash_command_flags(command: str) -> List[str]:
    try:
        result = subprocess.run(
            command.split(" ") + ["--help"], capture_output=True, text=True
        )
        if result.returncode == 0:
            flags = re.findall(r"(?<=\s)(--[a-zA-Z0-9_-]+)", result.stdout)
            return flags
        else:
            return []
    except Exception:
        return []


# asks for password via terminal
def bash_command(command: str):
    command = command.split()
    code = os.spawnvpe(os.P_WAIT, command[0], command, os.environ)
    if code == 127:
        sys.stderr.write("{0}: command not found\n".format(command[0]))
    return code == 0, ""


def removeprefix(string: str, prefix: str):
    if string.startswith(prefix):
        return string[len(prefix) :]
    return string


def removesuffix(string: str, suffix: str):
    if string.endswith(suffix):
        return string[: -len(suffix)]
    return string


def has_flag(args: List[str], flag: Tuple[str, str]) -> bool:
    if flag[0] in args or flag[1] in args:
        return True
    return False


def get_flag(given_flag: str, flag_list: List[Tuple[str, str]]) -> Tuple[str, str]:
    for flag in flag_list:
        if given_flag in flag:
            return flag
    return None


def get_flag_value(args: List[str], flag: Tuple[str, str]) -> str:
    value = None
    for flag_option in flag:
        if flag_option in args and len(args) > args.index(flag_option) + 1:
            if value is None:
                value = args[args.index(flag_option) + 1]
            else:
                LOGGER.error(f"Flag {flag} has multiple definitions!")
    return value


def sort_by_feasibility(dependencies: Dict[str, List[str]]):
    def topological_sort(graph):
        def dfs(node):
            visited.add(node)
            being_explored.add(node)

            for neighbor in graph[node]:
                if neighbor in being_explored:
                    raise ValueError("Cycle detected at node '{}'".format(neighbor))
                elif neighbor not in visited:
                    dfs(neighbor)

            being_explored.remove(node)
            topological_order.append(node)

        visited = set()
        being_explored = set()
        topological_order = []

        for node in list(graph.keys()):
            if node not in visited:
                dfs(node)

        return topological_order[::-1]

    all_keys = set(dependencies.keys())
    all_deps = set(dep for deps in dependencies.values() for dep in deps)
    missing_keys = all_deps - all_keys
    if missing_keys:
        raise ValueError(
            "Dependency list contains keys not present in the dictionary: {}".format(
                missing_keys
            )
        )

    graph = defaultdict(list)
    for key, deps in dependencies.items():
        for dep in deps:
            graph[dep].append(key)
    # Adding items without dependencies to the graph
    for key in all_keys:
        if key not in graph:
            graph[key] = []

    try:
        sorted_keys = topological_sort(graph)
        return sorted_keys
    except ValueError as e:
        raise ValueError("Cycle detected in dependencies: {}".format(e))


def append_to_bash_file(file_path: str, lines: Union[str, List[str]]) -> bool:
    try:
        if (
            not os.path.isfile(file_path)
            and not os.path.isdir(file_path)
            and os.path.isdir(os.path.dirname(file_path))
        ):
            with open(file_path, "w") as file:
                file.write("# bash\n")
        if os.path.isfile(file_path):
            add_new_line = False
            with open(file_path, "rb") as file:
                try:
                    file.seek(-1, 2)
                    last_char = file.read(1)
                    if not last_char == b"\n":
                        add_new_line = True
                except OSError:
                    pass
            with open(file_path, "a") as file:
                if add_new_line:
                    file.write("\n")
                if isinstance(lines, str):
                    lines = [lines]
                for line in lines:
                    file.write(line + "\n")
            return True
    except PermissionError as e:
        LOGGER.error(f"{e}")
    return False


def split_line(line: str) -> List[str]:
    splitted = line.split(" ")
    splitted = [
        s for i, s in enumerate(splitted) if not s == "" or i == len(splitted) - 1
    ]
    return splitted
