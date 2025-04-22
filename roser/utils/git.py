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

import difflib
import os
from dataclasses import dataclass, field
from typing import Dict, List, Union

import git
import re

from .logger import LOGGER
from .utils import bash_command, user_question, user_input, run_subprocess

# ANSI escape codes for colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
PURPLE = "\033[95m"
RESET = "\033[0m"


def colored_print(text, color, indent=0):
    print(" " * indent + color + text + RESET)


class Git:
    @dataclass
    class Changes:
        modified: List[str] = field(default_factory=list)
        untracked: List[str] = field(default_factory=list)
        deleted: List[str] = field(default_factory=list)

        def show(self) -> str:
            if self.modified:
                colored_print("Modified files:", RESET, indent=2)
                for file in self.modified:
                    colored_print(file, YELLOW, indent=4)

            if self.untracked:
                colored_print("Untracked files:", RESET, indent=2)
                for file in self.untracked:
                    colored_print(file, GREEN, indent=4)

            if self.deleted:
                colored_print("Deleted files:", RESET, indent=2)
                for file in self.deleted:
                    colored_print(file, RED, indent=4)

        def is_inside(self, file_path_relative_to_git: str) -> bool:
            return any(
                [
                    file_path_relative_to_git in self.modified,
                    file_path_relative_to_git in self.untracked,
                    file_path_relative_to_git in self.deleted,
                ]
            )

        def __bool__(self):
            return any([self.modified, self.untracked, self.deleted])

    def get_uncommitted_changes(
        folder_path: str,
        recursive: bool = False,
        show: bool = False,
        exclude_paths: List[str] = [],
    ) -> Dict[str, Changes]:
        def get_repo_changes(f: str, exclude_paths: List[str] = []) -> Git.Changes:
            changes = Git.Changes()
            try:
                repo = git.Repo(f, search_parent_directories=True)
                diff = repo.index.diff(None)

                for item in diff:
                    path = repo.working_dir + "/" + item.a_path
                    if path in exclude_paths:
                        continue
                    if item.change_type == "M":
                        changes.modified.append(repo.working_dir + "/" + item.a_path)
                    elif item.change_type == "D":
                        changes.deleted.append(repo.working_dir + "/" + item.a_path)

                untracked = repo.git.status(untracked_files=True, porcelain=True).split(
                    "\n"
                )
                for line in untracked:
                    path = repo.working_dir + "/" + line[3:]
                    if path in exclude_paths:
                        continue
                    if line.startswith("?? "):
                        changes.untracked.append(repo.working_dir + "/" + line[3:])

            except git.exc.NoSuchPathError:
                LOGGER.warn(f"Git repository not found at path: {repo.working_dir}")

            except git.exc.GitCommandError:
                pass

            return changes

        uncommitted_changes: Dict[str, Git.Changes] = {}
        uncommitted_changes[folder_path] = get_repo_changes(
            folder_path, exclude_paths=exclude_paths
        )

        # if recursive:
        #     for root, dirs, files in os.walk(folder_path):
        #         for dir in dirs:
        #             repo_path = os.path.join(root, dir)
        #             if os.path.exists(os.path.join(repo_path, ".git")):
        #                 uncommitted_changes[repo_path] = get_repo_changes(repo_path)

        if show:
            for path, changes in uncommitted_changes.items():
                if changes:
                    colored_print(
                        f"Uncommitted changes in {path}:",
                        BLUE,
                    )
                    changes.show()

        return uncommitted_changes

    def are_files_equal(file1: str, file2: str, show_diff: bool = True):
        with open(file1, "r") as f1, open(file2, "r") as f2:
            lines1 = f1.readlines()
            lines2 = f2.readlines()
        equal = True
        differ = difflib.unified_diff(lines1, lines2, fromfile=file1, tofile=file2)
        if show_diff:
            for line in differ:
                line = line.rstrip("\n")
                if line.startswith("-"):
                    colored_print(line, RED)  # Red for removed lines
                    equal = False
                elif line.startswith("+"):
                    colored_print(line, GREEN)  # Green for added lines
                    equal = False
                else:
                    colored_print(line, PURPLE)  # Purple for metadata lines
        return equal

    def is_file_committed(repo_path, file_path):
        repo = git.Repo(repo_path, search_parent_directories=True)
        try:
            git_object = repo.rev_parse(file_path)
            return True
        except BaseException as e:
            return False

    def commit(
        file_path: Union[str, List[str]],
        commit_message: str,
        show_info=True,
        show_error=True,
    ) -> bool:
        try:
            if isinstance(file_path, str):
                repo = git.Repo(file_path, search_parent_directories=True)
            elif isinstance(file_path, list) and len(file_path) > 0:
                repo = git.Repo(file_path[0], search_parent_directories=True)
            repo.git.add(file_path)
            repo.index.commit(commit_message)
            if show_info:
                LOGGER.info(f"Committed {file_path}")
        except git.exc.GitCommandError as e:
            if show_error or show_info:
                LOGGER.error(f"Error while committing {file_path}: {e}")
            return False
        return True

    def add_tag(tag_name: str, file_path: str, show_info=True, show_error=True) -> bool:
        try:
            repo = git.Repo(file_path, search_parent_directories=True)
            tag = repo.create_tag(tag_name, message=f"Tag {tag_name}", force=True)
            if show_info:
                LOGGER.info(f"Tag {tag_name} added successfully in {repo.working_dir}")
        except git.exc.GitCommandError as e:
            if show_error or show_info:
                LOGGER.error(f"Error while adding tag {tag_name}: {e}")
            return False
        return True

    def get_tags(repo_path: str):
        try:
            repo = git.Repo(repo_path, search_parent_directories=True)
            repo.remotes.origin.fetch()
            repo.git.fetch("--tags")
            sorted_tags = sorted(
                repo.tags, key=lambda t: t.commit.committed_date, reverse=True
            )
            tags = [tag.name for tag in sorted_tags]
            return tags
        except Exception as e:
            LOGGER.error(f"Error: {e}")
            return []

    def is_already_tagged(repo_path: str, desired_tag: str = None):
        try:
            repo = git.Repo(repo_path)
            current_commit = repo.head.commit

            # Check if the current commit is tagged
            for tag in repo.tags:
                if desired_tag is None:
                    if tag.commit == current_commit:
                        return True
                else:
                    if tag.commit == current_commit and tag.tag.tag == desired_tag:
                        return True

            return False
        except git.exc.NoSuchPathError:
            LOGGER.info(f"Git repository not found at path: {repo.working_dir}")

    def push(
        file_path: str,
        tags: bool = True,
        show_info: bool = True,
        show_error: bool = True,
    ):
        error = ""
        try:
            repo = git.Repo(file_path, search_parent_directories=True)
            success, result = bash_command(f"git -C {repo.working_dir} push")
            if tags:
                bash_command(f"git -C {repo.working_dir} push --force --tags")
            if show_info:
                LOGGER.info(f"Repository {repo.working_dir} pushed correctly")
        except git.exc.GitCommandError as e:
            error = e
        if not success and (show_error or show_info):
            LOGGER.error(f"Error while pushing repository {repo.working_dir}: {error}")
        return success

    def get_remotes_url(path: str) -> List[str]:
        success, result = run_subprocess([f"git -C {path} remote -v"])
        if not success:
            return []
        remotes = []
        for line in result.split("\n"):
            count = 0
            for pieces in line.split("\t"):
                for types in pieces.split("\r"):
                    for value in types.split(" "):
                        if count == 0:
                            name = value
                        if count == 1:
                            url = value
                        if count == 2:
                            type = value
                        count += 1
            if type == "(push)":
                remotes += [url]
        return remotes

    def check_tag(tag: str) -> bool:
        # Check if the tag name starts with a letter or number
        if not tag[0].isalnum():
            return False

        # Check if the tag name contains only allowed characters
        if not re.match(r"^[a-zA-Z0-9_.-]+$", tag):
            return False

        # Check if the tag name is not the same as any of the reserved characters
        reserved_characters = "^{}~:"
        if any(char in reserved_characters for char in tag):
            return False

        # Check if the tag name does not contain a backslash
        if "\\" in tag:
            return False

        return True

    def tag_routine(path: str, tag: str = None) -> bool:
        if tag is None:
            # check previous tags
            tags = Git.get_tags(path)
            if tags:
                LOGGER.info(f"Latest tag: {tags[0]}; Found tags: {tags}")
            else:
                LOGGER.warn(f"No previous tags found.")
            # new tag
            tag = user_input(f"Insert the desired version to tag: ")
            tag = tag.strip()

        if Git.is_already_tagged(path, tag):
            return True
        # add tag
        return Git.add_tag(tag, path)

    def commit_routine(files: List[str], commit_message: str) -> bool:
        LOGGER.info("Files to commit:")
        [LOGGER.info(f" -{file}\n") for file in files]
        if not user_question("Do you want to commit?"):
            return False
        if commit_message == "":
            LOGGER.error("Empty commit message")
            return False
        return Git.commit(files, commit_message)

    def push_routine(path: str) -> bool:
        if not user_question("Do you want to push the current repository status?"):
            return False
        return Git.push(path)
