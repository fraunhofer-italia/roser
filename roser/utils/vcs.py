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

import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import yaml
from .utils import (
    LOGGER,
    ConfigurationException,
    find_files_by_extension,
    get_dict_value,
    bash_command,
    run_subprocess,
)


@dataclass
class VcsRepository:
    path: str
    type: str
    url: str
    version: str = ""

    def clone(self):
        if self.type == "git":
            branch = ""
            if self.version != "":
                branch = f"-b {self.version} "
            success, result = bash_command(f"git clone {branch}{self.url} {self.path}")
            if result:
                if success:
                    LOGGER.info(result)
                else:
                    LOGGER.error(result)
            return success
        else:
            LOGGER.error("Only git clone is supported")
            return False


class Vcs:
    file: str
    repos: Dict[str, VcsRepository] = field(default_factory=list)

    def __init__(self, file: str):
        self.file = file
        with open(self.file, "r") as f:
            contents = yaml.safe_load(f.read())
        repositories = {}
        context = f"Parsing Vcs '{self.file}'"
        for rep_path, repository in get_dict_value(
            context, contents, "repositories", dict, {}
        ).items():
            rep_context = context + f", repository '{rep_path}'"
            repositories[rep_path] = VcsRepository(
                path=os.path.join(os.path.dirname(self.file), rep_path),
                type=get_dict_value(rep_context, repository, "type", str, "git"),
                url=get_dict_value(rep_context, repository, "url", str),
                version=get_dict_value(rep_context, repository, "version", str, ""),
            )

        self.repos = repositories
        return

    def pull(self, path: str = None) -> bool:
        final_result = True
        if path is None:
            commands = [
                f"vcs import --workers 1 --input {self.file} {os.path.dirname(self.file)}",
                f"vcs pull --workers 1 {os.path.dirname(self.file)}",
            ]
            for command in commands:
                success, result = bash_command(command)
                if result:
                    if success:
                        LOGGER.info(result)
                    else:
                        LOGGER.error(result)
                final_result = final_result and success
        else:
            for repo in self.repos.values():
                if path == repo.path:
                    return repo.clone()
            final_result = False

        return final_result

    def get_paths(self):
        return [repo.path for repo in self.repos.values()]

    @staticmethod
    def search_files(
        path: str,
        stable: bool = False,
        exclude_dirs: List[str] = "",
        branch: str = "",
    ) -> List[str]:
        if branch == "stable":
            raise ConfigurationException(
                f"Searching Vcs files at path '{path}'",
                "'stable' branch cannot be used.",
            )
        vcs_files = find_files_by_extension(
            path, ".repos", 2, exclude_dirs=exclude_dirs
        )
        default_vcs_files = []
        stable_vcs_files = []
        branch_vcs_files = []
        branch_stable_vcs_files = []
        for file in vcs_files:
            basename = os.path.basename(file)
            if basename == ".repos":
                default_vcs_files += [file]
            elif stable and basename == "stable.repos":
                stable_vcs_files += [file]
            elif branch != "":
                if basename == f"{branch}.repos":
                    branch_vcs_files += [file]
                elif stable and basename == f"{branch}.stable.repos":
                    branch_stable_vcs_files += [file]
        if stable:
            if branch != "":
                if len(branch_vcs_files) > 0 and not len(branch_stable_vcs_files) > 0:
                    return []
                else:
                    return branch_stable_vcs_files

            if len(vcs_files) > 0 and not len(stable_vcs_files) > 0:
                return []
            else:
                return stable_vcs_files

        if branch != "":
            if len(branch_vcs_files) > 0:
                return branch_vcs_files
        return default_vcs_files

    @staticmethod
    def get_stable_from_folder(folder_path: str, branch: str = "") -> str:
        name = "stable.repos" if branch == "" else f"{branch}.stable.repos"
        return os.path.join(folder_path, name)

    @staticmethod
    def get_stable_from_file(file: str) -> str:
        name = os.path.basename(file)
        dir = os.path.dirname(file)
        if name == ".repos":
            return os.path.join(dir, "stable.repos")
        elif name.endswith(".repos"):
            return os.path.join(dir, name.removesuffix(".repos") + ".stable.repos")
        else:
            return None

    def export_stable(self) -> Tuple[bool, str]:
        output_file = Vcs.get_stable_from_file(self.file)
        return run_subprocess(
            f'/bin/bash -ic "vcs export --exact-with-tags {os.path.dirname(self.file)} > {output_file}"',
            False,
        )
