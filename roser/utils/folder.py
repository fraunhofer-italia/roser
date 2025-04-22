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

from dataclasses import dataclass
import os
from typing import Dict, List, Tuple

from git import Repo, GitError, GitCommandError
import yaml
from .vcs import Vcs, VcsRepository
from .git import Git
from .utils import (
    LOGGER,
    ConfigurationException,
    is_correlated_to_paths,
    is_inside_paths,
    bash_command,
    user_question,
    find_files_by_extension,
)


@dataclass
class Paths:
    docker: str
    roser: str
    ws: str
    devcontainer: str = None


class FolderStructure:
    path: str
    parent: FolderStructure = None
    branch: str = ""
    substructures: Dict[str, FolderStructure] = {}

    def __init__(
        self,
        path: str,
        parent: FolderStructure = None,
        branch: str = "",
        pull: bool = False,
        stable: bool = False,
        info: bool = True,
    ):
        if not os.path.isdir(path):
            raise ConfigurationException(
                "Analyzing Folder Structure", f"'{path}' is not present"
            )
        self.path = path
        self.parent = parent
        self.substructures = {}
        self.branch = branch
        if info and pull:
            LOGGER.info(
                f"\n \n Importing and Pulling substructure of path {self.path} \n \n"
            )
        self.update(root=False, pull=pull, stable=stable)

    # returns lost substructures during the update
    def update(
        self,
        root: bool = False,
        pull: bool = False,
        stable: bool = False,
    ) -> Tuple[Dict[str, FolderStructure], Dict[str, FolderStructure]]:
        new_substructure_paths = []
        # updates main repo
        _git = None
        try:
            if not os.path.isdir(self.path):
                LOGGER.warn(f"Folder {self.path} does not exist.")
                if user_question("Do you want to initialize it?"):
                    self.parent.update_substructure(self.path)
            _git = Repo(self.path)
            # checkout on the first branch that has the same commit of the repo
            if _git.head.is_detached and not stable:
                for branch in _git.branches:
                    if branch.commit.hexsha == _git.head.commit.hexsha:
                        _git.git.checkout(branch.name)
                        break
            if root and not stable:
                if not _git.head.is_detached:
                    _git.active_branch
                    success, result = bash_command(f"git -C {self.path} pull")
                    if not success:
                        LOGGER.error(f"Failed to pull repo '{self.path}'")
                else:
                    LOGGER.error(
                        "Checkout on a branch to update the root Git repository."
                    )
            if pull and len(_git.submodules) > 0:
                success, result = bash_command(
                    f"git -C {self.path} submodule update --init"
                )
                if not success:
                    LOGGER.error(
                        f"Git Folder {self.path} has wrongly defined submodules. Error: \n {result}"
                    )
                    LOGGER.warn(f"Trying to clone them singularly....")
                    for module in _git.submodules:
                        success, result = bash_command(
                            f"git -C {self.path} submodule update --init {module.abspath}"
                        )
                        if not success:
                            LOGGER.error(
                                f"Submodule {module.abspath} of folder {self.path} cannot be updated. Error: \n {result}"
                            )
        except GitError:
            LOGGER.warn(
                f"Path '{self.path}' is not a Git repo. Only git repo are managed"
            )

        try:
            # search for git submodules
            submodules_paths = (
                [submodule.abspath for submodule in _git.submodules]
                if not _git is None
                else []
            )
        except:
            submodules_paths = []
            LOGGER.error(f"Failed to get submodules from repo {self.path}")
        new_substructure_paths += submodules_paths

        vcs_files = Vcs.search_files(
            path=self.path,
            stable=stable,
            exclude_dirs=submodules_paths,
            branch=self.branch,
        )
        # iterates through files
        for file in vcs_files:
            vcs = Vcs(file)
            repos_paths = [repo.path for repo in vcs.repos.values()]
            if all(
                [
                    not is_correlated_to_paths(repo_path, submodules_paths)
                    for repo_path in repos_paths
                ]
            ):
                if pull:
                    vcs.pull()
                if all([os.path.isdir(repo_path) for repo_path in repos_paths]):
                    new_substructure_paths += repos_paths
                else:
                    LOGGER.warn(
                        f"Vcs file '{file}' ignored. It defines repositories that does not exists."
                    )
            else:
                LOGGER.error(f"Vcs file '{file}' overwrites a Git submodule.")

        lost_substructures = {
            path: substructure
            for path, substructure in self.substructures.items()
            if path not in new_substructure_paths
        }

        for substructure_path in new_substructure_paths:
            if substructure_path in self.substructures.keys():
                self.substructures[substructure_path].update(root=False, pull=pull)
            else:
                self.substructures[substructure_path] = FolderStructure(
                    path=substructure_path,
                    branch=self.branch,
                    parent=self,
                    pull=pull,
                    info=False,
                )
        return self.substructures, lost_substructures

    def update_substructure(self, path: str) -> bool:
        _git = None
        is_submodule = False
        is_vcs = False
        try:
            _git = Repo(self.path)
            # search for git submodules
            submodules_paths = (
                [submodule.abspath for submodule in _git.submodules]
                if not _git is None
                else []
            )
            is_submodule = path in submodules_paths
        except GitError:
            LOGGER.warn(
                f"Path '{self.path}' is not a Git repo. Only git repo are managed"
            )
        vcs_files = Vcs.search_files(
            path=self.path,
            stable=False,
            exclude_dirs=submodules_paths,
            branch=self.branch,
        )
        for file in vcs_files:
            _vcs = Vcs(file)
            if path in _vcs.get_paths():
                is_vcs = True
                break
        if not is_submodule and not is_vcs:
            LOGGER.error(f"Path {path} is not substructure of Folder {self.path}")
            return False
        if is_submodule and is_vcs:
            LOGGER.error(
                f"Path {path} is both a submodule and a vcs submodule of Folder {self.path}"
            )
            return False
        if is_submodule:
            success, result = bash_command(
                f"git -C {self.path} submodule update --init {path}"
            )
            if not success:
                LOGGER.error(
                    f"Submodule {path} of folder {self.path} cannot be updated. Error: \n {result}"
                )
            return success
        if is_vcs:
            success = _vcs.pull(path)
            if not success:
                LOGGER.error(f"Repo {path} of folder {self.path} cannot be updated.")
            return success
        return

    def get_substructure_paths(self) -> List[str]:
        return list(self.substructures.keys())

    def is_inside(self, path: str) -> bool:
        return is_inside_paths(path, [self.path])

    def get_structure(self, path: str) -> FolderStructure:
        if path == self.path:
            return self
        if not self.is_inside(path):
            return None
        for substructure_path, substructure in self.substructures.items():
            if substructure_path == path:
                return substructure
            else:
                result = substructure.get_structure(path)
                if not result is None:
                    return result
        return None

    def get_parent_root(self) -> FolderStructure:
        if self.parent is None:
            return self
        else:
            return self.parent.get_parent_root()

    def freeze(
        self,
        indentation: str = "",
        tag: str = None,
        do_tag: bool = True,
        add_image_tag: bool = True,
        exclude_from_vcs: List[str] = [],
    ) -> bool:
        return FolderStructure._freeze_structure(
            indentation,
            self.path,
            branch=self.branch,
            tag=tag,
            do_tag=do_tag,
            add_image_tag=add_image_tag,
            exclude_from_vcs=exclude_from_vcs,
        )

    def get_stable_repos(self):
        return find_files_by_extension(self.path, "stable.repos", max_depth=2)

    def get_stable_image_tag(self):
        stable_repos_files = self.get_stable_repos()
        if not stable_repos_files:
            return None

        if len(stable_repos_files) > 1:
            LOGGER.warning(
                f"Multiple stable.repos file found assuming first one: {stable_repos_files[0]}"
            )

        with open(stable_repos_files[0], "r") as f:
            dict = yaml.safe_load(f)

        if "image_tag" in dict:
            return dict["image_tag"]

        LOGGER.warning("image_tag not found in stable.repos")
        # TODO: add here retro-compatibility
        return None

    def _freeze_structure(
        indentation: str,
        path: str,
        branch: str = "",
        tag: str = None,
        do_tag: bool = True,
        add_image_tag: bool = True,
        exclude_from_vcs: List[str] = [],
    ) -> bool:
        if indentation == "":
            print_path = path
        else:
            print_path = path.removeprefix(path)
        try:
            _git = Repo(path, search_parent_directories=True)
            # search for git submodules
            submodules_paths = (
                [submodule.abspath for submodule in _git.submodules]
                if not _git is None
                else []
            )
        except GitError:
            LOGGER.error(
                f"{indentation}Path '{print_path}' is not a Git repo. Only git repo are managed"
            )
            return False
        exclude_paths = Vcs.search_files(
            path,
            stable=True,
            exclude_dirs=submodules_paths,
            branch=branch,
        )
        if any(
            Git.get_uncommitted_changes(
                path,
                recursive=False,
                show=False,
                exclude_paths=exclude_paths,
            ).values()
        ):
            # checks git changes
            changes_before = Git.get_uncommitted_changes(
                path, recursive=False, show=True
            )
            if any(changes_before.values()) and not user_question(
                "Trying to freeze a entity with uncommitted changes. "
                "Do you want to continue anyway without sub-repository commits?"
            ):
                LOGGER.error(f"{indentation}Freeze aborted.")
                return False

        push_required = False
        # exports vcs files
        vcs_files = Vcs.search_files(
            path, stable=False, exclude_dirs=submodules_paths, branch=branch
        )
        if vcs_files:
            stable_contents_before = {}
            for vcs_file in vcs_files:
                _vcs = Vcs(vcs_file)
                vcs_stable_file = Vcs.get_stable_from_file(vcs_file)
                stable_contents_before[vcs_stable_file] = ""
                try:
                    with open(vcs_stable_file, "r") as f:
                        stable_contents_before[vcs_stable_file] = f.read()
                except FileNotFoundError:
                    pass
                success, result = _vcs.export_stable()
                # Adds image_tag on top of stable.repos
                if add_image_tag:
                    os.system(f"sed -i '1i image_tag: {tag}' {vcs_stable_file}")
                if not success:
                    LOGGER.error(
                        f"{indentation}Failed to create freeze {print_path} of vcs file {vcs_file.removeprefix}. error: {result}"
                    )
                    return False

                if exclude_from_vcs:
                    with open(vcs_stable_file, "r") as f:
                        dict = yaml.safe_load(f.read())
                    with open(vcs_stable_file, "w") as f:
                        new_dict = {}
                        for key, value in dict["repositories"].items():
                            if not any([key.startswith(ep) for ep in exclude_from_vcs]):
                                new_dict[key] = value
                        new_dict = {"repositories": new_dict}
                        f.write(yaml.dump(new_dict))

            # get the stable files
            vcs_stable_files = Vcs.search_files(
                path, stable=True, exclude_dirs=submodules_paths, branch=branch
            )
            changes_after = Git.get_uncommitted_changes(
                path, recursive=False, show=True
            )
            for vcs_stable_file in vcs_stable_files:
                if vcs_stable_file not in stable_contents_before.keys():
                    LOGGER.warn(
                        f"{indentation}File {vcs_stable_file.removeprefix(path)} under path {path} is deprecated."
                    )
                    continue
                with open(vcs_stable_file, "r") as f:
                    if f.read() != stable_contents_before[
                        vcs_stable_file
                    ] and not changes_after[path].is_inside(vcs_stable_file):
                        LOGGER.error(
                            f"{indentation}Unable to freeze {path}. Maybe .gitignore is ignoring file {vcs_stable_file.removeprefix(path)}."
                        )
                        return False

            # if something to commit
            if not all(
                [
                    not changes_after[path].is_inside(vcs_stable_file)
                    for vcs_stable_file in vcs_stable_files
                ]
            ):
                try:
                    commit_message = os.environ["ROSER_FREEZE_COMMIT_MSG"]
                except KeyError:
                    if all(
                        [
                            file in changes_after[path].untracked
                            for file in vcs_stable_files
                        ]
                    ):
                        msg_key = "update"
                    else:
                        msg_key = "add"
                    commit_message = f"chore: {msg_key} stable.repos"
                # Git commit phase
                if not Git.commit_routine(vcs_stable_files, commit_message):
                    LOGGER.error(f"{indentation}Commit aborted.")
                    return False
                push_required = True

        if do_tag:
            # Git tag phase
            if not Git.tag_routine(path, tag):
                LOGGER.info(f"No tag added")
            else:
                push_required = True
        # Git push phase
        if push_required and not Git.push_routine(path):
            LOGGER.error(f"{indentation}Push aborted.")
            return False

        return True
